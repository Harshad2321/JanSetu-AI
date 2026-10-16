"""
JanSetu AI — Incident & Workflow Typed Schemas.

Defines Pydantic models, validated enums, and data contracts for:
- Incident and citizen complaints
- Category extraction and multimodal photo evidence analysis
- Geolocation metadata with provenance and accuracy bounds
- Priority assessment and resolution planning
- Critic gate verdicts and closure verification
- Shared workflow case state with dual-status tracking
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# ============================================================================
# Enums
# ============================================================================

class IncidentCategory(str, Enum):
    """Civic incident categories supported by JanSetu AI."""
    POTHOLE = "pothole"
    WATERLOGGING = "waterlogging"
    GARBAGE = "garbage"
    UNCERTAIN_OTHER = "uncertain_other"


class OperationalStatus(str, Enum):
    """
    Operational workflow state of an incident resolution lifecycle.
    Kept strictly decoupled from photo evidence verification status.

    The tracker defines stricter target states than the working app; they are added here to
    support a compatibility-safe, deterministic state machine without breaking existing statuses.
    """
    NEW = "NEW"
    SUBMITTED = "SUBMITTED"
    RECORDED_PENDING_REVIEW = "RECORDED_PENDING_REVIEW"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    AWAITING_CLARIFICATION = "AWAITING_CLARIFICATION"
    CLASSIFIED = "CLASSIFIED"
    TRIAGED = "TRIAGED"
    PLANNING = "PLANNING"
    AWAITING_AUTHORIZATION = "AWAITING_AUTHORIZATION"
    IN_PROGRESS_SIMULATED = "IN_PROGRESS_SIMULATED"
    VALIDATING = "VALIDATING"
    SIMULATING = "SIMULATING"
    VERIFYING_CLOSURE = "VERIFYING_CLOSURE"
    AWAITING_VERIFICATION = "AWAITING_VERIFICATION"
    PLAN_FAILED = "PLAN_FAILED"
    REPLANNING = "REPLANNING"
    RECOVERING = "RECOVERING"
    ESCALATED = "ESCALATED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    AWAITING_HUMAN_REVIEW = "AWAITING_HUMAN_REVIEW"
    AWAITING_EVIDENCE_RETAKE = "AWAITING_EVIDENCE_RETAKE"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    REOPENED = "REOPENED"
    VERIFIED_CLOSED = "VERIFIED_CLOSED"
    SIMULATED_RESOLVED = "SIMULATED_RESOLVED"
    CLOSURE_BLOCKED = "CLOSURE_BLOCKED"
    RESOLVED = "RESOLVED"
    DUPLICATE = "DUPLICATE"


class DuplicateReviewStatus(str, Enum):
    """Classification for possible duplicate incidents."""
    UNCONFIRMED = "UNCONFIRMED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class VerificationOutcome(str, Enum):
    """Independent verification verdicts required by the tracker."""
    VERIFIED = "VERIFIED"
    REJECTED_INSUFFICIENT_EVIDENCE = "REJECTED_INSUFFICIENT_EVIDENCE"
    REJECTED_INCOMPLETE_ACTION = "REJECTED_INCOMPLETE_ACTION"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class PlanType(str, Enum):
    """Response-plan variants required by the target architecture."""
    TEMPORARY_RELIEF = "TEMPORARY_RELIEF"
    PERMANENT_RESOLUTION = "PERMANENT_RESOLUTION"


class PlanStatus(str, Enum):
    """Lifecycle state for response plans and saved versions."""
    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"
    VERIFIED = "VERIFIED"


class EvidenceOutcome(str, Enum):
    """
    Outcome of photographic evidence verification.
    Separated from operational resolution status.
    """
    MATCHED = "MATCHED"
    MISMATCH = "MISMATCH"
    INCONCLUSIVE = "INCONCLUSIVE"
    LOW_QUALITY = "LOW_QUALITY"
    NOT_PROVIDED = "NOT_PROVIDED"


class LocationSource(str, Enum):
    """Provenance and acquisition method of reported coordinates."""
    DEVICE_GPS = "DEVICE_GPS"
    USER_PIN_ADJUSTED = "USER_PIN_ADJUSTED"
    MANUAL_ENTRY = "MANUAL_ENTRY"
    REVERSE_GEOCODED = "REVERSE_GEOCODED"


class PriorityBand(str, Enum):
    """Triage priority tiers."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class CriticVerdictStatus(str, Enum):
    """Critic and verification gate decision outcomes."""
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    ESCALATE = "ESCALATE"


class ImageQualityAssessment(str, Enum):
    """Visual clarity and usability assessment for uploaded photographs."""
    GOOD = "GOOD"
    BLURRY = "BLURRY"
    DARK = "DARK"
    OCCLUDED = "OCCLUDED"
    TOO_SMALL = "TOO_SMALL"
    CORRUPTED = "CORRUPTED"
    ABSENT = "ABSENT"


class EvidenceRecommendation(str, Enum):
    """Recommended triage workflow action regarding evidence."""
    PROCEED = "PROCEED"
    REQUEST_RETAKE = "REQUEST_RETAKE"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    REQUEST_CLARIFICATION = "REQUEST_CLARIFICATION"


class ToolExecutionStatus(str, Enum):
    """Execution status for internal tool and service invocations."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    SKIPPED = "SKIPPED"


# ============================================================================
# Geographic Location Schema
# ============================================================================

class IncidentLocation(BaseModel):
    """
    Geographic location metadata for civic complaints.
    Enforces strict coordinate boundaries, non-negative accuracy, and source provenance.
    """
    model_config = ConfigDict(use_enum_values=True)

    latitude: Optional[float] = Field(
        default=None,
        description="Latitude in decimal degrees (-90.0 to 90.0)"
    )
    longitude: Optional[float] = Field(
        default=None,
        description="Longitude in decimal degrees (-180.0 to 180.0)"
    )
    accuracy_meters: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Reported GPS horizontal accuracy in meters"
    )
    source: LocationSource = Field(
        default=LocationSource.MANUAL_ENTRY,
        description="Source of the location coordinates"
    )
    address_text: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Reverse-geocoded or citizen-provided address description"
    )
    timestamp: Optional[datetime] = Field(
        default=None,
        description="Timestamp when coordinates were acquired"
    )
    is_user_confirmed: bool = Field(
        default=False,
        description="True if citizen explicitly confirmed the pin location"
    )

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (-90.0 <= v <= 90.0):
            raise ValueError(f"Latitude must be between -90.0 and 90.0, got {v}")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (-180.0 <= v <= 180.0):
            raise ValueError(f"Longitude must be between -180.0 and 180.0, got {v}")
        return v

    @model_validator(mode="after")
    def validate_coordinate_pair(self) -> IncidentLocation:
        has_lat = self.latitude is not None
        has_lon = self.longitude is not None
        if has_lat != has_lon:
            raise ValueError("Both latitude and longitude must be provided together, or both omitted.")
        return self


# ============================================================================
# Citizen Complaint & Intake Schemas
# ============================================================================

class CitizenComplaint(BaseModel):
    """
    Original citizen complaint payload.
    Photographs are optional and strongly encouraged; complaints without photos
    are fully accepted and queued for civic inspection.
    """
    model_config = ConfigDict(use_enum_values=True)

    complaint_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for the complaint (e.g. INC-1001)"
    )
    description: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Citizen's text description of the civic problem"
    )
    reported_category: IncidentCategory = Field(
        default=IncidentCategory.UNCERTAIN_OTHER,
        description="Citizen-selected category"
    )
    location: IncidentLocation = Field(
        default_factory=IncidentLocation,
        description="Reported incident location and accuracy metadata"
    )
    has_photograph: bool = Field(
        default=False,
        description="True if an image was attached with the submission"
    )
    reporter_contact: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional masked citizen contact for notifications"
    )
    submitted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Submission timestamp in UTC"
    )


class Incident(BaseModel):
    """Canonical incident record used by the normalized Twin and persistence layer."""
    model_config = ConfigDict(use_enum_values=True, populate_by_name=True)

    incident_id: str = Field(description="Stable incident identifier")
    original_complaint: str = Field(default="", description="Original citizen-submitted complaint text")
    description: Optional[str] = Field(default=None, description="Original complaint description alias")
    normalized_summary: Optional[str] = Field(default=None, description="Normalized summary extracted by the workflow")
    category: IncidentCategory = Field(default=IncidentCategory.UNCERTAIN_OTHER)
    issue_type: Optional[str] = Field(default=None, description="Incident issue type (pothole, waterlogging, garbage)")
    coordinates: Optional[IncidentLocation] = Field(default=None, description="User-selected or device-provided coordinates")
    latitude: Optional[float] = Field(default=None, description="Latitude coordinate")
    longitude: Optional[float] = Field(default=None, description="Longitude coordinate")
    original_image_reference: Optional[str] = Field(default=None, description="Reference to stored original image or upload metadata")
    image_ref: Optional[str] = Field(default=None, description="Image reference identifier or URI")
    impact_details: Optional[str] = Field(default=None, description="Impact summary or safety implications from the report")
    operational_status: OperationalStatus = Field(default=OperationalStatus.SUBMITTED)
    status: Optional[str] = Field(default=None, description="Incident lifecycle status alias")
    priority: Optional[PriorityAssessment] = Field(default=None, description="Computed triage score and rationale")
    priority_band: Optional[str] = Field(default=None, description="Priority band (Low, Medium, High, Critical)")
    is_synthetic: bool = Field(default=True, description="Synthetic data marker required by the academic PoC")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)
    duplicate_review_status: DuplicateReviewStatus = Field(default=DuplicateReviewStatus.UNCONFIRMED)

    @model_validator(mode="after")
    def sync_canonical_fields(self) -> Incident:
        if self.description and not self.original_complaint:
            self.original_complaint = self.description
        elif self.original_complaint and not self.description:
            self.description = self.original_complaint

        if self.issue_type and self.category == IncidentCategory.UNCERTAIN_OTHER:
            try:
                self.category = IncidentCategory(self.issue_type)
            except ValueError:
                pass
        elif not self.issue_type:
            self.issue_type = self.category.value if hasattr(self.category, "value") else str(self.category)

        if self.image_ref and not self.original_image_reference:
            self.original_image_reference = self.image_ref
        elif self.original_image_reference and not self.image_ref:
            self.image_ref = self.original_image_reference

        if self.coordinates:
            if self.latitude is None:
                self.latitude = self.coordinates.latitude
            if self.longitude is None:
                self.longitude = self.coordinates.longitude
        elif self.latitude is not None and self.longitude is not None:
            if not self.coordinates:
                self.coordinates = IncidentLocation(latitude=self.latitude, longitude=self.longitude)

        if not self.status:
            self.status = self.operational_status.value if hasattr(self.operational_status, "value") else str(self.operational_status)

        if not self.priority_band and self.priority:
            self.priority_band = self.priority.priority_band
        return self


class IncidentSubmissionRequest(BaseModel):
    """Inbound intake request payload from frontend or REST client."""
    model_config = ConfigDict(use_enum_values=True)

    complaint: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Citizen complaint text"
    )
    category: IncidentCategory = Field(
        default=IncidentCategory.UNCERTAIN_OTHER,
        description="Citizen-selected category"
    )
    location: IncidentLocation = Field(
        default_factory=IncidentLocation,
        description="Geolocation metadata"
    )
    image_base64: Optional[str] = Field(
        default=None,
        description="Optional Base64-encoded image string"
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="Lab simulation hook for triggering failure recovery"
    )


# ============================================================================# Agent Output Schemas (Preserving backward compatibility)
# ============================================================================

class IncidentExtraction(BaseModel):
    """Facts extracted from the complaint text by Incident Intelligence Agent."""
    model_config = ConfigDict(use_enum_values=True)

    category: str = Field(
        description="Incident category, e.g. 'pothole', 'waterlogging', 'garbage', 'other'"
    )
    severity_indicators: List[str] = Field(
        default_factory=list,
        description="Textual clues indicating severity (e.g. 'deep crater', 'damaged two cars')"
    )
    missing_info: List[str] = Field(
        default_factory=list,
        description="Important information missing from the report"
    )
    confidence_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score (0.0 to 1.0)"
    )
    public_exposure_clues: List[str] = Field(
        default_factory=list,
        description="Clues about pedestrian, vehicular, or arterial traffic exposure"
    )
    extracted_location_clues: Optional[str] = Field(
        default=None,
        description="Location or landmark mentioned in the text"
    )


class PhotoEvidenceAnalysis(BaseModel):
    """
    Typed multimodal evidence analysis produced by Incident Intelligence Agent.
    Strictly disclaims legal proof of presence or authorization of physical repairs.
    """
    model_config = ConfigDict(use_enum_values=True)

    detected_category: str = Field(
        description="Category visually detected in the photograph"
    )
    visible_evidence: str = Field(
        description="Observable visual artifacts (e.g. 'Asphalt crater ~80cm wide with standing water')"
    )
    relevance_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Relevance to the complaint description (0.0 to 1.0)"
    )
    image_quality: ImageQualityAssessment = Field(
        default=ImageQualityAssessment.GOOD,
        description="Visual clarity and lighting quality assessment"
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence level in the visual assessment (0.0 to 1.0)"
    )
    recommendation: EvidenceRecommendation = Field(
        default=EvidenceRecommendation.PROCEED,
        description="Recommended next step: PROCEED, REQUEST_RETAKE, HUMAN_REVIEW, REQUEST_CLARIFICATION"
    )
    outcome: EvidenceOutcome = Field(
        default=EvidenceOutcome.MATCHED,
        description="Verification outcome: MATCHED, MISMATCH, INCONCLUSIVE, LOW_QUALITY, NOT_PROVIDED"
    )
    quality_explanation: Optional[str] = Field(
        default=None,
        description="Reasoning for low quality, blur, or inconclusive assessment"
    )
    provenance: str = Field(
        default="UNVERIFIED",
        description="Verification provenance: GROQ_VISION, DETERMINISTIC_FALLBACK, SEEDED_SIMULATION, INTAKE_SANITIZED_PRELIMINARY, NOT_PROVIDED"
    )
    authenticity_disclaimer: str = Field(
        default=(
            "AI visual triage only. Does not verify physical location, "
            "timestamp, or legal authenticity. Not an authorization for uninspected municipal works."
        ),
        description="Mandatory legal disclaimer"
    )


class ModelPrediction(BaseModel):
    """Typed prediction record for model outputs from NLP, vision or fusion layers."""
    model_config = ConfigDict(use_enum_values=True)

    prediction_id: str = Field(description="Stable identifier for the prediction record")
    incident_id: str = Field(description="Owning incident identifier")
    task_type: str = Field(default="inference", description="vision, NLP, fusion, or other model task")
    task: Optional[str] = Field(default=None, description="Task alias (vision, nlp, fusion)")
    predicted_label: str = Field(default="", description="Predicted label or category")
    label: Optional[str] = Field(default=None, description="Label alias")
    scores: Dict[str, float] = Field(default_factory=dict, description="Per-class model-reported scores")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Model-reported confidence; not a calibrated probability")
    model_name: str = Field(description="Model name, e.g. Groq/VLM, Ollama or TF-IDF pipeline")
    model_version: str = Field(default="unknown", description="Model version or checkpoint identifier")
    available: bool = Field(default=True, description="True only when the model was available to produce this output")
    fallback_provenance: str = Field(default="direct", description="direct, fallback, synthetic, unavailable")
    fallback: Optional[str] = Field(default=None, description="Fallback provenance alias")
    is_synthetic: bool = Field(default=True, description="Synthetic data marker required by the academic PoC")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def sync_prediction_aliases(self) -> ModelPrediction:
        if self.task and (not self.task_type or self.task_type == "inference"):
            self.task_type = self.task
        elif not self.task:
            self.task = self.task_type

        if self.label and not self.predicted_label:
            self.predicted_label = self.label
        elif not self.label:
            self.label = self.predicted_label

        if self.fallback and self.fallback_provenance == "direct":
            self.fallback_provenance = self.fallback
        elif not self.fallback:
            self.fallback = self.fallback_provenance
        return self

    @field_validator("confidence")
    @classmethod
    def validate_model_reported_confidence(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("Model confidence must be between 0.0 and 1.0.")
        return v


class GeoAnalysis(BaseModel):
    """Geospatial context and duplicate detection produced by GeoCivic Agent."""
    model_config = ConfigDict(use_enum_values=True)

    nearby_incident_ids: List[str] = Field(
        default_factory=list,
        description="IDs of nearby active or synthetic incidents"
    )
    is_duplicate: bool = Field(
        default=False,
        description="True if this report is likely a duplicate of an existing record"
    )
    duplicate_review_status: DuplicateReviewStatus = Field(
        default=DuplicateReviewStatus.UNCONFIRMED,
        description="Duplicate review state; never auto-merge without human confirmation"
    )
    duplicate_of_id: Optional[str] = Field(
        default=None,
        description="ID of the original parent incident if duplicate"
    )
    distance_to_nearest_meters: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Calculated distance in meters to nearest incident"
    )
    duplicate_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in duplicate classification (0.0 to 1.0)"
    )
    similarity_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Text similarity score from evidence review; never proof of identity"
    )
    review_rationale: Optional[str] = Field(
        default=None,
        description="Reason why the duplicate candidate is or is not retained for human review"
    )


class PriorityAssessment(BaseModel):
    """Priority scoring and urgency band produced by Priority Intelligence Agent."""
    model_config = ConfigDict(use_enum_values=True)

    priority_score: int = Field(
        ge=0,
        le=100,
        description="Calculated priority score from 0 (lowest) to 100 (critical)"
    )
    priority_band: str = Field(
        default="Medium",
        description="Band: 'Low', 'Medium', 'High', or 'Critical'"
    )
    explanation: str = Field(
        description="Detailed reasoning for this priority score and band"
    )
    urgency_factors: List[str] = Field(
        default_factory=list,
        description="Key risk factors contributing to urgency (e.g. arterial road, school zone)"
    )

    @field_validator("priority_band")
    @classmethod
    def normalize_band(cls, v: str) -> str:
        norm = v.capitalize()
        if norm not in ("Low", "Medium", "High", "Critical"):
            raise ValueError(f"Priority band must be Low, Medium, High, or Critical; got {v}")
        return norm


class ResolutionPlan(BaseModel):
    """Mitigation and repair plan generated by Resolution Planning Agent."""
    model_config = ConfigDict(use_enum_values=True)

    mitigation_steps: List[str] = Field(
        default_factory=list,
        description="Immediate safety containment steps"
    )
    permanent_repair_steps: List[str] = Field(
        default_factory=list,
        description="Permanent restoration steps"
    )
    required_resources: List[str] = Field(
        default_factory=list,
        description="Equipment, materials, or specialized crews required"
    )
    assigned_roles: List[str] = Field(
        default_factory=list,
        description="Municipal teams or departments assigned"
    )
    closure_criteria: List[str] = Field(
        default_factory=list,
        description="Strict measurable criteria that must be verified before incident closure"
    )
    estimated_duration_hours: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Estimated remediation duration in hours"
    )


class ResponsePlan(BaseModel):
    """Tracker-compliant response plan record with plan-type separation and versioning."""
    model_config = ConfigDict(use_enum_values=True)

    plan_id: str = Field(description="Stable identifier for the plan record")
    incident_id: str = Field(description="Owning incident")
    plan_type: PlanType = Field(description="TEMPORARY_RELIEF or PERMANENT_RESOLUTION")
    version: int = Field(default=1, ge=1, description="Plan version number")
    status: PlanStatus = Field(default=PlanStatus.DRAFT, description="Current status of the plan")
    actions: List[str] = Field(default_factory=list, description="Action steps for the response plan")
    dependencies: List[str] = Field(default_factory=list, description="Inputs, approvals, or prerequisites required before execution")
    resource_requirements: List[str] = Field(default_factory=list, description="Required equipment and staffing")
    resources: Optional[List[str]] = Field(default=None, description="Resource requirements alias")
    approval_requirements: List[str] = Field(default_factory=list, description="Approvals or signatures required")
    requires_approval: bool = Field(default=False, description="True if approvals are required before proceeding")
    estimated_cost: Optional[float] = Field(default=None, ge=0.0, description="Estimated cost where available")
    cost_estimate: Optional[float] = Field(default=None, ge=0.0, description="Estimated cost alias")
    estimated_duration_hours: Optional[float] = Field(default=None, ge=0.0, description="Estimated duration where available")
    time_estimate: Optional[float] = Field(default=None, ge=0.0, description="Estimated duration alias")
    closure_criteria: List[str] = Field(default_factory=list, description="Strict measurable criteria that must be verified before incident closure")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_synthetic: bool = Field(default=True, description="Synthetic PoC marker")

    @model_validator(mode="after")
    def sync_plan_aliases(self) -> ResponsePlan:
        if self.resources and not self.resource_requirements:
            self.resource_requirements = self.resources
        elif not self.resources:
            self.resources = self.resource_requirements
        if self.cost_estimate is not None and self.estimated_cost is None:
            self.estimated_cost = self.cost_estimate
        elif self.estimated_cost is not None and self.cost_estimate is None:
            self.cost_estimate = self.estimated_cost
        if self.time_estimate is not None and self.estimated_duration_hours is None:
            self.estimated_duration_hours = self.time_estimate
        elif self.estimated_duration_hours is not None and self.time_estimate is None:
            self.time_estimate = self.estimated_duration_hours
        if self.approval_requirements and not self.requires_approval:
            self.requires_approval = True
        return self


class ExecutionAttempt(BaseModel):
    """Execution history for a simulated intervention attempt."""
    model_config = ConfigDict(use_enum_values=True)

    attempt_id: str = Field(description="Stable execution-attempt identifier")
    incident_id: Optional[str] = Field(default=None, description="Owning incident")
    plan_id: Optional[str] = Field(default=None, description="The plan version under execution")
    resource: str = Field(default="simulated_runtime", description="Resource or service used")
    outcome: str = Field(description="Outcome of the simulated execution")
    failure_reason: Optional[str] = Field(default=None, description="Failure reason when the execution failed")
    evidence_reference: Optional[str] = Field(default=None, description="Reference to evidence used or produced")
    evidence_ref: Optional[str] = Field(default=None, description="Evidence reference alias")
    simulated: bool = Field(default=True, description="The academic PoC requires explicit simulation markers")
    attempted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def sync_attempt_aliases(self) -> ExecutionAttempt:
        if self.evidence_ref and not self.evidence_reference:
            self.evidence_reference = self.evidence_ref
        elif not self.evidence_ref:
            self.evidence_ref = self.evidence_reference
        return self

    @field_validator("simulated")
    @classmethod
    def require_simulated(cls, v: bool) -> bool:
        if not v:
            raise ValueError("ExecutionAttempt records in this academic PoC must be simulated=True.")
        return v


class VerificationResult(BaseModel):
    """Independent verification result for an incident closure decision."""
    model_config = ConfigDict(use_enum_values=True)

    verification_id: str = Field(description="Unique verification identifier")
    incident_id: str = Field(description="Incident under verification")
    criteria: List[str] = Field(default_factory=list, description="Closure criteria checked")
    evidence_reviewed: List[str] = Field(default_factory=list, description="Evidence references reviewed")
    result: VerificationOutcome = Field(default=VerificationOutcome.REJECTED_INSUFFICIENT_EVIDENCE, description="Outcome of verification")
    outcome: Optional[str] = Field(default=None, description="Outcome alias")
    passed: bool = Field(default=False, description="True only when verification passes")
    rejection_reasons: List[str] = Field(default_factory=list, description="Why evidence or action was rejected")
    reviewer: str = Field(default="independent_verification_agent", description="Who performed the verification")
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for audit tracing")

    @model_validator(mode="after")
    def sync_verification_aliases(self) -> VerificationResult:
        res_val = self.result.value if hasattr(self.result, "value") else str(self.result)
        if not self.outcome:
            self.outcome = res_val
        return self


class AuditEvent(BaseModel):
    """Immutable audit trail event record."""
    model_config = ConfigDict(use_enum_values=True)

    event_id: Optional[str] = Field(default=None, description="Stable event identifier when available")
    incident_id: Optional[str] = Field(default=None, description="Owning incident if applicable")
    timestamp: str = Field(description="Event timestamp")
    agent: str = Field(description="Agent or system component name")
    action: str = Field(description="Action executed")
    result: str = Field(description="Action result or status summary")
    summary: Optional[str] = Field(default=None, description="Short summary of the event")
    outcome: Optional[str] = Field(default=None, description="Outcome classification when applicable")
    event_type: Optional[str] = Field(default=None, description="Type of event, e.g. state_change, validation, recovery")
    correlation_id: Optional[str] = Field(default=None, description="Correlation ID for tracing through the workflow")

    @model_validator(mode="after")
    def sync_audit_fields(self) -> AuditEvent:
        if not self.summary:
            self.summary = self.result or self.action
        return self


class HumanCorrection(BaseModel):
    """Human-authored correction record for a normalized or inferred field."""
    model_config = ConfigDict(use_enum_values=True)

    correction_id: str = Field(description="Stable human-correction identifier")
    incident_id: str = Field(description="Incident affected by the correction")
    source_record: str = Field(description="Source table or record type that was corrected")
    corrected_field: str = Field(description="Field or attribute corrected")
    original_value: Optional[str] = Field(default=None, description="Original value before correction")
    corrected_value: Optional[str] = Field(default=None, description="Corrected value after review")
    reviewer: str = Field(default="human_operator", description="Reviewer or operator identity")
    review_status: str = Field(default="PENDING", description="PENDING, ACCEPTED, or REJECTED")
    corrected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    timestamp: Optional[datetime] = Field(default=None, description="Correction timestamp alias")

    @model_validator(mode="after")
    def sync_correction_aliases(self) -> HumanCorrection:
        if self.timestamp and not self.corrected_at:
            self.corrected_at = self.timestamp
        elif not self.timestamp:
            self.timestamp = self.corrected_at
        return self


class RevisedPlan(BaseModel):
    """Alternative plan generated by Adaptive Recovery Agent following an intervention failure."""
    model_config = ConfigDict(use_enum_values=True)

    new_steps: List[str] = Field(
        default_factory=list,
        description="Alternative mitigation or repair steps"
    )
    new_resources: List[str] = Field(
        default_factory=list,
        description="Updated or additional resources needed"
    )
    escalation_required: bool = Field(
        default=False,
        description="True if incident cannot be resolved with available autonomous resources"
    )
    reasoning: str = Field(
        description="Explanation of the revised strategy or reason for escalation"
    )


class ValidationDecision(BaseModel):
    """
    Critic and verification gate decision.
    Validates plans against policy, resource constraints, and safety guidelines.
    """
    model_config = ConfigDict(use_enum_values=True)

    status: str = Field(
        description="'APPROVE', 'REJECT', or 'ESCALATE'"
    )
    feedback: str = Field(
        description="Constructive critique, policy feedback, or reason for rejection/escalation"
    )
    policy_violations: List[str] = Field(
        default_factory=list,
        description="Specific safety or municipal policy guidelines breached"
    )
    resource_check_passed: bool = Field(
        default=True,
        description="True if required resources are available and allocated"
    )
    safety_check_passed: bool = Field(
        default=True,
        description="True if public safety measures are adequate"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        upper = v.upper()
        if upper not in ("APPROVE", "REJECT", "ESCALATE"):
            raise ValueError(f"Critic decision status must be APPROVE, REJECT, or ESCALATE; got {v}")
        return upper


# CriticVerdict alias for strict typing
CriticVerdict = ValidationDecision


# ============================================================================
# Operational & Trace Schemas
# ============================================================================

class ClosureEvidence(BaseModel):
    """
    Verification evidence required to authorize incident closure.
    Ensures no incident is marked resolved without explicit verification.
    """
    model_config = ConfigDict(use_enum_values=True)

    incident_id: str = Field(
        description="Incident reference identifier"
    )
    closure_criteria_met: List[str] = Field(
        default_factory=list,
        description="Criteria verified as fulfilled"
    )
    outstanding_criteria: List[str] = Field(
        default_factory=list,
        description="Criteria still unmet"
    )
    is_ready_for_closure: bool = Field(
        default=False,
        description="True if all required closure criteria are verified"
    )
    inspector_notes: Optional[str] = Field(
        default=None,
        description="Notes from field inspector or simulation verification"
    )
    verified_at: Optional[datetime] = Field(
        default=None,
        description="Verification timestamp in UTC"
    )


class ToolExecutionResult(BaseModel):
    """Standardized result wrapper for internal tools and utilities."""
    model_config = ConfigDict(use_enum_values=True)

    tool_name: str = Field(description="Name of the executed tool")
    status: ToolExecutionStatus = Field(default=ToolExecutionStatus.SUCCESS)
    output_summary: str = Field(description="Summary of tool output")
    execution_time_ms: float = Field(default=0.0, ge=0.0, description="Execution duration in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Error details if tool failed")


class AgentExecutionTrace(BaseModel):
    """Execution telemetry for agent invocations."""
    model_config = ConfigDict(use_enum_values=True)

    agent_name: str = Field(description="Identifier of the executing agent")
    start_time: str = Field(description="ISO start timestamp")
    end_time: str = Field(description="ISO completion timestamp")
    input_summary: str = Field(description="Summary of input provided to agent")
    output_summary: str = Field(description="Summary of output generated by agent")
    status: str = Field(default="SUCCESS", description="'SUCCESS', 'FAILURE', or 'SKIPPED'")
    retry_count: int = Field(default=0, ge=0, description="Retry count for this agent")



# ============================================================================
# Shared Workflow Case State
# ============================================================================

class SharedWorkflowCaseState(BaseModel):
    """
    Comprehensive typed state model for the JanSetu AI multi-agent workflow.
    Guarantees strict separation between evidence status and operational status.
    """
    model_config = ConfigDict(use_enum_values=True)

    incident_id: str = Field(
        description="Unique incident reference identifier (e.g. INC-1001)"
    )
    complaint: CitizenComplaint = Field(
        description="Original citizen complaint details"
    )
    operational_status: OperationalStatus = Field(
        default=OperationalStatus.NEW,
        description="Operational resolution status"
    )
    evidence_status: EvidenceOutcome = Field(
        default=EvidenceOutcome.NOT_PROVIDED,
        description="Photo evidence verification outcome"
    )
    extracted_facts: Optional[IncidentExtraction] = Field(
        default=None,
        description="Facts extracted by Incident Intelligence Agent"
    )
    evidence_analysis: Optional[PhotoEvidenceAnalysis] = Field(
        default=None,
        description="Multimodal evidence analysis"
    )
    geo_context: Optional[GeoAnalysis] = Field(
        default=None,
        description="Geospatial analysis and duplicate detection"
    )
    priority: Optional[PriorityAssessment] = Field(
        default=None,
        description="Priority and urgency assessment"
    )
    current_plan: Optional[ResolutionPlan] = Field(
        default=None,
        description="Active resolution plan"
    )
    validation: Optional[ValidationDecision] = Field(
        default=None,
        description="Critic validation verdict"
    )
    closure_evidence: Optional[ClosureEvidence] = Field(
        default=None,
        description="Closure verification evidence"
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        le=10,
        description="Replanning retry count (bounded to prevent infinite loops)"
    )
    audit_timeline: List[AuditEvent] = Field(
        default_factory=list,
        description="Audit timeline of events"
    )
    agent_traces: List[AgentExecutionTrace] = Field(
        default_factory=list,
        description="Detailed agent execution traces"
    )
    simulation_result: Optional[str] = Field(
        default=None,
        description="Mock simulation result: SUCCESS or FAILURE"
    )
    failure_reason: Optional[str] = Field(
        default=None,
        description="Injected or simulated failure reason"
    )

    @model_validator(mode="after")
    def validate_evidence_and_operational_status_separation(self) -> SharedWorkflowCaseState:
        """
        Enforce core domain constraints:
        1. A photo being MATCHED does NOT mean the complaint is RESOLVED.
        2. A photograph cannot independently close an incident.
        3. A complaint without verified closure evidence cannot become RESOLVED or SIMULATED_RESOLVED.
        4. A photo being NOT_PROVIDED or MISMATCH must never cause silent dropping or deletion.
        """
        # Rule 1: A resolution status requires verified closure evidence with is_ready_for_closure=True
        if self.operational_status in (OperationalStatus.RESOLVED, OperationalStatus.SIMULATED_RESOLVED):
            if not self.closure_evidence or not self.closure_evidence.is_ready_for_closure:
                raise ValueError(
                    f"Incident cannot reach status '{self.operational_status}' without verified closure evidence. "
                    "Incident cannot be marked RESOLVED solely because photograph is MATCHED."
                )

        # Rule 2: A matched photograph alone cannot resolve an incident
        if self.evidence_status == EvidenceOutcome.MATCHED and self.operational_status in (OperationalStatus.RESOLVED, OperationalStatus.SIMULATED_RESOLVED):
            if not self.closure_evidence or not self.closure_evidence.is_ready_for_closure:
                raise ValueError("A matched photograph cannot independently resolve an incident without verified closure evidence.")

        # Rule 3: Missing photograph can never jump to resolved status
        if self.evidence_status == EvidenceOutcome.NOT_PROVIDED and self.operational_status in (OperationalStatus.RESOLVED, OperationalStatus.SIMULATED_RESOLVED):
            if not self.closure_evidence or not self.closure_evidence.is_ready_for_closure:
                raise ValueError("A complaint without a photograph cannot reach a resolved status without verified closure evidence.")

        return self


# ============================================================================
# Phase 5: Agents 1–3 Typed Output Models (P5.1 - P5.4)
# ============================================================================

class IncidentIntelOutput(BaseModel):
    """Validated output from Agent 1: Incident Intelligence."""
    model_config = ConfigDict(use_enum_values=True)

    incident_id: str = Field(description="Unique incident identifier")
    original_complaint: str = Field(description="Strictly preserved raw complaint text")
    selected_category: Optional[str] = Field(default=None, description="Citizen-selected category")
    predicted_category: Optional[str] = Field(default=None, description="Model or fused category")
    confidence: Optional[float] = Field(default=None, description="Model-reported confidence score (not calibrated)")
    evidence_summary: str = Field(default="", description="Summary of evidence streams")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing mandatory fields")
    clarification_questions: List[str] = Field(default_factory=list, description="Targeted clarification questions")
    needs_review: bool = Field(default=False, description="True if disagreement, uncertainty, or missing fields")
    status: str = Field(default="TRIAGED", description="Operational workflow status")
    extracted_facts: Optional[IncidentExtraction] = Field(default=None)
    evidence_analysis: Optional[PhotoEvidenceAnalysis] = Field(default=None)
    model_predictions: List[ModelPrediction] = Field(default_factory=list)


class DuplicateCandidateRecord(BaseModel):
    """Typed candidate duplicate record produced by Agent 2: Geo-Spatial."""
    model_config = ConfigDict(use_enum_values=True)

    candidate_id: str = Field(description="Unique candidate record ID")
    incident_id: str = Field(description="Current incident ID")
    other_incident_id: str = Field(description="Candidate matching incident ID")
    distance_meters: Optional[float] = Field(default=None, description="Exact Haversine distance in meters")
    text_similarity: Optional[float] = Field(default=None, description="TF-IDF cosine similarity score")
    category_comparison: str = Field(default="UNKNOWN", description="Category comparison description")
    rationale: str = Field(default="", description="Explainable matching rationale")
    review_status: str = Field(default="UNCONFIRMED", description="UNCONFIRMED until human review")


class GeoSpatialOutput(BaseModel):
    """Validated output from Agent 2: Geo-Spatial Intelligence."""
    model_config = ConfigDict(use_enum_values=True)

    incident_id: str = Field(description="Incident ID")
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    duplicate_candidates: List[DuplicateCandidateRecord] = Field(default_factory=list)
    has_unconfirmed_duplicates: bool = Field(default=False)
    dbscan_cluster_id: Optional[int] = Field(default=None, description="Cluster label or None if noise/empty")
    is_hotspot: bool = Field(default=False, description="True if part of a dense spatial cluster")
    hotspot_summary: str = Field(default="", description="Summary of cluster findings")
    nearby_incident_ids: List[str] = Field(default_factory=list)
    geo_analysis: Optional[GeoAnalysis] = Field(default=None)


class PriorityAssessmentOutput(BaseModel):
    """Validated output from Agent 3: Risk & Priority."""
    model_config = ConfigDict(use_enum_values=True)

    incident_id: str = Field(description="Incident ID")
    priority_score: float = Field(ge=0.0, le=100.0, description="Calculated priority score (0-100)")
    priority_band: str = Field(description="LOW, MEDIUM, HIGH, CRITICAL")
    factor_contributions: Dict[str, float] = Field(default_factory=dict, description="Point contribution per factor")
    input_factors: Dict[str, Any] = Field(default_factory=dict, description="Input values evaluated")
    missing_factors: List[str] = Field(default_factory=list, description="Factors without available evidence")
    uncertainty_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Uncertainty metric")
    uncertainty_description: str = Field(default="", description="Interpretation of uncertainty")
    is_escalated: bool = Field(default=False, description="Mandatory escalation flag")
    escalation_reasons: List[str] = Field(default_factory=list, description="Reason codes triggering escalation")
    policy_version: str = Field(default="1.0.0", description="Configuration policy version")
    explanation: str = Field(default="", description="Explainable scoring breakdown")
    urgency_factors: List[str] = Field(default_factory=list)


class ResponsePlanningOutput(BaseModel):
    """Validated output from Agent 4: Response Planning."""
    model_config = ConfigDict(use_enum_values=True)

    incident_id: str = Field(description="Incident ID")
    temporary_plan: ResponsePlan = Field(description="Plan A: Immediate risk reduction plan (TEMPORARY_RELIEF)")
    permanent_plan: ResponsePlan = Field(description="Plan B: Long-term remediation plan (PERMANENT_RESOLUTION)")
    selected_plan: ResponsePlan = Field(description="Primary executable plan version")
    resolution_plan: ResolutionPlan = Field(description="Backwards-compatible legacy plan representation")
    status: str = Field(default="PLANNING", description="Operational workflow status")
    rationale: str = Field(default="", description="Planning rationale based on triage and priority")


class AdaptiveRecoveryOutput(BaseModel):
    """Validated output from Agent 5: Adaptive Recovery."""
    model_config = ConfigDict(use_enum_values=True)

    incident_id: str = Field(description="Incident ID")
    recovery_attempted: bool = Field(default=True)
    previous_plan_id: Optional[str] = Field(default=None)
    revised_plan: Optional[ResponsePlan] = Field(default=None, description="Materially revised plan addressing failure")
    resolution_plan: Optional[ResolutionPlan] = Field(default=None, description="Backwards-compatible legacy plan representation")
    failure_reason: str = Field(description="Original failure mode triggering recovery")
    selected_alternative: Optional[str] = Field(default=None, description="Selected alternative resource/action")
    rejected_alternatives: List[Dict[str, Any]] = Field(default_factory=list, description="Alternatives rejected as unsafe/unavailable")
    constraints: List[str] = Field(default_factory=list, description="Derived constraints from the failure reason")
    retry_count: int = Field(default=1, description="Current recovery retry iteration")
    status: str = Field(default="REPLANNING", description="Operational workflow status")
    escalated_to_human: bool = Field(default=False, description="True if retry limit reached or no alternatives exist")
    rationale: str = Field(default="", description="Rationale explaining why the alternative was chosen")


class IndependentVerificationOutput(BaseModel):
    """Validated output from Agent 6: Independent Verification."""
    model_config = ConfigDict(use_enum_values=True)

    incident_id: str = Field(description="Incident ID")
    verification_result: VerificationResult = Field(description="Typed independent verification result")
    status: str = Field(description="Operational workflow status")
    passed: bool = Field(default=False, description="True only if closure criteria and evidence verified")
    outcome: str = Field(description="VERIFIED, REJECTED_INSUFFICIENT_EVIDENCE, REJECTED_INCOMPLETE_ACTION, HUMAN_REVIEW_REQUIRED")
    rejection_reasons: List[str] = Field(default_factory=list)
    closure_verified: bool = Field(default=False, description="True if incident meets criteria for VERIFIED_CLOSED")
