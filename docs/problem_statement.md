# Problem Statement

JanSetu AI addresses a civic incident problem that is too messy for simple forms or chatbots: residents submit photos, text, and location details with inconsistent language, missing evidence, duplicate reports, and uncertain urgency. Current systems often create a ticket, but they do not reason across evidence, check for duplicates, recover from failed field work, or verify whether closure is actually justified. Our agentic workflow interprets multimodal input, finds duplicate and hotspot signals, scores risk, plans a temporary and permanent response, and then simulates execution. When a crew fails or evidence is missing, the system re-plans and escalates instead of claiming success. Closure is allowed only after independent verification. All data are synthetic and all execution is simulated, which keeps the project safe, explainable, and suitable for a classroom proof of concept.

## Before / After

| Issue | Before (today's complaint handling) | After (JanSetu AI) |
|---|---|---|
| Unstructured reports | A citizen sends a photo and text with unclear location or wording; a form may store it without understanding it. | Agent 1 interprets the complaint, extracts facts, and asks for clarification only when needed. |
| Duplicate reports | Similar incidents are treated as separate tickets or silently merged without proof. | Agent 2 checks spatial and textual similarity, flags candidate duplicates as `UNCONFIRMED`, and never auto-merges. |
| Crew failure | A failed repair is treated as complete or not reworked. | Agent 5 analyses the block, preserves the failed plan, and proposes a different feasible response. |
| Closure without proof | A team can close the incident based on a photo or assumption. | Agent 6 verifies closure against evidence and rejects closure when proof is missing. |
| Unclear urgency | Risk is often inferred from a subjective form field or a single complaint. | Agent 3 uses transparent weights and mandatory escalation rules to score urgency and evidence. |

## Agent role map

| Agent | Assignment role | Input | Output |
|---|---|---|---|
| Agent 1: Incident Intelligence | Research | complaint text, image, location metadata, optional impact details | structured incident facts, evidence status, clarification questions |
| Agent 2: Geo-Spatial Intelligence | Research | coordinates, location details, description text | duplicate candidates, hotspot summary, spatial risk signals |
| Agent 3: Risk & Priority | Business Automation | structured facts, exposure cues, risk weights | priority score, band, escalation decision |
| Agent 4: Response Planning | Planner | priority, evidence, duplicate review | temporary-relief plan and permanent-resolution plan |
| Agent 5: Adaptive Recovery | Business Automation | failed execution reason, previous plan, constraints | reworked plan, preserved failed plan, retry/escalation decision |
| Agent 6: Independent Verification | Critic | plan, evidence, execution result | approve / reject / reopen / replan verdict |

Scope boundary: all data is synthetic and all execution is simulated.
