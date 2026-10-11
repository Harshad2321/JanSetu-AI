import operator
from typing import TypedDict, List, Optional, Any, Annotated
from app.schemas.incident import (
    IncidentExtraction,
    PhotoEvidenceAnalysis,
    IncidentLocation,
    GeoAnalysis,
    PriorityAssessment,
    ResolutionPlan,
    ValidationDecision,
    ClosureEvidence,
    AuditEvent
)

class IncidentState(TypedDict, total=False):
    incident_id: str
    raw_input: str
    
    # Citizen input extensions
    selected_category: Optional[str]
    location_data: Optional[Any]
    image_base64: Optional[str]
    image_bytes: Optional[bytes]
    simulation_mode: Optional[bool]
    simulated_outcome: Optional[str]
    injected_critic_verdict: Optional[Any]
    allow_unverified_triage: Optional[bool]
    allow_closure_recovery: Optional[bool]
    
    # Outputs from agents
    extracted_facts: Optional[IncidentExtraction]
    evidence_analysis: Optional[PhotoEvidenceAnalysis]
    evidence_status: Optional[str]
    geo_context: Optional[GeoAnalysis]
    priority: Optional[PriorityAssessment]
    current_plan: Optional[ResolutionPlan]
    validation: Optional[ValidationDecision]
    closure_evidence: Optional[ClosureEvidence]
    synthetic_closure_evidence: Optional[Any]
    
    # Internal state tracking
    status: str # NEW, RECORDED_PENDING_REVIEW, AWAITING_CLARIFICATION, AWAITING_HUMAN_REVIEW, AWAITING_EVIDENCE_RETAKE, TRIAGED, PLANNING, VALIDATING, SIMULATING, VERIFYING_CLOSURE, RECOVERING, ESCALATED, SIMULATED_RESOLVED, CLOSURE_BLOCKED, RESOLVED, DUPLICATE
    retry_count: int
    audit_timeline: Annotated[List[AuditEvent], operator.add]
    
    # Simulation context for mock failures
    simulation_result: Optional[str]
    failure_reason: Optional[str]
