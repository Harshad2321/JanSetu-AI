"""Deterministic transition rules for JanSetu civic workflow states.

This module keeps the current app compatible with the earlier simulation-based flow,
while enforcing the tracker's stricter gate: an incident may only enter
VERIFIED_CLOSED when a valid, passing VerificationResult for that incident is
provided.
"""

from __future__ import annotations

from typing import Mapping

from app.schemas.incident import OperationalStatus, VerificationOutcome, VerificationResult


class TransitionError(ValueError):
    """Raised when a workflow state transitions outside the allowed map."""


_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    # Tracker section 4 states
    OperationalStatus.SUBMITTED.value: {OperationalStatus.NEEDS_CLARIFICATION.value, OperationalStatus.CLASSIFIED.value},
    OperationalStatus.NEEDS_CLARIFICATION.value: {OperationalStatus.CLASSIFIED.value, OperationalStatus.HUMAN_REVIEW.value},
    OperationalStatus.CLASSIFIED.value: {OperationalStatus.TRIAGED.value},
    OperationalStatus.TRIAGED.value: {
        OperationalStatus.PLANNING.value,
        OperationalStatus.VALIDATING.value,
        OperationalStatus.HUMAN_REVIEW.value,
    },
    OperationalStatus.PLANNING.value: {
        OperationalStatus.AWAITING_AUTHORIZATION.value,
        OperationalStatus.IN_PROGRESS_SIMULATED.value,
        OperationalStatus.VALIDATING.value,
        OperationalStatus.SIMULATING.value,
        OperationalStatus.ESCALATED.value,
        OperationalStatus.HUMAN_REVIEW.value,
    },
    OperationalStatus.AWAITING_AUTHORIZATION.value: {OperationalStatus.IN_PROGRESS_SIMULATED.value, OperationalStatus.HUMAN_REVIEW.value},
    OperationalStatus.IN_PROGRESS_SIMULATED.value: {OperationalStatus.AWAITING_VERIFICATION.value, OperationalStatus.PLAN_FAILED.value},
    OperationalStatus.PLAN_FAILED.value: {OperationalStatus.REPLANNING.value, OperationalStatus.RECOVERING.value, OperationalStatus.HUMAN_REVIEW.value},
    OperationalStatus.REPLANNING.value: {OperationalStatus.PLANNING.value, OperationalStatus.VALIDATING.value, OperationalStatus.HUMAN_REVIEW.value},
    OperationalStatus.AWAITING_VERIFICATION.value: {
        OperationalStatus.VERIFIED_CLOSED.value,
        OperationalStatus.SIMULATED_RESOLVED.value,
        OperationalStatus.VERIFICATION_FAILED.value,
        OperationalStatus.CLOSURE_BLOCKED.value,
    },
    OperationalStatus.VERIFICATION_FAILED.value: {
        OperationalStatus.REOPENED.value,
        OperationalStatus.REPLANNING.value,
        OperationalStatus.HUMAN_REVIEW.value,
        OperationalStatus.AWAITING_VERIFICATION.value,
        OperationalStatus.VERIFIED_CLOSED.value,
    },
    OperationalStatus.HUMAN_REVIEW.value: set(),
    OperationalStatus.VERIFIED_CLOSED.value: set(),
    OperationalStatus.REOPENED.value: {OperationalStatus.TRIAGED.value, OperationalStatus.PLANNING.value},

    # Compatibility states for existing application flow
    OperationalStatus.NEW.value: {
        OperationalStatus.RECORDED_PENDING_REVIEW.value,
        OperationalStatus.CLASSIFIED.value,
        OperationalStatus.TRIAGED.value,
        OperationalStatus.SUBMITTED.value,
        OperationalStatus.NEEDS_CLARIFICATION.value,
    },
    OperationalStatus.RECORDED_PENDING_REVIEW.value: {OperationalStatus.CLASSIFIED.value, OperationalStatus.HUMAN_REVIEW.value, OperationalStatus.TRIAGED.value},
    OperationalStatus.AWAITING_CLARIFICATION.value: {OperationalStatus.CLASSIFIED.value, OperationalStatus.HUMAN_REVIEW.value, OperationalStatus.NEEDS_CLARIFICATION.value},
    OperationalStatus.AWAITING_HUMAN_REVIEW.value: set(),
    OperationalStatus.AWAITING_EVIDENCE_RETAKE.value: {OperationalStatus.HUMAN_REVIEW.value, OperationalStatus.CLASSIFIED.value},
    OperationalStatus.VALIDATING.value: {OperationalStatus.SIMULATING.value, OperationalStatus.PLANNING.value, OperationalStatus.ESCALATED.value, OperationalStatus.HUMAN_REVIEW.value},
    OperationalStatus.SIMULATING.value: {
        OperationalStatus.VERIFYING_CLOSURE.value,
        OperationalStatus.RECOVERING.value,
        OperationalStatus.IN_PROGRESS_SIMULATED.value,
        OperationalStatus.PLAN_FAILED.value,
    },
    OperationalStatus.VERIFYING_CLOSURE.value: {
        OperationalStatus.VERIFIED_CLOSED.value,
        OperationalStatus.SIMULATED_RESOLVED.value,
        OperationalStatus.CLOSURE_BLOCKED.value,
        OperationalStatus.AWAITING_VERIFICATION.value,
        OperationalStatus.VERIFICATION_FAILED.value,
    },
    OperationalStatus.RECOVERING.value: {OperationalStatus.VALIDATING.value, OperationalStatus.PLANNING.value, OperationalStatus.ESCALATED.value, OperationalStatus.HUMAN_REVIEW.value},
    OperationalStatus.CLOSURE_BLOCKED.value: {
        OperationalStatus.REPLANNING.value,
        OperationalStatus.RECOVERING.value,
        OperationalStatus.HUMAN_REVIEW.value,
        OperationalStatus.ESCALATED.value,
        OperationalStatus.AWAITING_VERIFICATION.value,
        OperationalStatus.VERIFIED_CLOSED.value,
        OperationalStatus.SIMULATED_RESOLVED.value,
    },
    OperationalStatus.ESCALATED.value: set(),
    OperationalStatus.SIMULATED_RESOLVED.value: set(),
    OperationalStatus.RESOLVED.value: set(),
    OperationalStatus.DUPLICATE.value: set(),
}


def normalize_status(value: str | OperationalStatus | None) -> str:
    """Return a canonical status string."""
    if value is None:
        raise TransitionError("Status must not be None.")
    if isinstance(value, OperationalStatus):
        return value.value
    return str(value).upper()


def is_allowed_transition(current: str | OperationalStatus | None, next_status: str | OperationalStatus) -> bool:
    """Return True when a transition is explicitly permitted."""
    current_key = normalize_status(current)
    next_key = normalize_status(next_status)
    allowed = _ALLOWED_TRANSITIONS.get(current_key, set())
    return next_key in allowed


def validate_transition(
    current: str | OperationalStatus | None,
    next_status: str | OperationalStatus,
    *,
    verification_result: VerificationResult | Mapping[str, object] | None = None,
    incident_id: str | None = None,
) -> str:
    """Validate a transition and enforce the tracker closure gate.

    The tracker requires that VERIFIED_CLOSED can only be reached when a valid,
    passing VerificationResult has been produced for that incident. The app keeps
    SIMULATED_RESOLVED for compatibility with existing demo behavior, but it is never
    treated as a real municipal closure equivalent.
    """
    current_key = normalize_status(current)
    next_key = normalize_status(next_status)
    if not is_allowed_transition(current_key, next_key):
        raise TransitionError(f"Invalid state transition from {current_key} to {next_key}.")

    if next_key == OperationalStatus.VERIFIED_CLOSED.value:
        if verification_result is None:
            raise TransitionError("VERIFIED_CLOSED requires a passing VerificationResult.")

        if isinstance(verification_result, Mapping):
            passed = verification_result.get("passed") is True
            result_value = verification_result.get("result")
            if not passed:
                raise TransitionError("VERIFIED_CLOSED requires a passing VerificationResult.")
            if incident_id and verification_result.get("incident_id") not in (None, incident_id):
                raise TransitionError("VerificationResult incident_id does not match the incident being closed.")
            if result_value is not None and str(result_value) != VerificationOutcome.VERIFIED.value:
                raise TransitionError("VERIFIED_CLOSED requires a VERIFIED outcome.")
            return next_key

        if not getattr(verification_result, "passed", False):
            raise TransitionError("VERIFIED_CLOSED requires a passing VerificationResult.")
        if getattr(verification_result, "result", None) not in (None, VerificationOutcome.VERIFIED, VerificationOutcome.VERIFIED.value):
            raise TransitionError("VERIFIED_CLOSED requires a VERIFIED outcome.")
        if incident_id and getattr(verification_result, "incident_id", None) not in (None, incident_id):
            raise TransitionError("VerificationResult incident_id does not match the incident being closed.")

    # Closed-state gate: a successful simulation or planner claim never counts as verified closure.
    if next_key == OperationalStatus.SIMULATED_RESOLVED.value and current_key not in {OperationalStatus.AWAITING_VERIFICATION.value, OperationalStatus.VERIFYING_CLOSURE.value}:
        raise TransitionError("SIMULATED_RESOLVED is a compatibility-only status and must only follow the closure gate.")

    if next_key == OperationalStatus.VERIFICATION_FAILED.value and "VERIFICATION_FAILED" not in current_key:
        return next_key

    return next_key


def transition_status(
    current: str | OperationalStatus | None,
    next_status: str | OperationalStatus,
    *,
    verification_result: VerificationResult | Mapping[str, object] | None = None,
    incident_id: str | None = None,
) -> str:
    """Validate and return the normalized next state."""
    return validate_transition(
        current,
        next_status,
        verification_result=verification_result,
        incident_id=incident_id,
    )


__all__ = [
    "TransitionError",
    "ALLOWED_TRANSITIONS",
    "normalize_status",
    "is_allowed_transition",
    "validate_transition",
    "transition_status",
]

ALLOWED_TRANSITIONS = _ALLOWED_TRANSITIONS
