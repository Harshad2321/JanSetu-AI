"""
JanSetu AI — Incident Intake & Workflow Execution API Routes.

Implements:
- Citizen complaint creation (multipart/form-data for camera/file uploads & JSON for headless clients)
- Coordinate validation and provenance tracking
- Decoupled operational and photographic verification statuses
- LangGraph multi-agent workflow invocation with bounded retries
- Seeded failure and simulation scenario execution
- Agent execution traces and audit history retrieval
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from app.config import settings
from app.db.models import IncidentModel
from app.db.repository import (
    create_incident,
    get_incident_by_id,
    list_incidents,
)
from app.db.seed import seed_demonstration_incidents
from app.db.session import get_db
from app.schemas.api import (
    IncidentListResponse,
    IncidentResponse,
    SimulationScenarioRequest,
    WorkflowRunRequest,
    WorkflowRunResponse,
)
from app.schemas.incident import (
    AgentExecutionTrace,
    AuditEvent,
    EvidenceOutcome,
    IncidentCategory,
    IncidentLocation,
    IncidentSubmissionRequest,
    LocationSource,
    OperationalStatus,
)
from app.services.image_storage import (
    get_image_access_url,
    load_sanitized_image,
    save_sanitized_base64,
    save_sanitized_image,
)
from app.core.image_processing import evaluate_evidence_intake
from app.services.workflow_service import execute_incident_workflow

logger = logging.getLogger("jansetu.api.incidents")

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=IncidentListResponse)
def get_incidents(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by operational status"),
    category_filter: Optional[str] = Query(None, alias="category", description="Filter by incident category"),
    evidence_status_filter: Optional[str] = Query(None, alias="evidence_status", description="Filter by evidence status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> IncidentListResponse:
    """List and filter recorded civic incidents."""
    items, total = list_incidents(
        db,
        status=status_filter,
        category=category_filter,
        evidence_status=evidence_status_filter,
        limit=limit,
        offset=offset,
    )
    return IncidentListResponse(
        total=total,
        items=[item.to_response() for item in items],
    )


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident_endpoint(
    request: Request,
    db: Session = Depends(get_db),
) -> IncidentResponse:
    """
    Record a new citizen civic incident.

    Accepts:
    1. multipart/form-data:
       - complaint: text (5-2000 characters)
       - category: pothole, waterlogging, garbage, uncertain_other
       - latitude, longitude: optional decimal degrees
       - accuracy_meters: optional float
       - location_source: DEVICE_GPS, USER_PIN_ADJUSTED, MANUAL_ENTRY
       - address_text: optional address
       - is_user_confirmed: optional boolean
       - image: optional image file upload
    2. application/json:
       - IncidentSubmissionRequest payload (with optional image_base64)

    Business Rules:
    - Missing photo -> operational status RECORDED_PENDING_REVIEW, evidence status NOT_PROVIDED.
    - Sanitizes any attached photograph (EXIF stripped, dimension bounded).
    - Preserves all submissions without silent rejection.
    """
    content_type = request.headers.get("content-type", "")
    incident_id = f"INC-{str(uuid.uuid4())[:8].upper()}"
    now_iso = datetime.now(timezone.utc).isoformat()

    complaint_text: str = ""
    category_str: str = IncidentCategory.UNCERTAIN_OTHER.value
    location_data: Dict[str, Any] = {}
    photo_storage_path: Optional[str] = None
    has_photo: bool = False
    evidence_status: EvidenceOutcome = EvidenceOutcome.NOT_PROVIDED
    operational_status: OperationalStatus = OperationalStatus.RECORDED_PENDING_REVIEW
    failure_reason: Optional[str] = None

    is_form = (
        "multipart/form-data" in content_type
        or "application/x-www-form-urlencoded" in content_type
    )

    if is_form:
        form = await request.form()
        raw_complaint = form.get("complaint")
        if not raw_complaint or not isinstance(raw_complaint, str) or len(raw_complaint.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Complaint description must be between 5 and 2000 characters.",
            )
        complaint_text = raw_complaint.strip()

        raw_category = form.get("category")
        if raw_category and isinstance(raw_category, str):
            try:
                category_str = IncidentCategory(raw_category).value
            except ValueError:
                category_str = IncidentCategory.UNCERTAIN_OTHER.value

        # Parse location fields
        lat_raw = form.get("latitude")
        lon_raw = form.get("longitude")
        acc_raw = form.get("accuracy_meters")
        source_raw = form.get("location_source", LocationSource.MANUAL_ENTRY.value)
        addr_raw = form.get("address_text")
        confirmed_raw = form.get("is_user_confirmed", False)

        lat = float(lat_raw) if lat_raw and str(lat_raw).strip() != "" else None
        lon = float(lon_raw) if lon_raw and str(lon_raw).strip() != "" else None
        acc = float(acc_raw) if acc_raw and str(acc_raw).strip() != "" else None
        is_confirmed = (
            str(confirmed_raw).lower() in ("true", "1", "yes")
            if isinstance(confirmed_raw, (str, bool))
            else bool(confirmed_raw)
        )

        try:
            loc = IncidentLocation(
                latitude=lat,
                longitude=lon,
                accuracy_meters=acc,
                source=LocationSource(source_raw) if source_raw in LocationSource._value2member_map_ else LocationSource.MANUAL_ENTRY,
                address_text=str(addr_raw) if addr_raw else None,
                is_user_confirmed=is_confirmed,
            )
            location_data = loc.model_dump(mode="json")
        except ValidationError as err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(err),
            )

        # Parse image upload
        uploaded_image = form.get("image")
        if uploaded_image and isinstance(uploaded_image, UploadFile) and uploaded_image.filename:
            raw_bytes = await uploaded_image.read()
            if len(raw_bytes) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Image upload exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
                )
            if len(raw_bytes) > 0:
                is_valid, stored_path, _, err_msg, quality = save_sanitized_image(raw_bytes, incident_id)
                if not is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Image upload rejected: {err_msg or 'Invalid image format.'}",
                    )
                photo_storage_path = stored_path
                has_photo = True
                evidence_status = EvidenceOutcome.MATCHED
                operational_status = OperationalStatus.NEW

        raw_failure = form.get("failure_reason")
        if raw_failure and isinstance(raw_failure, str):
            failure_reason = raw_failure.strip()

    else:
        # JSON body parsing
        try:
            body = await request.json()
            submission = IncidentSubmissionRequest(**body)
        except ValidationError as err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(err),
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON request payload.",
            )

        complaint_text = submission.complaint
        category_str = (
            submission.category.value
            if hasattr(submission.category, "value")
            else str(submission.category)
        )
        location_data = submission.location.model_dump(mode="json") if submission.location else {}
        failure_reason = submission.failure_reason

        if submission.image_base64:
            is_valid, stored_path, _, err_msg, quality = save_sanitized_base64(
                submission.image_base64, incident_id
            )
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Base64 image rejected: {err_msg or 'Invalid image.'}",
                )
            photo_storage_path = stored_path
            has_photo = True
            evidence_status = EvidenceOutcome.MATCHED
            operational_status = OperationalStatus.NEW

    # Create audit event for submission
    submission_event = AuditEvent(
        timestamp=now_iso,
        agent="Intake Portal",
        action="Incident Submitted",
        result=(
            "Citizen report recorded with sanitized photograph."
            if has_photo
            else "Citizen report recorded without photograph (pending inspection)."
        ),
    )

    # Evaluate preliminary evidence intake
    _, preliminary_ev = evaluate_evidence_intake(
        image_bytes=raw_bytes if (has_photo and 'raw_bytes' in locals() and raw_bytes) else None
    )

    incident_model = IncidentModel(
        incident_id=incident_id,
        complaint=complaint_text,
        category=category_str,
        location_data=location_data,
        has_photograph=has_photo,
        photo_storage_path=photo_storage_path,
        operational_status=operational_status.value,
        evidence_status=evidence_status.value,
        evidence_analysis=preliminary_ev.model_dump(),
        failure_reason=failure_reason,
        audit_timeline=[submission_event.model_dump()],
    )

    created = create_incident(db, incident_model)
    logger.info("Created incident %s with status %s", created.incident_id, created.operational_status)
    return created.to_response()


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident_detail(
    incident_id: str,
    db: Session = Depends(get_db),
) -> IncidentResponse:
    """Retrieve full incident details and current operational state."""
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found.",
        )
    return incident.to_response()


@router.get("/{incident_id}/photo")
def get_incident_photo(
    incident_id: str,
    db: Session = Depends(get_db),
):
    """
    Secure backend-mediated access to incident photographic evidence.
    - Supabase Storage: Generates short-lived signed URL and redirects (307).
    - Local Storage: Streams sanitized JPEG bytes directly.
    Guarantees:
    - Never exposes private bucket credentials to frontend clients.
    - Strict 404 handling if photo does not exist.
    """
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found.",
        )
    if not incident.has_photograph or not incident.photo_storage_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No photographic evidence recorded for incident '{incident_id}'.",
        )

    # Remote storage: return signed temporary URL
    signed_url = get_image_access_url(incident.photo_storage_path)
    if signed_url:
        return RedirectResponse(
            url=signed_url,
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    # Local storage: stream sanitized bytes
    image_bytes = load_sanitized_image(incident.photo_storage_path)
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored photograph could not be retrieved from persistence layer.",
        )

    return Response(
        content=image_bytes,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.post("/{incident_id}/run", response_model=WorkflowRunResponse)
def run_workflow_endpoint(
    incident_id: str,
    run_req: Optional[WorkflowRunRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Execute the multi-agent LangGraph workflow for an existing incident.
    Optionally accepts a simulation scenario or injected failure.
    """
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found.",
        )

    response = execute_incident_workflow(db, incident, run_req)
    return response


@router.get("/{incident_id}/trace", response_model=List[AgentExecutionTrace])
def get_incident_trace(
    incident_id: str,
    db: Session = Depends(get_db),
) -> List[AgentExecutionTrace]:
    """Retrieve agent execution traces for the specified incident."""
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found.",
        )
    return incident.to_response().agent_traces


@router.get("/{incident_id}/audit", response_model=List[AuditEvent])
def get_incident_audit(
    incident_id: str,
    db: Session = Depends(get_db),
) -> List[AuditEvent]:
    """Retrieve complete audit event history for the specified incident."""
    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found.",
        )
    return incident.to_response().audit_timeline


@router.post("/{incident_id}/simulate", response_model=WorkflowRunResponse)
def simulate_scenario_endpoint(
    incident_id: str,
    req: SimulationScenarioRequest,
    db: Session = Depends(get_db),
) -> WorkflowRunResponse:
    """Trigger a documented failure or success simulation scenario for demonstration."""
    if settings.ENVIRONMENT.lower() == "production" and not settings.DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Synthetic simulations are disabled in production environment.",
        )

    incident = get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID '{incident_id}' not found.",
        )

    workflow_req = WorkflowRunRequest(simulation_scenario=req.scenario)
    return execute_incident_workflow(db, incident, workflow_req)


@router.post("/seed", status_code=status.HTTP_200_OK)
def seed_endpoint(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Explicitly seed demonstration incidents for testing and UI showcase."""
    if settings.ENVIRONMENT.lower() == "production" and not settings.DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demonstration seeding is disabled in production environment.",
        )

    seeded = seed_demonstration_incidents(db)
    return {
        "message": f"Successfully seeded {len(seeded)} demonstration incidents.",
        "seeded_ids": seeded,
    }
