from typing import List, Optional
from pydantic import BaseModel, Field

class IncidentExtraction(BaseModel):
    category: str = Field(description="The category of the incident, e.g., 'pothole', 'waterlogging', 'garbage'")
    severity_indicators: List[str] = Field(description="Clues about the severity from the text, e.g., 'damaged two cars', 'deep'")
    missing_info: List[str] = Field(description="Important information missing from the report")
    confidence_score: float = Field(description="Confidence in the extraction, 0.0 to 1.0")

class GeoAnalysis(BaseModel):
    nearby_incident_ids: List[str] = Field(description="IDs of nearby incidents")
    is_duplicate: bool = Field(description="True if this is likely a duplicate report")
    duplicate_of_id: Optional[str] = Field(default=None, description="ID of the original incident if duplicate")

class PriorityAssessment(BaseModel):
    priority_score: int = Field(description="Priority score from 0 to 100")
    priority_band: str = Field(description="Band: 'Low', 'Medium', 'High', or 'Critical'")
    explanation: str = Field(description="Reasoning for this priority assessment")

class ResolutionPlan(BaseModel):
    mitigation_steps: List[str] = Field(description="Immediate steps to reduce harm")
    permanent_repair_steps: List[str] = Field(description="Steps for the permanent fix")
    required_resources: List[str] = Field(description="Equipment or materials needed")
    assigned_roles: List[str] = Field(description="Roles or crews needed, e.g., 'Traffic Control', 'Paving Crew'")
    closure_criteria: List[str] = Field(description="Conditions that must be met to close the incident")

class RevisedPlan(BaseModel):
    new_steps: List[str] = Field(description="Alternative mitigation or repair steps")
    new_resources: List[str] = Field(description="Updated resources needed")
    escalation_required: bool = Field(description="True if the incident cannot be resolved with available resources")
    reasoning: str = Field(description="Explanation of the revised plan or escalation")

class ValidationDecision(BaseModel):
    status: str = Field(description="'APPROVE', 'REJECT', or 'ESCALATE'")
    feedback: str = Field(description="Feedback or reason for rejection/escalation")

class AuditEvent(BaseModel):
    timestamp: str
    agent: str
    action: str
    result: str
