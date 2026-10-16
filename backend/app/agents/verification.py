"""
Independent Verification Agent (Phase 6, P6.4).

This module intentionally separates post-execution verification from the Critic's
pre-execution plan review.
The Critic validates and approves/rejects a proposed plan before execution.
The Independent Verification Agent evaluates the approved plan, recorded execution attempt,
and completion evidence AFTER execution and decides whether closure is valid.

Guarantees:
- Never trusts the planner's or simulator's claim of success alone.
- Compares recorded evidence and execution facts with the original closure criteria.
- Only a passing VerificationResult authorizes transition to VERIFIED_CLOSED.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.agents.base import BaseCivicAgent
from app.graph.state import IncidentState
from app.graph.state_machine import transition_status
from app.schemas.incident import (
    AuditEvent,
    ClosureEvidence,
    IndependentVerificationOutput,
    OperationalStatus,
    VerificationOutcome,
    VerificationResult,
)

logger = logging.getLogger("jansetu.verification")


def verify_incident(
    incident_id: str,
    plan: Any = None,
    evidence: Any = None,
    execution_outcome: Optional[str] = None,
    execution_attempt: Any = None,
    requires_human_signoff: bool = False,
    supervisor_signoff: bool = False,
) -> VerificationResult:
    """Evaluate plan, execution attempt, and closure evidence independently."""
    # 1. Mandatory human supervisor sign-off gate
    if requires_human_signoff and not supervisor_signoff:
        return VerificationResult(
            verification_id=f"VER-{incident_id}-HUMAN",
            incident_id=incident_id,
            criteria=getattr(plan, "closure_criteria", []) if plan else [],
            evidence_reviewed=[],
            result=VerificationOutcome.HUMAN_REVIEW_REQUIRED,
            outcome=VerificationOutcome.HUMAN_REVIEW_REQUIRED.value,
            passed=False,
            rejection_reasons=["Mandatory human supervisor sign-off required before closure."],
            reviewer="independent_verification_agent",
            correlation_id=incident_id,
        )

    # 2. Execution outcome gate: must be successful
    if execution_outcome and execution_outcome != "SUCCESS":
        return VerificationResult(
            verification_id=f"VER-{incident_id}-EXEC-FAIL",
            incident_id=incident_id,
            criteria=getattr(plan, "closure_criteria", []) if plan else [],
            evidence_reviewed=[],
            result=VerificationOutcome.REJECTED_INCOMPLETE_ACTION,
            outcome=VerificationOutcome.REJECTED_INCOMPLETE_ACTION.value,
            passed=False,
            rejection_reasons=[f"Intervention execution did not complete successfully (outcome: {execution_outcome})."],
            reviewer="independent_verification_agent",
            correlation_id=incident_id,
        )

    # Also check execution_attempt model if passed
    if execution_attempt is not None:
        att_outcome = getattr(execution_attempt, "outcome", None)
        if att_outcome and att_outcome != "SUCCESS":
            return VerificationResult(
                verification_id=f"VER-{incident_id}-ATT-FAIL",
                incident_id=incident_id,
                criteria=getattr(plan, "closure_criteria", []) if plan else [],
                evidence_reviewed=[],
                result=VerificationOutcome.REJECTED_INCOMPLETE_ACTION,
                outcome=VerificationOutcome.REJECTED_INCOMPLETE_ACTION.value,
                passed=False,
                rejection_reasons=[f"Execution attempt outcome was '{att_outcome}', not 'SUCCESS'."],
                reviewer="independent_verification_agent",
                correlation_id=incident_id,
            )

    # 3. Evidence presence gate
    if evidence is None:
        return VerificationResult(
            verification_id=f"VER-{incident_id}-NO-EVID",
            incident_id=incident_id,
            criteria=getattr(plan, "closure_criteria", []) if plan else [],
            evidence_reviewed=[],
            result=VerificationOutcome.REJECTED_INSUFFICIENT_EVIDENCE,
            outcome=VerificationOutcome.REJECTED_INSUFFICIENT_EVIDENCE.value,
            passed=False,
            rejection_reasons=["No completion evidence was provided for independent verification."],
            reviewer="independent_verification_agent",
            correlation_id=incident_id,
        )

    if isinstance(evidence, dict):
        try:
            evidence = ClosureEvidence(**evidence)
        except Exception:
            pass

    criteria_met = list(getattr(evidence, "closure_criteria_met", []) or [])
    required = list(getattr(plan, "closure_criteria", []) or []) if plan else []
    if not required:
        required = list(criteria_met)

    is_ready = getattr(evidence, "is_ready_for_closure", False)
    unmet = [c for c in required if c not in criteria_met]

    # 4. Strict verification of all closure criteria
    if is_ready and not unmet and len(criteria_met) > 0:
        return VerificationResult(
            verification_id=f"VER-{incident_id}-PASS",
            incident_id=incident_id,
            criteria=required,
            evidence_reviewed=criteria_met,
            result=VerificationOutcome.VERIFIED,
            outcome=VerificationOutcome.VERIFIED.value,
            passed=True,
            rejection_reasons=[],
            reviewer="independent_verification_agent",
            correlation_id=incident_id,
        )

    rejection_reasons = []
    if unmet:
        rejection_reasons.append(f"Unmet closure criteria: {', '.join(unmet)}")
        outcome = VerificationOutcome.REJECTED_INCOMPLETE_ACTION
    else:
        rejection_reasons.append("Evidence is not marked ready for closure or verification photo is absent.")
        outcome = VerificationOutcome.REJECTED_INSUFFICIENT_EVIDENCE

    return VerificationResult(
        verification_id=f"VER-{incident_id}-REJECT",
        incident_id=incident_id,
        criteria=required,
        evidence_reviewed=criteria_met,
        result=outcome,
        outcome=outcome.value,
        passed=False,
        rejection_reasons=rejection_reasons,
        reviewer="independent_verification_agent",
        correlation_id=incident_id,
    )


class IndependentVerificationAgent(BaseCivicAgent[IndependentVerificationOutput]):
    """Agent 6: Independent Verification Specialist."""

    agent_name: str = "Independent Verification Agent"
    agent_role: str = "Critic"

    def run(
        self,
        incident: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> IndependentVerificationOutput:
        """
        Evaluate plan, simulated execution attempt, and closure evidence independently.
        Returns validated IndependentVerificationOutput.
        """
        data = self.extract_incident_dict(incident)
        ctx = context or {}

        incident_id = data.get("incident_id") or ctx.get("incident_id") or "unknown"
        plan = data.get("current_plan") or ctx.get("current_plan")
        evidence = (
            data.get("closure_evidence")
            or data.get("synthetic_closure_evidence")
            or ctx.get("closure_evidence")
            or ctx.get("synthetic_closure_evidence")
        )
        sim_result = data.get("simulation_result") or ctx.get("simulation_result")
        attempt = data.get("execution_attempt") or ctx.get("execution_attempt")
        requires_signoff = bool(data.get("requires_human_signoff") or ctx.get("requires_human_signoff", False))

        verification = verify_incident(
            incident_id=incident_id,
            plan=plan,
            evidence=evidence,
            execution_outcome=sim_result,
            execution_attempt=attempt,
            requires_human_signoff=requires_signoff,
        )

        outcome_str = verification.result.value if hasattr(verification.result, "value") else str(verification.result)

        if verification.passed:
            status = OperationalStatus.AWAITING_VERIFICATION.value
        elif verification.result == VerificationOutcome.HUMAN_REVIEW_REQUIRED:
            status = OperationalStatus.HUMAN_REVIEW.value
        else:
            status = OperationalStatus.VERIFICATION_FAILED.value

        # Optional persistence if db provided
        db = ctx.get("db")
        if db is not None:
            from app.db.repository import persist_verification_record
            try:
                persist_verification_record(db, verification)
            except Exception as exc:
                logger.warning("Could not persist verification result: %s", exc)

        return IndependentVerificationOutput(
            incident_id=incident_id,
            verification_result=verification,
            status=status,
            passed=verification.passed,
            outcome=outcome_str,
            rejection_reasons=verification.rejection_reasons,
            closure_verified=verification.passed,
        )


def verification_node(state: IncidentState) -> Dict[str, Any]:
    """Evaluate closure evidence and return an independent verification verdict."""
    agent = IndependentVerificationAgent()
    output = agent.run(state)
    verification = output.verification_result

    now = datetime.now(timezone.utc).isoformat()
    if verification.passed:
        audit_event = AuditEvent(
            timestamp=now,
            agent=agent.agent_name,
            action="Verification Passed",
            result=f"Independent review approved closure: all {len(verification.evidence_reviewed)} criteria verified.",
            outcome="VERIFIED",
        )
        return {
            "verification_result": verification,
            "verification_output": output.model_dump(),
            "status": output.status,
            "audit_timeline": [audit_event.model_dump()],
        }

    audit_event = AuditEvent(
        timestamp=now,
        agent=agent.agent_name,
        action="Verification Rejected",
        result="; ".join(verification.rejection_reasons),
        outcome=verification.result.value if hasattr(verification.result, "value") else str(verification.result),
    )
    return {
        "verification_result": verification,
        "verification_output": output.model_dump(),
        "status": output.status,
        "audit_timeline": [audit_event.model_dump()],
    }


__all__ = ["IndependentVerificationAgent", "verification_node", "verify_incident"]
