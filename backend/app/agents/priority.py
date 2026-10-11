"""
JanSetu AI — Priority Intelligence Agent.

Responsible for:
- Calculating transparent priority scores (0 to 100) and bands (Low, Medium, High, Critical)
- Evaluating explicitly supported severity indicators, exposure factors, and arterial transit hazards
- Preserving objectivity without inventing absent information
- Executing concurrently with GeoCivic Agent in LangGraph
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.graph.state import IncidentState
from app.schemas.incident import (
    AuditEvent,
    IncidentExtraction,
    PriorityAssessment,
    PriorityBand,
)

logger = logging.getLogger("jansetu.priority")


def calculate_transparent_priority(
    raw_input: str,
    facts: IncidentExtraction | None,
) -> PriorityAssessment:
    """
    Calculate transparent priority score based strictly on explicit input evidence.
    
    Rubric:
    1. Category Base:
       - waterlogging: 65 (high hydraulic/transit disruption potential)
       - pothole: 50 (kinetic vehicle/safety risk)
       - garbage: 40 (public health and hygiene)
       - other/uncertain: 35
    2. Severity Indicators: +10 per concrete indicator (max +30)
    3. Public Exposure Clues: +15 per arterial/pedestrian/school factor (max +35)
    """
    category = facts.category.lower() if facts else "uncertain_other"
    
    # Base category weighting
    if "waterlog" in category:
        base_score = 65
    elif "pothole" in category:
        base_score = 50
    elif "garbage" in category:
        base_score = 40
    else:
        base_score = 35

    urgency_factors: List[str] = []
    severity_bonus = 0
    exposure_bonus = 0

    if facts:
        # Severity indicators explicitly extracted
        for ind in facts.severity_indicators:
            severity_bonus += 10
            urgency_factors.append(f"Severity: {ind}")
        severity_bonus = min(30, severity_bonus)

        # Public exposure clues explicitly extracted
        for exp in facts.public_exposure_clues:
            exposure_bonus += 15
            urgency_factors.append(f"Public Exposure: {exp}")
        exposure_bonus = min(35, exposure_bonus)

    # Keyword safety check on raw description for unparsed critical terms
    desc_lower = raw_input.lower()
    if any(k in desc_lower for k in ("hospital", "ambulance", "emergency", "fatal", "arterial", "highway")):
        if not any("arterial" in uf.lower() or "emergency" in uf.lower() for uf in urgency_factors):
            exposure_bonus += 15
            urgency_factors.append("Public Exposure: Emergency transit corridor detected")

    total_score = min(100, max(10, base_score + severity_bonus + exposure_bonus))

    # Determine band
    if total_score >= 80:
        band = PriorityBand.CRITICAL.value
    elif total_score >= 65:
        band = PriorityBand.HIGH.value
    elif total_score >= 45:
        band = PriorityBand.MEDIUM.value
    else:
        band = PriorityBand.LOW.value

    explanation = (
        f"Calculated from category '{category}' (base: {base_score}), "
        f"{len(facts.severity_indicators) if facts else 0} severity indicators (+{severity_bonus}), "
        f"and {len(facts.public_exposure_clues) if facts else 0} exposure clues (+{exposure_bonus})."
    )

    return PriorityAssessment(
        priority_score=total_score,
        priority_band=band,
        explanation=explanation,
        urgency_factors=urgency_factors,
    )


def priority_node(state: IncidentState) -> Dict[str, Any]:
    """
    Priority Intelligence Agent node. Runs concurrently with GeoCivic Agent.
    
    Returns:
    - priority: PriorityAssessment
    - audit_timeline: list of AuditEvent
    
    Does NOT update the 'status' key to prevent state merge collisions with parallel branches.
    """
    raw_input = state.get("raw_input", "")
    facts = state.get("extracted_facts")

    assessment = calculate_transparent_priority(raw_input, facts)

    now_iso = datetime.now(timezone.utc).isoformat()
    audit_event = AuditEvent(
        timestamp=now_iso,
        agent="Priority Intelligence",
        action="Assessed Priority & Urgency",
        result=f"Band: {assessment.priority_band}, Score: {assessment.priority_score}/100",
    )

    logger.info("Priority complete: score=%d, band=%s", assessment.priority_score, assessment.priority_band)

    return {
        "priority": assessment,
        "audit_timeline": [audit_event.model_dump()],
    }
