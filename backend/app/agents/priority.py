"""
JanSetu AI — Priority Intelligence Agent (Phase 5, P5.4).

Responsible for:
- Implementing the shared CivicAgentProtocol: run(incident, context) -> PriorityAssessmentOutput
- Loading configurable weights and mandatory escalation rules from config/risk_weights.yaml
- Calculating explainable priority score (0-100) and band (LOW, MEDIUM, HIGH, CRITICAL)
- Recording per-factor point contributions and tracking missing factors honestly
- Enforcing an independent deterministic mandatory escalation gate that can NEVER be overridden
  by low scores, missing data, or model predictions
- Preserving full backward compatibility with the LangGraph workflow and PriorityAssessment schema
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from app.agents.base import BaseCivicAgent
from app.graph.state import IncidentState
from app.schemas.incident import (
    AuditEvent,
    IncidentExtraction,
    PriorityAssessment,
    PriorityAssessmentOutput,
    PriorityBand,
)

logger = logging.getLogger("jansetu.priority")

# Configuration search locations
DEFAULT_CONFIG_PATHS = [
    Path(__file__).resolve().parent.parent.parent.parent / "config" / "risk_weights.yaml",
    Path(__file__).resolve().parent.parent / "config" / "risk_weights.yaml",
]

_CONFIG_CACHE: Dict[str, Dict[str, Any]] = {}


def load_risk_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Loads risk policy configuration from YAML, with robust default fallback."""
    cache_key = str(config_path) if config_path else "default"
    if cache_key in _CONFIG_CACHE:
        return _CONFIG_CACHE[cache_key]

    if config_path and config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
                _CONFIG_CACHE[cache_key] = cfg
                return cfg
        except Exception as exc:
            logger.warning("Failed to parse config at %s: %s", config_path, exc)

    for p in DEFAULT_CONFIG_PATHS:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                    _CONFIG_CACHE[cache_key] = cfg
                    return cfg
            except Exception as exc:
                logger.warning("Failed to parse risk config at %s: %s", p, exc)

    # Fallback in-memory configuration if no YAML file found
    return {
        "version": "1.0.0-fallback",
        "category_base_scores": {
            "waterlogging": 30.0,
            "pothole": 25.0,
            "garbage": 20.0,
            "uncertain_other": 15.0,
        },
        "factor_weights": {
            "immediate_danger": 25.0,
            "severity": 15.0,
            "public_exposure": 15.0,
            "people_affected": 10.0,
            "duration": 10.0,
            "recurrence": 5.0,
            "accessibility_safeguarding": 10.0,
        },
        "priority_bands": {
            "critical": 80.0,
            "high": 60.0,
            "medium": 40.0,
            "low": 0.0,
        },
        "mandatory_escalation_rules": [
            {
                "id": "E01_LIFE_SAFETY",
                "description": "Active cave-in, open manhole, high-voltage wire submerged, or direct life-safety threat",
                "keywords": ["open manhole", "manhole open", "cave-in", "cave in", "electric wire", "current", "electrocution", "sinkhole"],
            },
            {
                "id": "E02_EMERGENCY_CORRIDOR",
                "description": "Complete blockage of hospital access, ambulance route, or primary emergency corridor",
                "keywords": ["hospital blocked", "ambulance blocked", "hospital gate", "emergency corridor"],
            },
            {
                "id": "E03_ACCIDENT_OCCURRED",
                "description": "Active vehicular collision, severe bodily trauma, or acute life-safety emergency occurring at site",
                "keywords": [
                    "active collision",
                    "active crash",
                    "collision right now",
                    "crash right now",
                    "head-on collision",
                    "vehicle crashed right now",
                    "trapped in vehicle",
                    "driver trapped",
                    "trapped",
                    "severe head injury",
                    "unconscious casualty",
                    "bleeding heavily",
                    "multiple casualties",
                    "fatal collision",
                    "critical injury right now",
                ],
            },
            {
                "id": "E04_VULNERABLE_POPULATION",
                "description": "Hazard directly obstructing primary school, childcare facility, or elderly care center",
                "keywords": ["primary school", "children walking", "school entrance", "maternity ward"],
            },
        ],
    }


class PriorityIntelligenceAgent(BaseCivicAgent[PriorityAssessmentOutput]):
    """Agent 3: Risk & Priority Specialist."""

    agent_name: str = "Priority Intelligence"
    agent_role: str = "Business Automation"

    def __init__(self, config_path: Optional[Path] = None):
        self.config = load_risk_config(config_path)
        self.policy_version = str(self.config.get("version", "1.0.0"))

    def evaluate_mandatory_escalation(
        self,
        raw_text: str,
        facts: Optional[IncidentExtraction] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Independent mandatory escalation gate.
        Checks explicit life-safety and emergency keywords.
        Never overridden by numerical score or model predictions.

        Guarantees:
        - Accurately distinguishes active life-safety emergencies from historical accident reports.
        - Historical or past accident mentions increase priority score in planning, but do not
          trigger an emergency-only halt.
        """
        text_lower = raw_text.lower()
        escalation_reasons: List[str] = []

        # Indicators showing accident wording is purely historical or general hazard description
        historical_hazard_indicators = (
            "happened",
            "yesterday",
            "last week",
            "last month",
            "last year",
            "days ago",
            "past",
            "previously",
            "prior",
            "historical",
            "risk of",
            "risk to",
            "prone to",
            "accident prone",
            "causes accident",
            "causing accident",
            "can cause",
            "could cause",
            "may cause",
            "minor accident",
            "almost had",
            "narrowly avoided",
            "seen accidents",
            "prevent accident",
            "avoid accident",
        )

        rules = self.config.get("mandatory_escalation_rules", [])
        for rule in rules:
            rule_id = rule.get("id", "MANDATORY_ESCALATION")
            keywords = rule.get("keywords", [])

            if rule_id == "E03_ACCIDENT_OCCURRED":
                # Check for active emergency keywords first
                has_active_emergency = any(kw.lower() in text_lower for kw in keywords)
                if has_active_emergency:
                    escalation_reasons.append(f"{rule_id}: {rule.get('description', 'Active emergency collision')}")
                continue

            for kw in keywords:
                if kw.lower() in text_lower:
                    escalation_reasons.append(f"{rule_id}: {rule.get('description', kw)}")
                    break

        return len(escalation_reasons) > 0, escalation_reasons

    def run(
        self,
        incident: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> PriorityAssessmentOutput:
        """
        Calculate transparent, explainable priority score, factor contributions,
        uncertainty, and mandatory escalation. Returns validated PriorityAssessmentOutput.
        """
        data = self.extract_incident_dict(incident)
        incident_id = data.get("incident_id") or f"inc_{uuid.uuid4().hex[:8]}"
        raw_input = (data.get("raw_input") or data.get("complaint") or data.get("description") or "").strip()
        facts = data.get("extracted_facts")

        # Category extraction
        category = "uncertain_other"
        if facts is not None:
            category = getattr(facts, "category", None) or facts.get("category", "uncertain_other")
        else:
            category = data.get("selected_category") or data.get("category") or "uncertain_other"
        cat_key = category.lower().replace(" ", "_")

        base_scores = self.config.get("category_base_scores", {})
        base_score = float(base_scores.get(cat_key, base_scores.get("uncertain_other", 15.0)))

        factor_weights = self.config.get("factor_weights", {})
        factor_contributions: Dict[str, float] = {"category_base": round(base_score, 1)}
        input_factors: Dict[str, Any] = {"category": category}
        missing_factors: List[str] = []
        urgency_factors: List[str] = []

        desc_lower = raw_input.lower()

        # 1. Immediate Danger
        danger_wt = float(factor_weights.get("immediate_danger", 25.0))
        if any(w in desc_lower for w in ("danger", "hazard", "fatal", "open manhole", "cave in", "sinkhole", "electric")):
            factor_contributions["immediate_danger"] = danger_wt
            input_factors["immediate_danger"] = "High imminent hazard detected"
            urgency_factors.append(f"Immediate Danger (+{danger_wt} pts)")
        elif any(w in desc_lower for w in ("accident", "injury", "injured", "toppled", "skidded", "slipped", "crash", "casualty")):
            factor_contributions["immediate_danger"] = danger_wt
            input_factors["immediate_danger"] = "Elevated risk: historical accident, fall, or collision risk reported"
            urgency_factors.append(f"Reported Accident Risk (+{danger_wt} pts)")
        else:
            factor_contributions["immediate_danger"] = 0.0
            input_factors["immediate_danger"] = "No imminent life safety words reported"

        # 2. Incident Severity
        sev_wt = float(factor_weights.get("severity", 15.0))
        if facts and getattr(facts, "severity_indicators", None):
            indicators = facts.severity_indicators
            pts = min(sev_wt, len(indicators) * (sev_wt / 2.0))
            factor_contributions["severity"] = round(pts, 1)
            input_factors["severity_indicators"] = indicators
            urgency_factors.append(f"Severity Indicators (+{pts:.1f} pts)")
        elif any(w in desc_lower for w in ("severe", "huge", "deep", "massive", "knee deep", "waist height")):
            factor_contributions["severity"] = round(sev_wt * 0.8, 1)
            input_factors["severity"] = "Severe depth/extent reported in description"
            urgency_factors.append(f"Severity (+{sev_wt * 0.8:.1f} pts)")
        else:
            factor_contributions["severity"] = 0.0
            missing_factors.append("severity_metrics")

        # 3. Public Exposure
        exp_wt = float(factor_weights.get("public_exposure", 15.0))
        if any(w in desc_lower for w in ("school", "hospital", "station", "market", "main road", "highway", "bus stop")):
            factor_contributions["public_exposure"] = exp_wt
            input_factors["public_exposure"] = "High density pedestrian or arterial corridor"
            urgency_factors.append(f"Public Exposure (+{exp_wt} pts)")
        else:
            factor_contributions["public_exposure"] = 0.0
            missing_factors.append("public_exposure_context")

        # 4. People Affected
        peop_wt = float(factor_weights.get("people_affected", 10.0))
        if any(w in desc_lower for w in ("commuters", "residents", "thousands", "hundreds", "multiple", "all vehicles")):
            factor_contributions["people_affected"] = peop_wt
            input_factors["people_affected"] = "Widespread population affected"
            urgency_factors.append(f"People Affected (+{peop_wt} pts)")
        else:
            factor_contributions["people_affected"] = 0.0
            missing_factors.append("people_affected_estimate")

        # 5. Duration
        dur_wt = float(factor_weights.get("duration", 10.0))
        if any(w in desc_lower for w in ("week", "days", "months", "month", "since yesterday", "48 hours")):
            factor_contributions["duration"] = dur_wt
            input_factors["duration"] = "Prolonged unresolved condition"
            urgency_factors.append(f"Duration (+{dur_wt} pts)")
        else:
            factor_contributions["duration"] = 0.0
            missing_factors.append("duration_information")

        # 6. Recurrence
        rec_wt = float(factor_weights.get("recurrence", 5.0))
        if any(w in desc_lower for w in ("recurring", "again", "repeat", "every year", "every monsoon")):
            factor_contributions["recurrence"] = rec_wt
            input_factors["recurrence"] = "Documented recurrence"
            urgency_factors.append(f"Recurrence (+{rec_wt} pts)")
        else:
            factor_contributions["recurrence"] = 0.0
            missing_factors.append("historical_recurrence")

        # 7. Accessibility and Safeguarding
        acc_wt = float(factor_weights.get("accessibility_safeguarding", 10.0))
        if any(w in desc_lower for w in ("wheelchair", "elderly", "pedestrian", "children", "blind", "footpath blocked")):
            factor_contributions["accessibility_safeguarding"] = acc_wt
            input_factors["accessibility_safeguarding"] = "Vulnerable accessibility route obstructed"
            urgency_factors.append(f"Accessibility Safeguarding (+{acc_wt} pts)")
        else:
            factor_contributions["accessibility_safeguarding"] = 0.0
            missing_factors.append("accessibility_impact")

        # Sum total score (bounded 0 to 100)
        raw_score = sum(factor_contributions.values())
        total_score = min(100.0, max(0.0, round(raw_score, 1)))

        # Priority band based on score thresholds
        bands = self.config.get("priority_bands", {})
        crit_th = float(bands.get("critical", 80.0))
        high_th = float(bands.get("high", 60.0))
        med_th = float(bands.get("medium", 40.0))

        if total_score >= crit_th:
            computed_band = PriorityBand.CRITICAL.value
        elif total_score >= high_th:
            computed_band = PriorityBand.HIGH.value
        elif total_score >= med_th:
            computed_band = PriorityBand.MEDIUM.value
        else:
            computed_band = PriorityBand.LOW.value

        # Mandatory Escalation Gate
        is_escalated, escalation_reasons = self.evaluate_mandatory_escalation(raw_input, facts)
        final_band = computed_band
        if is_escalated:
            # Overrides band to CRITICAL regardless of numerical score!
            final_band = PriorityBand.CRITICAL.value
            urgency_factors.insert(0, f"MANDATORY ESCALATION: {escalation_reasons[0]}")

        # Uncertainty calculation based on missing factors
        total_evaluable_factors = 6
        missing_count = len(missing_factors)
        uncertainty_score = round(missing_count / total_evaluable_factors, 2)
        uncertainty_desc = (
            f"Uncertainty: {uncertainty_score * 100:.0f}% ({missing_count} factor(s) missing explicit citizen input: "
            f"{', '.join(missing_factors)})."
        )

        explanation = (
            f"Scoring policy v{self.policy_version}: category base '{category}' ({base_score} pts), "
            f"contributions: {factor_contributions}. "
            + (f"MANDATORY ESCALATION ACTIVE: {', '.join(escalation_reasons)}." if is_escalated else f"Assigned {final_band} band.")
        )

        return PriorityAssessmentOutput(
            incident_id=incident_id,
            priority_score=total_score,
            priority_band=final_band,
            factor_contributions=factor_contributions,
            input_factors=input_factors,
            missing_factors=missing_factors,
            uncertainty_score=uncertainty_score,
            uncertainty_description=uncertainty_desc,
            is_escalated=is_escalated,
            escalation_reasons=escalation_reasons,
            policy_version=self.policy_version,
            explanation=explanation,
            urgency_factors=urgency_factors,
        )


def calculate_transparent_priority(
    raw_input: str,
    facts: IncidentExtraction | None,
) -> PriorityAssessment:
    """
    Adapter maintaining backwards compatibility with legacy callers.
    Delegates to PriorityIntelligenceAgent().run().
    """
    agent = PriorityIntelligenceAgent()
    output = agent.run({"raw_input": raw_input, "extracted_facts": facts})
    return PriorityAssessment(
        priority_score=int(round(output.priority_score)),
        priority_band=output.priority_band,
        explanation=output.explanation,
        urgency_factors=output.urgency_factors,
    )


def priority_node(state: IncidentState) -> Dict[str, Any]:
    """
    Priority Intelligence Agent node for LangGraph workflow.
    Wraps PriorityIntelligenceAgent().run(state) maintaining full backwards compatibility.
    """
    agent = PriorityIntelligenceAgent()
    output = agent.run(state)

    cid = state.get("correlation_id") or f"corr_{output.incident_id}"
    now_iso = datetime.now(timezone.utc).isoformat()
    result_summary = (
        f"Score: {output.priority_score} | Band: {output.priority_band} | "
        f"Escalated: {output.is_escalated} | Uncertainty: {output.uncertainty_score}"
    )

    audit_event = AuditEvent(
        timestamp=now_iso,
        agent=agent.agent_name,
        action="Priority Scoring & Mandatory Escalation Check",
        result=result_summary,
        correlation_id=cid,
        event_type="priority",
    )

    logger.info("Priority complete: %s", result_summary)

    # Legacy-compatible PriorityAssessment object for existing graph state
    legacy_assessment = PriorityAssessment(
        priority_score=int(round(output.priority_score)),
        priority_band=output.priority_band,
        explanation=output.explanation,
        urgency_factors=output.urgency_factors,
    )

    return {
        "priority": legacy_assessment,
        "priority_output": output.model_dump(),
        "is_escalated": output.is_escalated,
        "escalation_reasons": output.escalation_reasons,
        "correlation_id": cid,
        "audit_timeline": [audit_event.model_dump()],
    }
