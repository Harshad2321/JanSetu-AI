import operator
from typing import TypedDict, List, Optional, Any, Annotated
from app.schemas.incident import (
    IncidentExtraction,
    GeoAnalysis,
    PriorityAssessment,
    ResolutionPlan,
    ValidationDecision,
    AuditEvent
)

class IncidentState(TypedDict):
    incident_id: str
    raw_input: str
    
    # Outputs from agents
    extracted_facts: Optional[IncidentExtraction]
    geo_context: Optional[GeoAnalysis]
    priority: Optional[PriorityAssessment]
    current_plan: Optional[ResolutionPlan]
    validation: Optional[ValidationDecision]
    
    # Internal state tracking
    status: str # NEW, PLANNING, VALIDATING, SIMULATING, RECOVERING, ESCALATED, RESOLVED, DUPLICATE
    retry_count: int
    audit_timeline: Annotated[List[AuditEvent], operator.add]
    
    # Simulation context for mock failures
    simulation_result: Optional[str]
    failure_reason: Optional[str]
