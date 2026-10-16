# JanSetu AI — System Limitations and Boundaries

**Document Version:** 1.0.0 (Phase 9 Validation)  
**Academic Context:** CA-3 Agentic AI Proof of Concept  
**Status:** Canonical & Honest Limitation Record  

---

## Executive Summary

JanSetu AI is an educational, prototype-grade multi-agent civic incident management platform. To ensure academic rigor and avoid unsupported claims, this document explicitly records the empirical, architectural, and operational limitations of the system. 

None of the components described below are presented as ready for live municipal municipal deployment without substantial engineering, legal compliance, field testing, and human oversight.

---

## 1. Machine Learning & Synthetic Data Limitations

### 1.1 Synthetic Dataset Boundaries
- **Lack of Natural Distribution:** The 300 training samples and 30 challenge samples in `data/synthetic_complaints_*.json` were synthetically generated across 4 languages (English, Hindi, Marathi, Hinglish). While template structures, formality styles, and vocabulary variations were deliberately induced, synthetic data cannot replicate:
  - Colloquial street slangs and local abbreviations (e.g., area-specific landmarks).
  - Spelling errors, typos, and mobile auto-correct distortions.
  - Emotionally distressed, chaotic, or fragmented citizen communication.
  - Multi-issue composite complaints (e.g., a pothole causing a water leak that washes garbage onto the pavement).
- **Overestimated In-Domain Performance:** The TF-IDF + Logistic Regression classifier achieves 100.0% accuracy on the held-out synthetic test set. This metric reflects the closed nature of the template generator rather than a generalized real-world capability. On the unseen challenge partition with non-overlapping vocabulary, accuracy drops to **73.33%**. On unconstrained real citizen complaints, performance would be significantly lower.

### 1.2 Uncalibrated Vision-Language Model (VLM) Confidences
- **Probability vs Certainty:** The Groq-hosted vision model (`qwen/qwen-2.5-vl-27b`) or local Ollama instances output text responses that are parsed into structured estimates. Any numerical confidence score extracted from text generation or softmax output does not represent a mathematically calibrated posterior probability.
- **Visual Ambiguity and Sensor Noise:**
  - Poor lighting, motion blur, rain-distorted vehicle windshields, or night photography degrade VLM visual feature extraction.
  - Shallow puddles may be mistaken for severe waterlogging; road shadows or surface patching can be misclassified as deep craters.
  - A 2D photographic perspective cannot compute true physical depth or volumetric cavity displacement.

### 1.3 Linguistic & Multilingual Nuance
- **Transliteration Variability:** Hinglish and code-mixed phrases exhibit arbitrary phonetic spelling variations (e.g., *"bahut bada gaddha"*, *"bohot bda khadda"*, *"kachra pada hai"*, *"kachda faila hua hai"*). The vocabulary vectorizer captures frequent n-grams but fails when rare or novel phonetic romanizations are used.
- **Low-Resource Language Coverage:** Coverage of Marathi and regional dialects is currently restricted to vocabulary seeded in the synthetic template generator. Syntactic variations across rural vs urban dialects are not modeled.

---

## 2. Decision Logic & Triage Limitations

### 2.1 Heuristic Priority Scoring
- **Weighted Heuristic Nature:** Priority scores (0–100) are generated through linear weighted summation defined in `config/risk_weights.yaml` (category base weight, self-reported severity, duration, location vulnerability). These weights represent an engineering heuristic, not an actuarially validated public hazard model.
- **Reporting Bias Vulnerability:** Citizens frequently exaggerate complaint severity or claim immediate danger to accelerate municipal dispatch. Without external sensor corroboration (e.g., traffic density feeds, bus telemetry), the system can be manipulated by inflated citizen descriptions unless gated by objective validation checks.
- **Missing Factor Uncertainty:** When citizen inputs omit duration or crowd estimates, the system explicitly logs `missing_factors` and penalizes certainty (`uncertainty_score > 0`). However, estimating risk under incomplete information remains inherently uncertain.

### 2.2 Geo-Spatial Clustering & Deduplication
- **Spatial Heuristic Thresholds:** Duplicate candidate identification relies on a 50-meter Haversine radius and TF-IDF cosine text similarity (>0.25). 
- **Urban Density Gotchas:** In dense urban environments, two distinct potholes may exist 15 meters apart on opposite lanes of a dual carriageway. Conversely, a large 50-meter waterlogging zone may be reported from different vantage points. 
- **Non-Automatic Merging (Invariant 7):** Because algorithmic similarity is evidence rather than proof, the system leaves candidates in an `UNCONFIRMED` review state. A human dispatcher is strictly required to confirm or reject merges.

---

## 3. Operational Simulation vs Physical Municipal Reality

### 3.1 Simulated Execution (`simulated=True`)
- **No Physical Dispatch:** The execution engine (`app.simulation.simulator`) is a software state simulator. When the system records a successful patch or a crew shortage, no physical municipal vehicle moves, no worker is deployed, and no physical asphalt is compacted.
- **Deterministic Scenarios:** Simulated failure scenarios (`CREW_UNAVAILABLE`, `MATERIAL_UNAVAILABLE`, `WEATHER_BLOCK`, `RELIEF_EXPIRED`, `COMPLETE_MISSING_EVIDENCE`) are triggered by seeded scenarios to demonstrate agentic adaptive recovery control flow, not empirical municipal logistics.
- **Labeling Invariant:** Every attempt is immutably stamped with `simulated=True`. Displaying or reporting these simulation events as evidence of physical road repair is strictly prohibited.

### 3.2 Physical Limitations of Visual Closure Verification
- **Visual Surface vs Structural Soundness:** Agent 6 (Independent Verification) validates that an after-repair photo matches criteria (e.g., cavity filled, surface flush). However:
  - A photograph cannot evaluate asphalt compaction density, core stability, aggregate adhesion, or underlying sub-base moisture.
  - Cosmetic surface coverage (e.g., loose gravel filling or thin bitumen layer) appears repaired in photographs but will wash out under the next rainfall.
- **Mandatory Human Sign-off Requirement:** Because photographic evidence alone cannot certify physical structural safety, the system explicitly enforces that high-severity or high-traffic incidents require a verified supervisor sign-off (`ClosureEvidence.supervisor_signoff`) before entering `VERIFIED_CLOSED`.

---

## 4. Architectural & System Boundaries

### 4.1 Bounded Replanning Limits
- To prevent infinite agent replanning loops in production, recovery is strictly capped at `MAX_RECOVERY_RETRIES = 2`.
- When retries are exhausted, the system does not attempt autonomous self-healing; it routes the incident to `HUMAN_REVIEW` and halts automatic dispatch.

### 4.2 Single-Node SQLite Storage
- The Civic Incident Twin and audit trails are backed by SQLite. While ACID transactions and foreign key integrity are enforced via SQLAlchemy and `transaction_scope`, SQLite is designed for single-node prototypes and is not intended for distributed, high-concurrency municipal municipal IT environments with thousands of concurrent field workers.

### 4.3 Third-Party API Dependence
- Live Groq vision calls require external Internet connectivity and are subject to remote API rate limits (HTTP 429). The system implements structured fallbacks (`VisionClassificationResult(available=False)`), but offline environments cannot utilize cloud-based visual inference unless a local Ollama runtime is configured.
