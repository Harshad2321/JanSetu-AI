# JanSetu AI: 10-Slide Presentation Outline

## Slide 1 — Problem and opportunity
- Civic complaints are messy, multimodal, and often duplicated.
- Current ticket forms do not reason across evidence or validate closure.
- JanSetu AI aims to turn noisy complaints into a governed, explainable workflow.

## Slide 2 — Domain and why it matters
- Civic incidents (potholes, waterlogging, garbage) affect safety, mobility, and public health.
- Delay in recognition and repair worsens risk for residents and crews.
- A system must combine evidence, risk, planning, and verification, not just a chatbot.

## Slide 3 — Current challenge in civic operations
- Unstructured citizen reports are inconsistent and incomplete.
- Similar incidents appear as duplicate tickets without evidence-based review.
- Failed repairs and closure without proof lead to poor trust and repeated work.

## Slide 4 — Proposed solution
- Use a multi-agent workflow to interpret input, find duplicates, score urgency, and plan responses.
- Keep operations synthetic and simulated to preserve safety and classroom feasibility.
- Require independent verification before any closure can be marked as successful.

## Slide 5 — Agent roles and responsibilities
- Agent 1: Incident Intelligence — extract facts, quality evidence, ask clarifying questions.
- Agent 2: Geo-Spatial Intelligence — check duplicates and hotspot patterns.
- Agent 3: Risk & Priority — compute score, explain factors, enforce escalation.
- Agent 4: Response Planning — produce temporary-relief and permanent-repair plans.
- Agent 5: Adaptive Recovery — re-plan after failure and preserve failed attempts.
- Agent 6: Independent Verification — reject or approve closure based on proof.

## Slide 6 — Architecture overview
- Citizen input enters the ML/DL layer.
- Vision, NLP, and fusion convert raw data into structured facts.
- The orchestrator dispatches the correct agent for each state.
- The Civic Incident Twin stores the status timeline and audit trail in SQLite.

## Slide 7 — Workflow and decision points
- Intake → evidence extraction → triage → duplicate review → prioritization.
- Plan created → simulator executes → recovery on failure → verification before closure.
- Decision points include clarification, escalation, plan failure/replan, verification rejection, and human review.

## Slide 8 — Demo plan
- Show a canonical pothole report from a citizen.
- Demonstrate evidence extraction, duplicate check, and risk scoring.
- Trigger a simulated crew failure to show recovery and re-planning.
- End with verification and the final audit timeline.

## Slide 9 — Validation and expected results
- System uses synthetic and simulated data labelled clearly.
- Model outputs are explainable and decisions are auditable.
- Evaluation focuses on correctness of the workflow, not on real-world municipal deployment.

## Slide 10 — Limitations and future scope
- This is a proof-of-concept, not production civic infrastructure.
- Synthetic data limits realism, and all execution is simulated.
- Future work could add stronger evaluation, richer policies, and a more realistic incident twin.
