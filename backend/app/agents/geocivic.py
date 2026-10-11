"""
JanSetu AI — GeoCivic Agent.

Responsible for:
- Reading confirmed coordinates, accuracy metadata, and description clues
- Computing exact Haversine distances against the synthetic civic registry
- Identifying spatial clusters, nearby active incidents, and duplicate candidates
- Preserving duplicate reports transparently without silent deletion
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.geo_utils import find_nearby_and_duplicates
from app.graph.state import IncidentState
from app.schemas.incident import (
    AuditEvent,
    GeoAnalysis,
    IncidentLocation,
)

logger = logging.getLogger("jansetu.geocivic")


def geocivic_node(state: IncidentState) -> Dict[str, Any]:
    """
    GeoCivic Agent node. Runs concurrently with Priority Intelligence Agent.
    
    Returns:
    - geo_context: GeoAnalysis
    - audit_timeline: list of AuditEvent
    
    Does NOT update the 'status' key to prevent state merge collisions with parallel branches.
    """
    facts = state.get("extracted_facts")
    raw_input = state.get("raw_input", "")
    location_data = state.get("location_data")

    # Extract coordinates safely
    lat: Optional[float] = None
    lon: Optional[float] = None

    if isinstance(location_data, IncidentLocation):
        lat = location_data.latitude
        lon = location_data.longitude
    elif isinstance(location_data, dict):
        lat = location_data.get("latitude")
        lon = location_data.get("longitude")

    category = facts.category if facts else state.get("selected_category", "uncertain_other")

    # Perform geospatial duplicate and proximity lookup
    analysis = find_nearby_and_duplicates(
        category=category,
        latitude=lat,
        longitude=lon,
        description_text=raw_input,
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    result_summary = (
        f"Nearby: {len(analysis.nearby_incident_ids)} | "
        f"Duplicate: {analysis.is_duplicate}"
        + (f" of {analysis.duplicate_of_id} (Dist: {analysis.distance_to_nearest_meters}m)" if analysis.is_duplicate else "")
    )

    audit_event = AuditEvent(
        timestamp=now_iso,
        agent="GeoCivic Agent",
        action="Geospatial Proximity & Duplicate Check",
        result=result_summary,
    )

    logger.info("GeoCivic complete: %s", result_summary)

    return {
        "geo_context": analysis,
        "audit_timeline": [audit_event.model_dump()],
    }
