"""
JanSetu AI — REST API Request & Response Schemas.

Defines client contracts for:
- Health check and configuration status
- Dashboard aggregates and metric distributions
- Incident submission, listing, filtering, and detail representation
- Workflow execution parameters and run outputs
- Simulation scenario control and audit trail inspection
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.incident import (
    AgentExecutionTrace,
    AuditEvent,
    ClosureEvidence,
    EvidenceOutcome,
    GeoAnalysis,
    IncidentCategory,
    IncidentExtraction,
    IncidentLocation,
    OperationalStatus,
    PhotoEvidenceAnalysis,
    PriorityAssessment,
    ResolutionPlan,
    ValidationDecision,
)


class SupportedScenario(str, Enum):
    """Documented deterministic simulation scenarios for React UI demonstration."""
    NORMAL = "normal"
    CREW_UNAVAILABLE = "crew_unavailable"
    MATERIALS_UNAVAILABLE = "materials_unavailable"
    CRITIC_REJECTION = "critic_rejection"
    INSUFFICIENT_CLOSURE_EVIDENCE = "insufficient_closure_evidence"
    RETRY_EXHAUSTION = "retry_exhaustion"


# ============================================================================
# General & Health Schemas
# ============================================================================

class HealthResponse(BaseModel):
    """Service health response without exposing sensitive keys."""
    model_config = ConfigDict(use_enum_values=True)

    status: str = Field(default="healthy")
    service: str = Field(default="JanSetu AI Backend")
    environment: str = Field(default="development")
    database: str = Field(default="connected")
    groq_configured: bool = Field(default=False)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class APIErrorResponse(BaseModel):
    """Standardized error envelope preventing raw internal stacktrace leakage."""
    error: str = Field(description="Error type or summary")
    detail: str = Field(description="Human-readable safe explanation")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============================================================================
# Dashboard Aggregates
# ============================================================================

class DashboardSummaryResponse(BaseModel):
    """High-level metrics for civic operations and triage distribution."""
    total_incidents: int = Field(default=0, ge=0)
    operational_statuses: Dict[str, int] = Field(default_factory=dict)
    evidence_statuses: Dict[str, int] = Field(default_factory=dict)
    categories: Dict[str, int] = Field(default_factory=dict)
    priority_bands: Dict[str, int] = Field(default_factory=dict)


# ============================================================================
# Incident Intake & Detail Schemas
# ============================================================================

class IncidentResponse(BaseModel):
    """Comprehensive incident state representation."""
    model_config = ConfigDict(use_enum_values=True)

    incident_id: str
    complaint: str
    category: IncidentCategory
    location: IncidentLocation
    has_photograph: bool
    operational_status: OperationalStatus
    evidence_status: EvidenceOutcome
    extracted_facts: Optional[IncidentExtraction] = None
    evidence_analysis: Optional[PhotoEvidenceAnalysis] = None
    geo_context: Optional[GeoAnalysis] = None
    priority: Optional[PriorityAssessment] = None
    current_plan: Optional[ResolutionPlan] = None
    validation: Optional[ValidationDecision] = None
    closure_evidence: Optional[ClosureEvidence] = None
    simulation_result: Optional[str] = None
    failure_reason: Optional[str] = None
    retry_count: int = 0
    agent_traces: List[AgentExecutionTrace] = Field(default_factory=list)
    audit_timeline: List[AuditEvent] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class IncidentListResponse(BaseModel):
    """Paginated incident list container."""
    total: int = Field(default=0, ge=0)
    items: List[IncidentResponse] = Field(default_factory=list)


# ============================================================================
# Workflow & Simulation Schemas
# ============================================================================

class WorkflowRunRequest(BaseModel):
    """Execution options for LangGraph agent orchestration."""
    model_config = ConfigDict(use_enum_values=True)

    failure_reason: Optional[str] = Field(
        default=None,
        description="Optional failure reason to inject into intervention simulator",
    )
    simulation_scenario: Optional[SupportedScenario] = Field(
        default=None,
        description="Named simulation scenario: normal, crew_unavailable, materials_unavailable, etc.",
    )
    allow_unverified_triage: Optional[bool] = Field(
        default=False,
        description="Override to proceed to planning without matched photo (remains recorded pending review)",
    )
    allow_closure_recovery: Optional[bool] = Field(
        default=False,
        description="Allow recovery routing when closure evidence is insufficient",
    )


class WorkflowRunResponse(BaseModel):
    """Results returned from workflow execution."""
    model_config = ConfigDict(use_enum_values=True)

    incident_id: str
    operational_status: OperationalStatus
    evidence_status: EvidenceOutcome
    is_simulated_resolution: bool = False
    simulation_scenario: Optional[str] = None
    current_plan: Optional[ResolutionPlan] = None
    validation: Optional[ValidationDecision] = None
    closure_evidence: Optional[ClosureEvidence] = None
    agent_traces: List[AgentExecutionTrace] = Field(default_factory=list)
    audit_timeline: List[AuditEvent] = Field(default_factory=list)
    message: str = "Workflow executed."


class SimulationScenarioRequest(BaseModel):
    """Targeted failure scenario selection for demonstration."""
    model_config = ConfigDict(use_enum_values=True)

    scenario: SupportedScenario = Field(
        ...,
        description="Scenario to trigger: normal, crew_unavailable, materials_unavailable, etc.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional operator notes describing the test context",
    )
