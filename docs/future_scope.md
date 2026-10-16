# JanSetu AI — Future Scope and Engineering Roadmap

**Document Version:** 1.0.0 (Phase 9 Validation)  
**Status:** Prospective Future Engineering Roadmap  
**Notice:** All items described herein represent proposed future directions for academic follow-up or municipal pilot development. **None of these features are claimed as implemented in the current Proof of Concept.**

---

## 1. Machine Learning & Computer Vision Enhancements

### 1.1 Edge-Deployable Vision Model (MobileNetV2 / YOLOv8-Nano)
- **Problem Statement:** Current vision analysis relies on heavy cloud VLMs (Groq Qwen-2.5-VL 27B) or local Ollama instances that require high-VRAM GPUs. Field devices used by municipal inspectors often have low compute capabilities and spotty network connectivity.
- **Proposed Architecture:**
  - Fine-tune a lightweight CNN/Vision Transformer (e.g., MobileNetV2 or YOLOv8-Nano) using a legitimately licensed, geographically diverse public dataset of road hazards (e.g., CRACK500, RDD2022 Road Damage Dataset).
  - Quantize the model using ONNX Runtime or TensorFlow Lite for on-device inference directly on inspector mobile hardware.
  - Retain the dual-model fusion strategy: lightweight edge model provides real-time bounding boxes; cloud/server VLM provides high-level scene reasoning only when connected.

### 1.2 Calibrated Uncertainty & Out-of-Distribution (OOD) Detection
- **Temperature Scaling & Platt Calibration:** Apply post-hoc probability calibration to ensure model confidence reflects empirical accuracy.
- **OOD Detection:** Implement an embedding-based distance check (e.g., Mahalanobis distance or Isolation Forest) to flag complaints unrelated to municipal infrastructure (e.g., personal disputes, indoor plumbing, spam) before they enter the civic triage pipeline.

### 1.3 Scaled Multilingual NLU
- **Fine-Tuned IndicBERT / IndicTrans2:** Replace TF-IDF vectorization with an Indic-specialized pre-trained language model capable of zero-shot transfer across Indian languages (Hindi, Marathi, Gujarati, Tamil, Bengali, Telugu, Kannada).
- **Phonetic Normalization:** Implement soundex/metaphone algorithms specifically adapted to Devanagari transliterations to handle arbitrary romanized Hinglish and Marathi spellings.

---

## 2. Decision Intelligence & Multi-Agent Orchestration

### 2.1 Dynamic Municipal Resource Optimization
- **Real-Time Resource Allocation:** Replace static synthetic registries with linear programming or constraint satisfaction solvers (e.g., OR-Tools) to optimize multi-incident dispatch schedules against real vehicle fleets, asphalt batch lifetimes, and municipal work shifts.
- **Weather & Traffic API Integration:** Connect Response Planning to live IMD meteorological webhooks and municipal traffic sensor feeds to automatically trigger weather-block contingencies before dispatching crews into monsoon downpours.

### 2.2 Formal Role-Based Access Control (RBAC) & Governance
- **Cryptographic Supervisor Sign-Offs:** Implement PKI-based digital signatures or JWT-authorized approvals for critical state transitions (`AWAITING_AUTHORIZATION -> IN_PROGRESS` and `RECOVERY_VERIFICATION -> VERIFIED_CLOSED`).
- **Separation of Duties Enforcement:** Ensure that the municipal contractor who executes an intervention cannot hold permissions to approve or verify closure of their own work order.

---

## 3. Platform Architecture & Production Readiness

### 3.1 Municipal ERP & Open311 Integration
- **Open Standards Support:** Implement Open311 GeoReport v2 endpoints to allow citizen intake from national portals (e.g., Swachhata app, CPGRAMS, local municipal 311 systems).
- **ERP Adapters:** Build standardized webhooks for enterprise municipal resource planning platforms (e.g., SAP Municipal Solutions, Microsoft Dynamics, open-source DIGIT).

### 3.2 Enterprise Persistence & Scalability
- **Distributed Database Migration:** Migrate the Civic Incident Twin persistence layer from SQLite to PostgreSQL + PostGIS, enabling high-concurrency spatial queries, spatial indexing (R-Tree), and multi-tenant ward-level partitioning.
- **Model Registry & MLOps:** Integrate MLflow or DVC for automated model versioning, dataset artifact hashing, and drift detection.

### 3.3 Sensor-Corroborated Verification
- **IoT & Telemetry Integration:** Equip municipal inspection vehicles with accelerometer-based roughness sensors (IRI - International Roughness Index) to provide physical, quantitative verification of road smoothness alongside photographic evidence.
