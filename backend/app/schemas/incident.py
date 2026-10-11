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
from typing import List, Optional, Any
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
    """
    NEW = "NEW"
    RECORDED_PENDING_REVIEW = "RECORDED_PENDING_REVIEW"
    AWAITING_CLARIFICATION = "AWAITING_CLARIFICATION"
    AWAITING_HUMAN_REVIEW = "AWAITING_HUMAN_REVIEW"
    AWAITING_EVIDENCE_RETAKE = "AWAITING_EVIDENCE_RETAKE"
    TRIAGED = "TRIAGED"
    PLANNING = "PLANNING"
    VALIDATING = "VALIDATING"
    SIMULATING = "SIMULATING"
    VERIFYING_CLOSURE = "VERIFYING_CLOSURE"
    RECOVERING = "RECOVERING"
    ESCALATED = "ESCALATED"
    SIMULATED_RESOLVED = "SIMULATED_RESOLVED"
    CLOSURE_BLOCKED = "CLOSURE_BLOCKED"
    RESOLVED = "RESOLVED"
    DUPLICATE = "DUPLICATE"


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


# ============================================================================
# Agent Output Schemas (Preserving backward compatibility)
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


class AuditEvent(BaseModel):
    """Immutable audit trail event record."""
    model_config = ConfigDict(use_enum_values=True)

    timestamp: str = Field(description="Event timestamp")
    agent: str = Field(description="Agent or system component name")
    action: str = Field(description="Action executed")
    result: str = Field(description="Action result or status summary")


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
