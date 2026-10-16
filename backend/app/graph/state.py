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

def _resolve_correlation_id(a: Optional[str], b: Optional[str]) -> Optional[str]:
    return a or b

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
    verification_result: Optional[Any]
    
    # Internal state tracking
    status: str # NEW, SUBMITTED, NEEDS_CLARIFICATION, CLASSIFIED, TRIAGED, PLANNING, VALIDATING, SIMULATING, VERIFYING_CLOSURE, AWAITING_VERIFICATION, VERIFIED_CLOSED, SIMULATED_RESOLVED, CLOSURE_BLOCKED, RECOVERING, ESCALATED, HUMAN_REVIEW
    retry_count: int
    correlation_id: Annotated[Optional[str], _resolve_correlation_id]
    target_closed_status: Optional[str]
    requires_human_signoff: Optional[bool]
    supervisor_signoff: Optional[bool]
    is_escalated: Optional[bool]
    escalation_reasons: Optional[List[str]]
    audit_timeline: Annotated[List[AuditEvent], operator.add]
    
    # Simulation context for mock failures
    simulation_result: Optional[str]
    simulation_scenario: Optional[Any]
    simulation_seed: Optional[int]
    failure_reason: Optional[str]
