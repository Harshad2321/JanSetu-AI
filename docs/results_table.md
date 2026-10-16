# JanSetu AI — Verification & Validation Results Table

**Generated Date:** 2026-10-16 12:00:37 UTC  
**Validation Suite:** `eval/run_validation.py`  
**Overall Invariants Status:** 11/11 PASSED (100% compliant)  

---

## 1. Machine Learning Evaluation (P4.3 & P9.2)

| Dataset Partition | Sample Count | Accuracy | Macro-F1 | Precision | Recall | Leakage Check |
|---|---|---|---|---|---|---|
| **Held-Out Test Set** (Stratified seed=42) | 60 | 100.0% | 100.0% | 100.0% | 100.0% | PASS (0 overlap) |
| **Challenge Set** (Disjoint vocabulary) | 30 | 73.3% | 73.3% | 73.5% | 73.3% | PASS (0 overlap) |

*Evaluation Provenance:* Train (240) / Held-Out Test (60) via stratified 80/20 seed=42; Challenge Set (30) with disjoint vocabulary  
*Data Leakage Detected:* **False** (0 vocabulary intersections)  
*Reproducibility Status:* **PASS (Identical metrics reproduced)**  

---

## 2. System Invariants & Workflow Decision Verification (P9.3)

| ID | Title & Check Description | Status | Evidence & Actual Output |
|---|---|---|---|
| **INV-1** | **Closure Gating Requirement**<br>_VERIFIED_CLOSED state strictly guarded by passing VerificationResult_ | ✅ PASS | Strictly enforced: Transition to VERIFIED_CLOSED raised TransitionError when missing or failing, and succeeded only with passed=True. |
| **INV-2** | **Simulation Labeling**<br>_All execution attempts explicitly stamped with simulated=True_ | ✅ PASS | Pydantic ExecutionAttempt enforcement: attempt.simulated == True |
| **INV-3** | **Mandatory Danger Escalation**<br>_Hazard triggers immediate human escalation overriding baseline numerical scores_ | ✅ PASS | Escalated: True; Reasons: ['E01_LIFE_SAFETY: Active cave-in, open manhole, high-voltage wire submerged, or direct life-safety threat', 'E04_VULNERABLE_POPULATION: Hazard directly obstructing primary school, childcare facility, or elderly care center']; Priority Band: Critical |
| **INV-4** | **Bounded Replanning Retries**<br>_Exhaustion of MAX_RECOVERY_RETRIES (2) routes to HUMAN_REVIEW_ | ✅ PASS | Retry count: 2 >= 2; escalated_to_human=True; status=HUMAN_REVIEW |
| **INV-5** | **History & Plan Version Preservation**<br>_Failed plans and execution attempts remain stored in relational Twin upon replanning_ | ✅ PASS | Stored plans: 2 (versions: [1, 2]); Stored attempts: 1 |
| **INV-6** | **Unsafe & Unauthorized Plan Rejection**<br>_Adaptive recovery enforces safety clearances and approval constraints_ | ✅ PASS | Eligible alternatives: 5 (all certified=True, authorized=True); Explicitly rejected unsafe/unauthorized: True |
| **INV-7** | **Duplicate Review Invariant**<br>_Nearby similar reports flagged as UNCONFIRMED candidates; zero auto-merging_ | ✅ PASS | Candidate status: 'UNCONFIRMED'; Both records preserved (ID INC-NEW-DUP vs INC-1002); auto_merged=False |
| **INV-8** | **Graceful Model Failure**<br>_Unavailable model flags available=False without fabricating predictions_ | ✅ PASS | Available: False; Error: 'Model artifact not available at non_existent_model.joblib'; Predicted label: None |
| **WF-1** | **Multimodal Disagreement Workflow**<br>_Conflicting NLP and Vision predictions route to clarification without forcing a category_ | ✅ PASS | Status: DISAGREEMENT; Disagreement: True; Forced category: None; Clarification questions: 1 |
| **WF-2** | **Independent Verification Gate**<br>_Verifier blocks closure if required evidence or supervisor sign-off is missing_ | ✅ PASS | Result: HUMAN_REVIEW_REQUIRED; Passed: False; Rejection reasons: ['Mandatory human supervisor sign-off required before closure.'] |
| **WF-3** | **Database Transaction Rollback Integrity**<br>_Atomic multi-step updates roll back completely upon error_ | ✅ PASS | Rollback confirmed: transaction rolled back cleanly and record found=False |

---

## 3. Methodological Integrity & Academic Boundaries

1. **Synthetic vs Physical Reality:** Metrics reflect performance solely on structured synthetic complaints. Real citizen complaints present colloquial dialect variation, severe image blur, OCR corruption, and multi-issue compound reports.
2. **Simulation Rigor:** All execution outcomes (`simulated=True`) demonstrate control flow and adaptive recovery logic; they do not constitute empirical evidence of municipal field dispatch.
3. **Closure Safety:** State transitions enforce that no incident can reach `VERIFIED_CLOSED` without passing independent criteria validation and supervisor clearance.
