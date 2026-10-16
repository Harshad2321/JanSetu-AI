/**
 * JanSetu AI — Centralized REST API Service.
 * Connects to the FastAPI backend with structured error parsing and timeout management.
 */

import type {
  DashboardSummary,
  HealthResponse,
  Incident,
  IncidentListResponse,
  SupportedScenario,
  WorkflowRunResponse,
  AgentExecutionTrace,
  AuditEvent,
} from '../types/api';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      } else if (errJson && errJson.error) {
        errorDetail = errJson.error;
      }
    } catch {
      // Non-JSON error body
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  getBaseUrl(): string {
    return API_BASE_URL;
  },

  getIncidentPhotoUrl(incidentId: string): string {
    return `${API_BASE_URL}/api/v1/incidents/${incidentId}/photo`;
  },

  async getHealth(): Promise<HealthResponse> {
    const res = await fetch(`${API_BASE_URL}/health`);
    return handleResponse<HealthResponse>(res);
  },

  async getDashboardSummary(): Promise<DashboardSummary> {
    const res = await fetch(`${API_BASE_URL}/api/v1/dashboard/summary`);
    return handleResponse<DashboardSummary>(res);
  },

  async getIncidents(params?: {
    status?: string;
    category?: string;
    evidence_status?: string;
    limit?: number;
    offset?: number;
  }): Promise<IncidentListResponse> {
    const url = new URL(`${API_BASE_URL}/api/v1/incidents`);
    if (params) {
      if (params.status) url.searchParams.set('status', params.status);
      if (params.category) url.searchParams.set('category', params.category);
      if (params.evidence_status) url.searchParams.set('evidence_status', params.evidence_status);
      if (params.limit) url.searchParams.set('limit', String(params.limit));
      if (params.offset) url.searchParams.set('offset', String(params.offset));
    }
    const res = await fetch(url.toString());
    return handleResponse<IncidentListResponse>(res);
  },

  async getIncident(incidentId: string): Promise<Incident> {
    const res = await fetch(`${API_BASE_URL}/api/v1/incidents/${incidentId}`);
    return handleResponse<Incident>(res);
  },

  async createIncident(formData: FormData): Promise<Incident> {
    const res = await fetch(`${API_BASE_URL}/api/v1/incidents`, {
      method: 'POST',
      body: formData,
      // Note: Do not set Content-Type header when sending FormData; browser sets it with correct boundary automatically
    });
    return handleResponse<Incident>(res);
  },

  async runWorkflow(
    incidentId: string,
    options?: { simulation_scenario?: string; failure_reason?: string; allow_unverified_triage?: boolean }
  ): Promise<WorkflowRunResponse> {
    const res = await fetch(`${API_BASE_URL}/api/v1/incidents/${incidentId}/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        allow_unverified_triage: true,
        ...(options || {}),
      }),
    });
    return handleResponse<WorkflowRunResponse>(res);
  },

  async simulateScenario(
    incidentId: string,
    scenario: SupportedScenario
  ): Promise<WorkflowRunResponse> {
    const res = await fetch(`${API_BASE_URL}/api/v1/incidents/${incidentId}/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario }),
    });
    return handleResponse<WorkflowRunResponse>(res);
  },

  async getTraces(incidentId: string): Promise<AgentExecutionTrace[]> {
    const res = await fetch(`${API_BASE_URL}/api/v1/incidents/${incidentId}/trace`);
    return handleResponse<AgentExecutionTrace[]>(res);
  },

  async getAudit(incidentId: string): Promise<AuditEvent[]> {
    const res = await fetch(`${API_BASE_URL}/api/v1/incidents/${incidentId}/audit`);
    return handleResponse<AuditEvent[]>(res);
  },

  async getIncidentTwin(incidentId: string): Promise<import('../types/api').CivicIncidentTwin> {
    const res = await fetch(`${API_BASE_URL}/api/v1/incidents/${incidentId}/twin`);
    return handleResponse<import('../types/api').CivicIncidentTwin>(res);
  },

  async getMLMetrics(): Promise<import('../types/api').MLMetricsResponse> {
    const res = await fetch(`${API_BASE_URL}/api/v1/ml/metrics`);
    return handleResponse<import('../types/api').MLMetricsResponse>(res);
  },

  async predictComplaint(text: string): Promise<import('../types/api').MLPredictResponse> {
    const res = await fetch(`${API_BASE_URL}/api/v1/ml/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    return handleResponse<import('../types/api').MLPredictResponse>(res);
  },
};

