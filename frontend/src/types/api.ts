/**
 * JanSetu AI — Frontend TypeScript API & Domain Types.
 * Strictly aligned with FastAPI Pydantic contracts and LangGraph state models.
 */

export type IncidentCategory = 'pothole' | 'waterlogging' | 'garbage' | 'uncertain_other';

export type OperationalStatus =
  | 'NEW'
  | 'RECORDED_PENDING_REVIEW'
  | 'AWAITING_CLARIFICATION'
  | 'AWAITING_HUMAN_REVIEW'
  | 'AWAITING_EVIDENCE_RETAKE'
  | 'TRIAGED'
  | 'PLANNING'
  | 'VALIDATING'
  | 'SIMULATING'
  | 'VERIFYING_CLOSURE'
  | 'RECOVERING'
  | 'ESCALATED'
  | 'SIMULATED_RESOLVED'
  | 'CLOSURE_BLOCKED'
  | 'RESOLVED'
  | 'DUPLICATE';

export type EvidenceOutcome =
  | 'MATCHED'
  | 'MISMATCH'
  | 'INCONCLUSIVE'
  | 'LOW_QUALITY'
  | 'NOT_PROVIDED';

export type LocationSource =
  | 'DEVICE_GPS'
  | 'USER_PIN_ADJUSTED'
  | 'MANUAL_ENTRY'
  | 'REVERSE_GEOCODED';

export type PriorityBand = 'Low' | 'Medium' | 'High' | 'Critical';

export type SupportedScenario =
  | 'normal'
  | 'crew_unavailable'
  | 'materials_unavailable'
  | 'critic_rejection'
  | 'insufficient_closure_evidence'
  | 'retry_exhaustion';

export interface IncidentLocation {
  latitude?: number | null;
  longitude?: number | null;
  accuracy_meters?: number | null;
  source: LocationSource;
  address_text?: string | null;
  timestamp?: string | null;
  is_user_confirmed: boolean;
}

export interface IncidentExtraction {
  category: IncidentCategory;
  primary_defect: string;
  severity_indicators: string[];
  public_exposure_clues: string[];
  extracted_location_clues?: string | null;
  missing_information: string[];
  confidence_score: number;
}

export interface PhotoEvidenceAnalysis {
  detected_category: string;
  visible_evidence: string;
  relevance_score: number;
  image_quality: string;
  confidence_score: number;
  recommendation: string;
  outcome: EvidenceOutcome;
  quality_explanation?: string | null;
  authenticity_disclaimer?: string | null;
}

export interface NearbyCandidate {
  incident_id: string;
  distance_meters: number;
  category: string;
  status: string;
  match_confidence: number;
  rationale: string;
}

export interface GeoAnalysis {
  nearby_incident_ids: string[];
  is_duplicate: boolean;
  duplicate_of_id?: string | null;
  distance_to_nearest_meters?: number | null;
  duplicate_confidence: number;
  duplicate_candidates?: NearbyCandidate[];
  spatial_uncertainty_explanation?: string | null;
}

export interface PriorityAssessment {
  priority_score: number;
  priority_band: PriorityBand;
  explanation: string;
  severity_factor?: number;
  exposure_factor?: number;
  duration_factor?: number;
  recurrence_factor?: number;
}

export interface ResolutionPlan {
  plan_id?: string;
  incident_id?: string;
  mitigation_steps: string[];
  permanent_repair_steps: string[];
  allocated_resources: string[];
  responsible_roles: string[];
  required_approvals: string[];
  closure_criteria: string[];
  estimated_duration_hours?: number;
  resource_constraints?: string[];
  is_revised?: boolean;
}

export interface ValidationDecision {
  status: 'APPROVE' | 'REJECT' | 'ESCALATE';
  feedback: string;
  safety_check_passed: boolean;
  resource_check_passed: boolean;
  policy_violations?: string[];
  retry_count?: number;
}

export interface ClosureEvidence {
  incident_id: string;
  closure_criteria_met: string[];
  outstanding_criteria: string[];
  is_ready_for_closure: boolean;
  inspector_notes?: string | null;
  verified_at?: string | null;
}

export interface AuditEvent {
  timestamp: string;
  agent: string;
  action: string;
  result: string;
}

export interface AgentExecutionTrace {
  agent_name: string;
  start_time: string;
  end_time: string;
  input_summary: string;
  output_summary: string;
  status: string;
  retry_count: number;
}

export interface Incident {
  incident_id: string;
  complaint: string;
  category: IncidentCategory;
  location: IncidentLocation;
  has_photograph: boolean;
  operational_status: OperationalStatus;
  evidence_status: EvidenceOutcome;
  extracted_facts?: IncidentExtraction | null;
  evidence_analysis?: PhotoEvidenceAnalysis | null;
  geo_context?: GeoAnalysis | null;
  priority?: PriorityAssessment | null;
  current_plan?: ResolutionPlan | null;
  validation?: ValidationDecision | null;
  closure_evidence?: ClosureEvidence | null;
  simulation_result?: string | null;
  failure_reason?: string | null;
  retry_count: number;
  agent_traces: AgentExecutionTrace[];
  audit_timeline: AuditEvent[];
  created_at: string;
  updated_at: string;
}

export interface IncidentListResponse {
  total: number;
  items: Incident[];
}

export interface DashboardSummary {
  total_incidents: number;
  operational_statuses: Record<string, number>;
  evidence_statuses: Record<string, number>;
  categories: Record<string, number>;
  priority_bands: Record<string, number>;
}

export interface WorkflowRunResponse {
  incident_id: string;
  operational_status: OperationalStatus;
  evidence_status: EvidenceOutcome;
  is_simulated_resolution: boolean;
  simulation_scenario?: string | null;
  current_plan?: ResolutionPlan | null;
  validation?: ValidationDecision | null;
  closure_evidence?: ClosureEvidence | null;
  agent_traces: AgentExecutionTrace[];
  audit_timeline: AuditEvent[];
  message: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  environment: string;
  database: string;
  groq_configured: boolean;
  timestamp: string;
}
