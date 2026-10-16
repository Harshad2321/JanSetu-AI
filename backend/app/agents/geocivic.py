"""
JanSetu AI — GeoCivic Agent (Phase 5, P5.3).

Responsible for:
- Implementing the shared CivicAgentProtocol: run(incident, context) -> GeoSpatialOutput
- Reading confirmed coordinates, accuracy metadata, and description clues
- Computing exact Haversine distances against the synthetic civic registry
- Evaluating text similarity via TF-IDF cosine similarity as supporting evidence
- Identifying spatial clusters via DBSCAN (eps=100m, min_samples=2)
- Flagging duplicate candidates as UNCONFIRMED without auto-merging or deleting reports
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.agents.base import BaseCivicAgent
from app.core.geo_utils import (
    SYNTHETIC_CIVIC_INCIDENTS,
    find_nearby_and_duplicates,
    run_dbscan_clustering,
    validate_coordinates,
)
from app.graph.state import IncidentState
from app.schemas.incident import (
    AuditEvent,
    DuplicateCandidateRecord,
    GeoAnalysis,
    GeoSpatialOutput,
    IncidentLocation,
)

logger = logging.getLogger("jansetu.geocivic")


class GeoSpatialAgent(BaseCivicAgent[GeoSpatialOutput]):
    """Agent 2: Geo-Spatial Intelligence Specialist."""

    agent_name: str = "GeoCivic Agent"
    agent_role: str = "Research"

    def run(
        self,
        incident: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> GeoSpatialOutput:
        """
        Execute geospatial proximity, text similarity, duplicate candidate generation,
        and DBSCAN spatial clustering. Returns validated GeoSpatialOutput.
        """
        data = self.extract_incident_dict(incident)

        incident_id = data.get("incident_id") or f"inc_{uuid.uuid4().hex[:8]}"
        raw_input = (data.get("raw_input") or data.get("complaint") or data.get("description") or "").strip()
        location_data = data.get("location_data")
        facts = data.get("extracted_facts")

        # Extract coordinates
        lat: Optional[float] = None
        lon: Optional[float] = None

        if isinstance(location_data, IncidentLocation):
            lat = location_data.latitude
            lon = location_data.longitude
        elif isinstance(location_data, dict):
            lat = location_data.get("latitude")
            lon = location_data.get("longitude")

        category = "uncertain_other"
        if facts is not None:
            category = getattr(facts, "category", None) or facts.get("category", "uncertain_other")
        else:
            category = data.get("selected_category") or data.get("category") or "uncertain_other"

        # 1. Proximity and duplicate candidates calculation
        geo_analysis, candidates = find_nearby_and_duplicates(
            category=category,
            latitude=lat,
            longitude=lon,
            description_text=raw_input,
            current_incident_id=incident_id,
        )

        # 2. DBSCAN Clustering against registry
        if validate_coordinates(lat, lon):
            clustering_points: List[Dict[str, Any]] = [
                {"incident_id": inc.incident_id, "latitude": inc.latitude, "longitude": inc.longitude}
                for inc in SYNTHETIC_CIVIC_INCIDENTS
            ]
            clustering_points.append({"incident_id": incident_id, "latitude": lat, "longitude": lon})
            cluster_result = run_dbscan_clustering(
                points=clustering_points,
                eps_meters=150.0,
                min_samples=2,
            )
            cluster_id = cluster_result["cluster_assignments"].get(incident_id)
            is_hotspot = cluster_id is not None
            hotspot_summary = cluster_result["summary"]
        else:
            cluster_id = None
            is_hotspot = False
            hotspot_summary = "Spatial clustering omitted: incident coordinates missing or unverified."

        return GeoSpatialOutput(
            incident_id=incident_id,
            latitude=lat,
            longitude=lon,
            duplicate_candidates=candidates,
            has_unconfirmed_duplicates=len(candidates) > 0,
            dbscan_cluster_id=cluster_id,
            is_hotspot=is_hotspot,
            hotspot_summary=hotspot_summary,
            nearby_incident_ids=geo_analysis.nearby_incident_ids,
            geo_analysis=geo_analysis,
        )


def geocivic_node(state: IncidentState) -> Dict[str, Any]:
    """
    GeoCivic Agent node for LangGraph workflow.
    Wraps GeoSpatialAgent().run(state) maintaining full backwards compatibility.
    """
    agent = GeoSpatialAgent()
    output = agent.run(state)

    cid = state.get("correlation_id") or f"corr_{output.incident_id}"
    now_iso = datetime.now(timezone.utc).isoformat()
    result_summary = (
        f"Nearby: {len(output.nearby_incident_ids)} | "
        f"Candidates: {len(output.duplicate_candidates)} (UNCONFIRMED) | "
        f"DBSCAN Cluster: {output.dbscan_cluster_id if output.dbscan_cluster_id is not None else 'Noise/None'}"
    )

    audit_event = AuditEvent(
        timestamp=now_iso,
        agent=agent.agent_name,
        action="Geospatial Proximity, Text Similarity & Clustering",
        result=result_summary,
        correlation_id=cid,
        event_type="geospatial",
    )

    logger.info("GeoCivic complete: %s", result_summary)

    return {
        "geo_context": output.geo_analysis,
        "duplicate_candidates": [c.model_dump() for c in output.duplicate_candidates],
        "correlation_id": cid,
        "audit_timeline": [audit_event.model_dump()],
    }
