# JanSetu AI — Citizen Incident Reporting & Evidence-Verification Workflow Plan

## 1. Executive Summary & Architectural Overview

JanSetu AI is an adaptive, multi-agent civic incident triage and remediation management system. This project plan specifies the upgrade to support a robust, privacy-respecting, and resilient **Citizen Incident Submission and Evidence-Verification Workflow**.

### Core Tenets & Architectural Decisions
1. **Preserve the 6-Specialist Agent Topology**: No seventh specialist agent is added. The existing **Incident Intelligence Agent** is extended to accept multimodal inputs (complaint description, selected category, and optional photograph).
2. **Dual-Status Architecture**:
   - **Evidence Verification Status**: `MATCHED`, `MISMATCH`, `INCONCLUSIVE`, `LOW_QUALITY`, `NOT_PROVIDED`.
   - **Operational Resolution Status**: `NEW`, `TRIAGED`, `PLANNING`, `VALIDATING`, `AWAITING_HUMAN_REVIEW`, `AWAITING_CLARIFICATION`, `SIMULATING`, `RECOVERING`, `RESOLVED`, `DUPLICATE`.
   Evidence status never collapses operational triage; a missing or inconclusive photo never causes silent deletion.
3. **Inclusive Intake**: Photographic proof is encouraged through UX affordances, but is **non-mandatory**. Reports filed without a photo receive a pending-evidence / human-review status and remain fully triaged.
4. **Current Groq Multimodal Capabilities**: Groq retired `llama-3.2-11b-vision-preview` and `llama-3.2-90b-vision-preview` on April 14, 2025. The active multimodal model supported on Groq is **`qwen/qwen3.8-27b`**, which supports structured JSON extraction, vision chat completions with base64/URL images, and explicit reasoning effort.
5. **Safety & Privacy Boundaries**:
   - Vision AI output is strictly an operational triage aid; it does not constitute legal proof of occurrence, exact GPS positioning, or physical authorization of repairs.
   - EXIF metadata is stripped on the backend to safeguard reporter privacy.
   - Groq credentials remain strictly server-side.

---

## 2. Citizen Incident Submission Flow (Frontend UX/UI)

### Visual Layout & Components (React + Vite + Tailwind CSS)

```
===================================================================================
 JANSETU AI  |  Citizen Incident Reporting Command Center      [System: Online]
===================================================================================

 [ 1. Incident Category ]
   (•) Pothole          ( ) Waterlogging
   ( ) Garbage Clutter  ( ) Uncertain / Other

 [ 2. Complaint Description & Clues ]
   [ "Severe pothole near Metro Pillar 42, already damaged two two-wheelers..."  ]

 [ 3. Photographic Evidence (Strongly Recommended) ]
   +-----------------------------------------------------------------------------+
   |  [ Mobile Camera: Take Photo ]       [ Browse / Drag & Drop File ]          |
   +-----------------------------------------------------------------------------+
   * On mobile: triggers device camera (rear-facing environment mode).
   * On desktop: triggers standard OS file dialog.
   * Preview: Shows thumbnail, image size, and "EXIF Privacy Sanitized" badge.
   * Note: "Complaints with photos resolve 3x faster. You can still submit without one."

 [ 4. Civic Incident Location ]
   [ (Locate) Use My Current Location ]
   Accuracy: ±8 meters [Device GPS] | Coordinates: 28.6139° N, 77.2090° E
   Reverse-Geocoded: "Barakhamba Road, Connaught Place, New Delhi"
   [x] I confirm this pin marks the location of the civic problem.
   
   Manual Override / Landmark:
   [ "Opposite Metro Pillar 42, Northbound Carriage"                           ]

 [ Submit Incident Report ]
===================================================================================
```

### Camera & Capture Implementation
- **Mobile Camera Trigger**:
  `<input type="file" accept="image/*" capture="environment" id="camera-capture">`
  Directly invokes the rear-facing camera on supported mobile browsers (iOS Safari, Android Chrome).
- **Mobile Fallback & Desktop Upload**:
  `<input type="file" accept="image/*" id="file-upload">`
  Allows selecting an existing photo from the photo library or desktop filesystem.
- **Preview & Non-Mandatory Policy**:
  If no photo is attached, a non-blocking indicator is shown:
  *"No photo attached. Your complaint will be recorded with status: Pending Evidence / Human Review."*

---

## 3. Geolocation & Spatial Metadata Strategy

### Location Lifecycle
1. **User Activation**: Geolocation is requested **only** after the citizen clicks `"Use My Current Location"`. Never requested automatically on page load.
2. **Browser API**: Invokes `navigator.geolocation.getCurrentPosition` with `enableHighAccuracy: true`, `timeout: 10000`, `maximumAge: 60000`.
3. **Capture Metadata**:
   - `latitude`, `longitude`
   - `accuracy_meters` (reported GPS horizontal accuracy)
   - `timestamp`
4. **Accuracy Handling**:
   - High Accuracy (`< 30m`): Displays green badge `GPS Confirmed (±{accuracy}m)`.
   - Moderate Accuracy (`30m - 100m`): Displays yellow badge `Approximate GPS (±{accuracy}m)`.
   - Low Accuracy (`> 100m`): Displays orange badge `Low Accuracy (±{accuracy}m) — Please confirm or adjust pin`.
5. **Interactive Pin Confirmation**:
   - Displays map coordinates and pin.
   - User must check: *"I confirm this pin marks the civic problem location"*.
   - If GPS permission is denied or inaccurate, user can drag the pin or enter a manual address/landmark.
6. **Location Source Tracking**:
   Recorded in payload as `DEVICE_GPS`, `USER_PIN_ADJUSTED`, `MANUAL_ENTRY`, or `REVERSE_GEOCODED`.
7. **Secure Context & Zero-Tracking**:
   - Works in `http://localhost` (standard browser secure-context exception) and `https://` in production.
   - Single snapshot only; no continuous location tracking.
   - Coordinates alone do not prove the photo was taken at that location.

---

## 4. Multimodal Photo Evidence Analysis Engine

### Groq Model Integration
- **Engine**: Groq `qwen/qwen3.8-27b` multimodal model.
- **Input Format**: Base64 data URI (`data:image/jpeg;base64,...`) passed in standard OpenAI-compatible `chat.completions` payload.
- **Structured Output**: Enforced via system prompt instructions and Pydantic validation.

### Output Contract (`PhotoEvidenceAnalysis`)
- `detected_category`: Detected civic hazard category (`pothole`, `waterlogging`, `garbage`, `other`, `unclear`).
- `visible_evidence`: Concrete visual description (e.g., *"Asphalt void approximately 1 meter wide with exposed aggregate and rainwater accumulation"*).
- `relevance_score`: Float between `0.0` and `1.0`.
- `image_quality`: Assessment string (`GOOD`, `BLURRY`, `DARK`, `OCCLUDED`, `ABSENT`).
- `confidence_score`: Float between `0.0` and `1.0`.
- `recommendation`: Action recommendation (`PROCEED`, `REQUEST_RETAKE`, `HUMAN_REVIEW`, `REQUEST_CLARIFICATION`).
- `outcome`: Enum:
  - `MATCHED`: Clear, relevant image matching citizen complaint and category.
  - `MISMATCH`: Clear image showing a completely unrelated object or category.
  - `LOW_QUALITY`: Severe blur, occlusion, or underexposure making verification impossible.
  - `INCONCLUSIVE`: Image is ambiguous or borderline.
  - `NOT_PROVIDED`: Citizen did not provide a photo.
- `authenticity_disclaimer`: *"AI visual triage only. Does not verify physical location, timestamp, or legal authenticity."*

---

## 5. Evidence-Based Workflow Routing & Orchestration

```mermaid
flowchart TD
    START([Citizen Incident Submission]) --> Intake[Incident Intelligence Agent\nText Extraction + Multimodal Vision]
    
    Intake --> Router{Evidence Status Router}
    
    Router -->|MATCHED| ParallelFork[Parallel Intake Triage]
    Router -->|NOT_PROVIDED| ParallelFork
    Router -->|MISMATCH| ClarifyQueue[Awaiting Citizen Clarification]
    Router -->|LOW_QUALITY| RetakeQueue[Awaiting Evidence Retake / Human Review]
    Router -->|INCONCLUSIVE| HumanReviewQueue[Awaiting Human Field Review]

    subgraph ParallelExecution ["Concurrent Processing"]
        ParallelFork --> GeoCivic[GeoCivic Agent\nHaversine Duplicate Detection]
        ParallelFork --> PriorityIntel[Priority Intelligence Agent\nHazard & Traffic Scoring]
    end

    GeoCivic --> ResolutionPlanning[Resolution Planning Agent]
    PriorityIntel --> ResolutionPlanning

    ResolutionPlanning --> CriticGate{Critic & Verification Gate}
    
    CriticGate -->|Approved| Simulation[Simulation Lab]
    CriticGate -->|Rejected (Retry <= 2)| ResolutionPlanning
    CriticGate -->|Escalate| SupervisorEscalation[Human Supervisor Escalation]

    Simulation -->|Intervention Succeeded| ResolvedState([RESOLVED])
    Simulation -->|Intervention Failed| AdaptiveRecovery[Adaptive Recovery Agent]
    
    AdaptiveRecovery --> CriticGate
```

### Routing Logic
1. **Clear, Relevant Photo (`MATCHED`)**:
   Passes directly to concurrent triage (`geocivic` and `priority_intel`).
2. **Missing Photo (`NOT_PROVIDED`)**:
   Complaint is permanently recorded with operational status `RECORDED_PENDING_REVIEW` and evidence status `NOT_PROVIDED`. Triage proceeds with lower confidence.
3. **Mismatched Photo (`MISMATCH`)**:
   Status set to `AWAITING_CLARIFICATION`. Citizen is invited to adjust category or upload correct photo. Never silently discarded.
4. **Low Quality / Inconclusive (`LOW_QUALITY` / `INCONCLUSIVE`)**:
   Status set to `AWAITING_EVIDENCE_RETAKE` or `AWAITING_HUMAN_REVIEW`. Prompt for retake displayed; moves to human review if unresolved.
5. **Concurrent GeoCivic & Priority Intelligence**:
   - `geocivic` compares confirmed coordinates against active and synthetic incidents using Haversine distance (< 50m threshold).
   - `priority_intel` evaluates hazard severity independently.
6. **Critic Gate, Simulation & Recovery**:
   - Critic independently validates safety, required resources, and closure criteria.
   - Bounded retries: max 2 iterations before escalating to human supervisor.

---

## 6. Privacy, Security, and Upload Hygiene

1. **Credential Protection**:
   `GROQ_API_KEY` stays on the FastAPI backend. Frontend never touches Groq APIs directly.
2. **Upload Constraints**:
   - Supported MIME types: `image/jpeg`, `image/png`, `image/webp`.
   - Max file size: 10MB raw upload; compressed to < 4MB Base64 for model ingestion.
   - Dimensions: Min 200x200px, Max 4096x4096px.
3. **Backend Image Sanitization & EXIF Scrubbing**:
   - Backend strips all EXIF metadata (camera serial, reporter home coordinates, device info) using Pillow before storage or caching.
4. **Data Minimization & Redaction**:
   - Base64 payloads and raw coordinates are redacted from server logs.
   - Coordinates are utilized solely for civic incident routing and spatial clustering.

---

## 7. Data Schemas & API Design

### Pydantic Models (`backend/app/schemas/incident.py`)

```python
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class IncidentCategory(str, Enum):
    POTHOLE = "pothole"
    WATERLOGGING = "waterlogging"
    GARBAGE = "garbage"
    UNCERTAIN_OTHER = "uncertain_other"

class EvidenceOutcome(str, Enum):
    MATCHED = "MATCHED"
    MISMATCH = "MISMATCH"
    INCONCLUSIVE = "INCONCLUSIVE"
    LOW_QUALITY = "LOW_QUALITY"
    NOT_PROVIDED = "NOT_PROVIDED"

class LocationSource(str, Enum):
    DEVICE_GPS = "DEVICE_GPS"
    USER_PIN_ADJUSTED = "USER_PIN_ADJUSTED"
    MANUAL_ENTRY = "MANUAL_ENTRY"
    REVERSE_GEOCODED = "REVERSE_GEOCODED"

class IncidentLocation(BaseModel):
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    accuracy_meters: Optional[float] = Field(default=None, ge=0.0)
    source: LocationSource = LocationSource.MANUAL_ENTRY
    address_text: Optional[str] = None
    is_user_confirmed: bool = False

class PhotoEvidenceAnalysis(BaseModel):
    detected_category: str
    visible_evidence: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    image_quality: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    recommendation: str
    outcome: EvidenceOutcome
    authenticity_disclaimer: str

class IncidentSubmissionRequest(BaseModel):
    complaint: str = Field(..., min_length=5, max_length=2000)
    category: IncidentCategory = IncidentCategory.UNCERTAIN_OTHER
    location: IncidentLocation
    image_base64: Optional[str] = None
    failure_reason: Optional[str] = None
```

### Endpoints Contract (`backend/app/main.py`)
- `POST /api/incidents`: Main intake endpoint. Accepts JSON with Base64 or `multipart/form-data`.
- `POST /api/incidents/{incident_id}/evidence`: Attach/update evidence photo for an existing report.
- `POST /api/incidents/{incident_id}/clarify`: Citizen or operator category/location clarification.
- `GET /api/incidents/{incident_id}`: Polls current operational and evidence verification status.

---

## 8. Verification Responsibility Matrix

| Verification Check | Type | Execution Engine | Action on Failure |
| :--- | :--- | :--- | :--- |
| **MIME Type & Magic Bytes** | Deterministic | Backend Validator (PIL) | Reject upload with 400 Bad Request |
| **EXIF Privacy Scrubbing** | Deterministic | Pillow Pipeline | Strips EXIF; saves clean image |
| **GPS Coordinate Validity** | Deterministic | Lat/Lon range & Float bounds | Fallback to manual address |
| **Spatial Proximity Duplicate** | Deterministic | Haversine formula (< 50m) | Flag duplicate candidate in GeoCivic |
| **Visual Category Match** | Vision Reasoning | Groq `qwen/qwen3.8-27b` | Sets `MISMATCH`; pauses triage |
| **Visual Quality & Blur** | Vision Reasoning | Groq `qwen/qwen3.8-27b` | Sets `LOW_QUALITY`; requests retake |
| **Mitigation Feasibility** | LLM + Critic Rules | Critic Agent | Loops back to replan or escalates |
| **Closure Verification** | LLM + Human Review | Simulation / Field Inspector | Re-triggers Adaptive Recovery |

---

## 9. Seeded Test Scenarios Matrix

| # | Scenario Title | Input Conditions | Evidence Outcome | Expected System Behavior |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Valid Pothole & Confirmed Location** | Clear pothole photo, GPS accuracy 8m, category `pothole` | `MATCHED` | Full pipeline execution; priority assigned; repair plan approved. |
| **2** | **Waterlogging with Relevant Photo** | Submerged road photo, category `waterlogging` | `MATCHED` | High priority band (75-100); suction pumps & drainage crew assigned. |
| **3** | **Garbage Report with Mismatched Photo** | Indoor sofa/cat photo, category `garbage` | `MISMATCH` | Halts automatic dispatch; flags `AWAITING_CLARIFICATION`; report preserved. |
| **4** | **Blurry / Unusable Photo** | Extreme motion blur image | `LOW_QUALITY` | Flags `AWAITING_EVIDENCE_RETAKE`; human inspection queue if unresolved. |
| **5** | **Missing Photograph** | Complaint text only, no image | `NOT_PROVIDED` | Successfully created; marked `RECORDED_PENDING_REVIEW`; triage continues. |
| **6** | **Location Permission Denied** | Geolocation permission rejected | `MATCHED` / `NOT_PROVIDED` | Activates manual address entry; marked `source="MANUAL_ENTRY"`. |
| **7** | **Poor GPS Accuracy (> 150m)** | Geolocation accuracy 250m | `MATCHED` | Prompts pin adjustment; sets `source="USER_PIN_ADJUSTED"` upon confirmation. |
| **8** | **Near Existing Synthetic Incident** | Incident within 25m of `INC-1002` | `MATCHED` | GeoCivic identifies duplicate; attaches parent `INC-1002`; avoids double dispatch. |
| **9** | **Groq Outage Fallback** | Simulated Groq 503 / network timeout | `FALLBACK_RULE_EVALUATED` | Invokes deterministic keyword extractor; marks fallback in audit trail. |
| **10** | **Evidence Insufficient for Closure** | Simulated repair failure | `MATCHED` -> `CLOSURE_FAILED` | Simulation fails closure; Adaptive Recovery proposes alternative plan. |

---

## 10. Implementation Plan & Approval Gate

- **Phase 1: Backend Schemas, Upload Sanitization & Image Processing**
  - Implement Pydantic models in `backend/app/schemas/incident.py`.
  - Add Pillow-based EXIF stripping and magic-byte validation.
- **Phase 2: Groq Multimodal Integration in Incident Intelligence**
  - Connect `backend/app/agents/incident_intel.py` to `qwen/qwen3.8-27b`.
  - Implement structured vision extraction prompt and deterministic fallback handler.
- **Phase 3: LangGraph Parallel Orchestrator & Evidence Routing**
  - Update `IncidentState` with location and evidence fields.
  - Implement concurrent fork for `geocivic` and `priority_intel`.
  - Wire conditional routes for evidence mismatch and human review.
- **Phase 4: Frontend Citizen Interface (React + Tailwind)**
  - Build responsive intake form with rear-camera capture and file chooser.
  - Build geolocation widget with accuracy indicators and interactive pin.
  - Render dual-status tracking and audit timeline.
- **Phase 5: Automated Seeded Test Suite**
  - Implement pytest suite covering all 10 scenarios.
