"""
JanSetu AI — Schemas & Data Contracts Test Suite.

Validates:
- Valid and invalid latitude / longitude values and boundary conditions
- Mandatory coordinate pairing and accuracy bounds
- Missing optional photographs and non-mandatory evidence handling
- Independent decoupling of evidence status and operational status
- Status combination constraints (e.g. no phantom resolution without verification)
- Normalization of priority bands and critic decision statuses
- Serialization and deserialization round-trips of all core Pydantic models
"""

import pytest
from pydantic import ValidationError

from app.schemas.incident import (
    # Enums
    IncidentCategory,
    OperationalStatus,
    EvidenceOutcome,
    LocationSource,
    PriorityBand,
    CriticVerdictStatus,
    ImageQualityAssessment,
    EvidenceRecommendation,
    ToolExecutionStatus,
    
    # Models
    IncidentLocation,
    CitizenComplaint,
    IncidentSubmissionRequest,
    IncidentExtraction,
    PhotoEvidenceAnalysis,
    GeoAnalysis,
    PriorityAssessment,
    ResolutionPlan,
    RevisedPlan,
    ValidationDecision,
    CriticVerdict,
    ClosureEvidence,
    ToolExecutionResult,
    AgentExecutionTrace,
    AuditEvent,
    SharedWorkflowCaseState,
)


# ============================================================================
# 1. Geographic Location Tests
# ============================================================================

def test_valid_location_coordinates():
    """Ensure valid coordinates with accuracy and source instantiate correctly."""
    loc = IncidentLocation(
        latitude=28.6139,
        longitude=77.2090,
        accuracy_meters=8.5,
        source=LocationSource.DEVICE_GPS,
        address_text="Barakhamba Road, Connaught Place, New Delhi",
        is_user_confirmed=True,
    )
    assert loc.latitude == 28.6139
    assert loc.longitude == 77.2090
    assert loc.accuracy_meters == 8.5
    assert loc.source == LocationSource.DEVICE_GPS
    assert loc.is_user_confirmed is True


def test_location_boundary_values():
    """Ensure coordinate extremes (-90, 90, -180, 180) are accepted."""
    loc1 = IncidentLocation(latitude=-90.0, longitude=-180.0)
    assert loc1.latitude == -90.0
    assert loc1.longitude == -180.0

    loc2 = IncidentLocation(latitude=90.0, longitude=180.0)
    assert loc2.latitude == 90.0
    assert loc2.longitude == 180.0


def test_invalid_latitude_out_of_bounds():
    """Ensure latitude beyond [-90, 90] raises ValidationError."""
    with pytest.raises(ValidationError) as exc:
        IncidentLocation(latitude=90.1, longitude=77.0)
    assert "Latitude must be between -90.0 and 90.0" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        IncidentLocation(latitude=-90.1, longitude=77.0)
    assert "Latitude must be between -90.0 and 90.0" in str(exc.value)


def test_invalid_longitude_out_of_bounds():
    """Ensure longitude beyond [-180, 180] raises ValidationError."""
    with pytest.raises(ValidationError) as exc:
        IncidentLocation(latitude=28.0, longitude=180.5)
    assert "Longitude must be between -180.0 and 180.0" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        IncidentLocation(latitude=28.0, longitude=-180.5)
    assert "Longitude must be between -180.0 and 180.0" in str(exc.value)


def test_coordinate_pair_enforcement():
    """Ensure latitude and longitude must either both be provided, or both omitted."""
    # Latitude provided alone
    with pytest.raises(ValidationError) as exc1:
        IncidentLocation(latitude=28.0, longitude=None)
    assert "Both latitude and longitude must be provided together" in str(exc1.value)

    # Longitude provided alone
    with pytest.raises(ValidationError) as exc2:
        IncidentLocation(latitude=None, longitude=77.0)
    assert "Both latitude and longitude must be provided together" in str(exc2.value)

    # Both omitted is fully valid (e.g. manual address description only)
    loc_manual = IncidentLocation(
        address_text="Opposite Central Market, Sector 15",
        source=LocationSource.MANUAL_ENTRY,
    )
    assert loc_manual.latitude is None
    assert loc_manual.longitude is None
    assert loc_manual.source == LocationSource.MANUAL_ENTRY


def test_negative_accuracy_rejected():
    """Ensure accuracy in meters cannot be negative."""
    with pytest.raises(ValidationError):
        IncidentLocation(latitude=28.0, longitude=77.0, accuracy_meters=-5.0)


def test_location_sources_supported():
    """Ensure all required location sources are supported."""
    sources = [
        LocationSource.DEVICE_GPS,
        LocationSource.USER_PIN_ADJUSTED,
        LocationSource.MANUAL_ENTRY,
        LocationSource.REVERSE_GEOCODED,
    ]
    for src in sources:
        loc = IncidentLocation(source=src)
        assert loc.source == src


# ============================================================================
# 2. Citizen Complaint & Missing Photograph Tests
# ============================================================================

def test_complaint_without_photograph():
    """Ensure complaints without photos are valid, recorded, and not rejected."""
    complaint = CitizenComplaint(
        description="Deep pothole on main road causing severe traffic backup.",
        reported_category=IncidentCategory.POTHOLE,
        has_photograph=False,
    )
    assert complaint.description.startswith("Deep pothole")
    assert complaint.reported_category == IncidentCategory.POTHOLE
    assert complaint.has_photograph is False
    assert complaint.location.source == LocationSource.MANUAL_ENTRY


def test_complaint_description_length_bounds():
    """Ensure complaints with inadequate length (< 5 chars) or excessive length (> 2000) fail."""
    with pytest.raises(ValidationError):
        CitizenComplaint(description="Bad")  # Too short

    with pytest.raises(ValidationError):
        CitizenComplaint(description="A" * 2001)  # Too long


def test_submission_request_serialization():
    """Ensure IncidentSubmissionRequest serializes cleanly with optional image and failure hook."""
    req = IncidentSubmissionRequest(
        complaint="Flooded underpass near city hospital.",
        category=IncidentCategory.WATERLOGGING,
        location=IncidentLocation(latitude=19.0760, longitude=72.8777, source=LocationSource.DEVICE_GPS),
        image_base64=None,
        failure_reason="simulated_pump_failure",
    )
    dumped = req.model_dump()
    assert dumped["category"] == "waterlogging"
    assert dumped["image_base64"] is None
    assert dumped["failure_reason"] == "simulated_pump_failure"


# ============================================================================
# 3. Status Decoupling & Combination Tests
# ============================================================================

def test_evidence_and_operational_status_decoupling():
    """
    Ensure evidence status and operational status are distinct and can coexist
    in legitimate operational permutations without collapsing into one.
    """
    base_complaint = CitizenComplaint(
        description="Garbage piling up outside commercial complex.",
        reported_category=IncidentCategory.GARBAGE,
    )

    # 1. Fresh complaint with matched photo in triage
    state1 = SharedWorkflowCaseState(
        incident_id="INC-001",
        complaint=base_complaint,
        operational_status=OperationalStatus.TRIAGED,
        evidence_status=EvidenceOutcome.MATCHED,
    )
    assert state1.operational_status == OperationalStatus.TRIAGED
    assert state1.evidence_status == EvidenceOutcome.MATCHED

    # 2. Complaint without photo awaiting field review
    state2 = SharedWorkflowCaseState(
        incident_id="INC-002",
        complaint=base_complaint,
        operational_status=OperationalStatus.RECORDED_PENDING_REVIEW,
        evidence_status=EvidenceOutcome.NOT_PROVIDED,
    )
    assert state2.operational_status == OperationalStatus.RECORDED_PENDING_REVIEW
    assert state2.evidence_status == EvidenceOutcome.NOT_PROVIDED

    # 3. Mismatched photo awaiting citizen clarification
    state3 = SharedWorkflowCaseState(
        incident_id="INC-003",
        complaint=base_complaint,
        operational_status=OperationalStatus.AWAITING_CLARIFICATION,
        evidence_status=EvidenceOutcome.MISMATCH,
    )
    assert state3.operational_status == OperationalStatus.AWAITING_CLARIFICATION
    assert state3.evidence_status == EvidenceOutcome.MISMATCH

    # 4. Low quality photo awaiting retake
    state4 = SharedWorkflowCaseState(
        incident_id="INC-004",
        complaint=base_complaint,
        operational_status=OperationalStatus.AWAITING_EVIDENCE_RETAKE,
        evidence_status=EvidenceOutcome.LOW_QUALITY,
    )
    assert state4.operational_status == OperationalStatus.AWAITING_EVIDENCE_RETAKE
    assert state4.evidence_status == EvidenceOutcome.LOW_QUALITY


def test_cannot_mark_resolved_solely_on_matched_photo():
    """
    Constraint check: A photo being MATCHED does not permit operational_status=RESOLVED
    unless a resolution plan and closure evidence are present.
    """
    complaint = CitizenComplaint(description="Major pothole on highway.")
    
    with pytest.raises(ValidationError) as exc:
        SharedWorkflowCaseState(
            incident_id="INC-005",
            complaint=complaint,
            operational_status=OperationalStatus.RESOLVED,
            evidence_status=EvidenceOutcome.MATCHED,
            # No plan, no closure evidence!
        )
    assert "Incident cannot be marked RESOLVED solely because photograph is MATCHED" in str(exc.value)


def test_valid_resolved_state_with_closure_evidence():
    """Ensure resolved state is accepted when closure evidence or resolution plan is attached."""
    complaint = CitizenComplaint(description="Major pothole on highway.")
    closure = ClosureEvidence(
        incident_id="INC-006",
        closure_criteria_met=["Pothole filled", "Asphalt compacted", "Traffic flow restored"],
        is_ready_for_closure=True,
    )
    state = SharedWorkflowCaseState(
        incident_id="INC-006",
        complaint=complaint,
        operational_status=OperationalStatus.RESOLVED,
        evidence_status=EvidenceOutcome.MATCHED,
        closure_evidence=closure,
    )
    assert state.operational_status == OperationalStatus.RESOLVED
    assert state.closure_evidence.is_ready_for_closure is True


# ============================================================================
# 4. Core Model Validation & Round-Trip Tests
# ============================================================================

def test_incident_extraction_model():
    """Ensure IncidentExtraction accepts severity and public exposure clues."""
    ext = IncidentExtraction(
        category="pothole",
        severity_indicators=["crater depth 15cm", "vehicle suspension damage"],
        missing_info=["exact landmark"],
        confidence_score=0.92,
        public_exposure_clues=["arterial corridor", "high pedestrian volume"],
        extracted_location_clues="Near City Center Metro",
    )
    dumped = ext.model_dump()
    assert dumped["category"] == "pothole"
    assert len(dumped["severity_indicators"]) == 2
    assert dumped["confidence_score"] == 0.92
    assert ext.public_exposure_clues[0] == "arterial corridor"


def test_photo_evidence_analysis_model():
    """Ensure PhotoEvidenceAnalysis enforces disclaimers and recommendation enums."""
    analysis = PhotoEvidenceAnalysis(
        detected_category="pothole",
        visible_evidence="Cavity in wearing course with loose aggregate",
        relevance_score=0.95,
        image_quality=ImageQualityAssessment.GOOD,
        confidence_score=0.88,
        recommendation=EvidenceRecommendation.PROCEED,
        outcome=EvidenceOutcome.MATCHED,
    )
    assert analysis.outcome == EvidenceOutcome.MATCHED
    assert analysis.recommendation == EvidenceRecommendation.PROCEED
    assert "AI visual triage only" in analysis.authenticity_disclaimer


def test_geo_analysis_model():
    """Ensure GeoAnalysis records nearby records and duplicate candidate links."""
    geo = GeoAnalysis(
        nearby_incident_ids=["INC-1002", "INC-0998"],
        is_duplicate=True,
        duplicate_of_id="INC-1002",
        distance_to_nearest_meters=18.4,
        duplicate_confidence=0.91,
    )
    assert geo.is_duplicate is True
    assert geo.duplicate_of_id == "INC-1002"
    assert geo.distance_to_nearest_meters == 18.4


def test_priority_assessment_model():
    """Ensure PriorityAssessment normalizes band names and checks bounds."""
    pri = PriorityAssessment(
        priority_score=85,
        priority_band="high",  # Lowercase should normalize to "High"
        explanation="Near busy hospital arterial intersection during peak hours.",
        urgency_factors=["Emergency vehicle corridor", "Active transit route"],
    )
    assert pri.priority_score == 85
    assert pri.priority_band == "High"
    assert len(pri.urgency_factors) == 2

    # Test out of bounds
    with pytest.raises(ValidationError):
        PriorityAssessment(priority_score=105, explanation="invalid")

    with pytest.raises(ValidationError):
        PriorityAssessment(priority_score=-1, explanation="invalid")


def test_critic_verdict_validation():
    """Ensure CriticVerdict enforces valid decision statuses (APPROVE, REJECT, ESCALATE)."""
    v1 = CriticVerdict(
        status="approve",  # Case insensitive validation to APPROVE
        feedback="Plan complies with municipal safety policies.",
        safety_check_passed=True,
    )
    assert v1.status == "APPROVE"

    v2 = CriticVerdict(status="REJECT", feedback="Lacks traffic barricades.")
    assert v2.status == "REJECT"

    v3 = CriticVerdict(status="ESCALATE", feedback="Structural bridge damage detected.")
    assert v3.status == "ESCALATE"

    with pytest.raises(ValidationError):
        CriticVerdict(status="INVALID_STATUS", feedback="error")


def test_closure_evidence_model():
    """Ensure ClosureEvidence handles verification criteria and inspector notes."""
    closure = ClosureEvidence(
        incident_id="INC-100",
        closure_criteria_met=["Debris cleared"],
        outstanding_criteria=["Surface sanitized"],
        is_ready_for_closure=False,
        inspector_notes="Awaiting sanitary crew sign-off",
    )
    assert closure.is_ready_for_closure is False
    assert len(closure.outstanding_criteria) == 1


def test_tool_execution_result_model():
    """Ensure ToolExecutionResult captures status and duration."""
    tool = ToolExecutionResult(
        tool_name="haversine_proximity_calculator",
        status=ToolExecutionStatus.SUCCESS,
        output_summary="Calculated distance: 22.4 meters",
        execution_time_ms=1.4,
    )
    assert tool.status == ToolExecutionStatus.SUCCESS
    assert tool.execution_time_ms == 1.4


def test_full_shared_workflow_state_roundtrip_serialization():
    """Ensure full SharedWorkflowCaseState can serialize to JSON and deserialize back losslessly."""
    complaint = CitizenComplaint(
        complaint_id="INC-777",
        description="Large water accumulation blocking arterial road lane.",
        reported_category=IncidentCategory.WATERLOGGING,
        location=IncidentLocation(
            latitude=28.5355,
            longitude=77.3910,
            accuracy_meters=12.0,
            source=LocationSource.DEVICE_GPS,
            address_text="Noida Expressway Sector 128",
            is_user_confirmed=True,
        ),
        has_photograph=True,
    )
    
    state = SharedWorkflowCaseState(
        incident_id="INC-777",
        complaint=complaint,
        operational_status=OperationalStatus.PLANNING,
        evidence_status=EvidenceOutcome.MATCHED,
        extracted_facts=IncidentExtraction(
            category="waterlogging",
            severity_indicators=["lane blocked", "30cm water depth"],
            confidence_score=0.95,
        ),
        priority=PriorityAssessment(
            priority_score=78,
            priority_band="High",
            explanation="Arterial highway lane closure risking gridlock.",
        ),
        current_plan=ResolutionPlan(
            mitigation_steps=["Deploy warning cones 100m upstream"],
            permanent_repair_steps=["Clear culvert blockage with high-pressure jet"],
            required_resources=["1x High-capacity suction pump", "3x Traffic safety cones"],
            assigned_roles=["Stormwater Drainage Crew", "Traffic Police Liaison"],
            closure_criteria=["Water drained from all travel lanes", "Catch basin running clear"],
        ),
        audit_timeline=[
            AuditEvent(timestamp="2026-10-11T15:00:00Z", agent="Incident Intelligence", action="Fact Extraction", result="Category: waterlogging"),
            AuditEvent(timestamp="2026-10-11T15:00:02Z", agent="Priority Intelligence", action="Risk Scoring", result="Score: 78 / Band: High"),
        ],
        retry_count=0,
    )

    # Serialize to JSON string
    json_data = state.model_dump_json()
    assert "INC-777" in json_data
    assert "waterlogging" in json_data
    assert "Noida Expressway" in json_data

    # Deserialize back from JSON string
    restored = SharedWorkflowCaseState.model_validate_json(json_data)
    assert restored.incident_id == state.incident_id
    assert restored.operational_status == state.operational_status
    assert restored.evidence_status == state.evidence_status
    assert restored.complaint.location.latitude == 28.5355
    assert restored.priority.priority_score == 78
    assert len(restored.audit_timeline) == 2
    assert restored.current_plan.mitigation_steps[0] == "Deploy warning cones 100m upstream"
