"""
JanSetu AI — Geospatial Utilities & Spatial Intelligence (Phase 5, P5.3).

Provides:
- Exact Haversine distance calculations with coordinate boundary validation
- Text similarity comparison via TF-IDF vectorization and cosine similarity
- Spatial DBSCAN clustering with spherical haversine metric on radians
- Synthetic active incident registry across civic sectors
- Proximity clustering, hotspot summaries, and unconfirmed duplicate candidate detection
"""

from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.schemas.incident import (
    DuplicateCandidateRecord,
    GeoAnalysis,
)


class SyntheticIncidentRecord(BaseModel):
    """Synthetic active incident record for proximity and duplicate testing."""
    incident_id: str
    category: str
    latitude: float
    longitude: float
    description: str
    status: str = "ACTIVE"


# Pre-seeded active synthetic incidents across urban sectors
SYNTHETIC_CIVIC_INCIDENTS: List[SyntheticIncidentRecord] = [
    SyntheticIncidentRecord(
        incident_id="INC-1002",
        category="pothole",
        latitude=28.6140,
        longitude=77.2092,
        description="Large asphalt pothole on Main St northbound lane near Connaught Place",
    ),
    SyntheticIncidentRecord(
        incident_id="INC-0998",
        category="pothole",
        latitude=28.6143,
        longitude=77.2096,
        description="Cracked road surface with deep cavity on Main St corridor",
    ),
    SyntheticIncidentRecord(
        incident_id="INC-2041",
        category="waterlogging",
        latitude=28.5358,
        longitude=77.3912,
        description="Severe stormwater accumulation blocking right lane of Expressway Underpass",
    ),
    SyntheticIncidentRecord(
        incident_id="INC-3088",
        category="garbage",
        latitude=28.7045,
        longitude=77.1028,
        description="Overflowing municipal waste bin spilling onto public pedestrian walkway",
    ),
]


def validate_coordinates(
    latitude: Optional[float],
    longitude: Optional[float],
) -> bool:
    """Validate that coordinates are numbers within valid geographical ranges."""
    if latitude is None or longitude is None:
        return False
    try:
        lat = float(latitude)
        lon = float(longitude)
        if math.isnan(lat) or math.isnan(lon) or math.isinf(lat) or math.isinf(lon):
            return False
        return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0
    except (ValueError, TypeError):
        return False


def haversine_distance_meters(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """
    Calculate the great-circle distance between two geographic coordinates in meters
    using the spherical Haversine formula.
    """
    if not validate_coordinates(lat1, lon1) or not validate_coordinates(lat2, lon2):
        raise ValueError("Invalid coordinates supplied to haversine_distance_meters.")

    earth_radius_m = 6_371_000.0  # Mean radius of Earth in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return earth_radius_m * c


def compute_text_similarity(text1: str, text2: str) -> float:
    """
    Computes TF-IDF cosine similarity between two complaint descriptions.
    Returns a score between 0.0 and 1.0. Used strictly as supporting evidence.
    """
    if not text1 or not text2 or not text1.strip() or not text2.strip():
        return 0.0

    try:
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            token_pattern=r"(?u)\b\w+\b",
            sublinear_tf=True,
        )
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        sim = float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
        return max(0.0, min(1.0, round(sim, 4)))
    except Exception:
        return 0.0


def run_dbscan_clustering(
    points: List[Dict[str, Any]],
    eps_meters: float = 100.0,
    min_samples: int = 2,
) -> Dict[str, Any]:
    """
    Executes DBSCAN spatial clustering on geographic coordinates using the spherical
    haversine distance metric.
    
    Guarantees:
    - Never treats missing coordinates as (0, 0).
    - Gracefully handles empty lists, single points, or points with invalid coords.
    - Explicitly represents noise (-1) as None (unclustered).
    
    Returns:
    {
      "cluster_assignments": {incident_id: Optional[int]},
      "clusters": {cluster_id: [incident_ids]},
      "num_clusters": int,
      "num_noise": int,
      "summary": str
    }
    """
    valid_points: List[Dict[str, Any]] = []
    for p in points:
        lat = p.get("latitude")
        lon = p.get("longitude")
        if validate_coordinates(lat, lon):
            valid_points.append(p)

    if len(valid_points) < min_samples:
        assignments = {p["incident_id"]: None for p in points if "incident_id" in p}
        return {
            "cluster_assignments": assignments,
            "clusters": {},
            "num_clusters": 0,
            "num_noise": len(valid_points),
            "summary": (
                f"DBSCAN: {len(valid_points)} point(s) with valid coordinates. "
                f"Insufficient points for clustering (min_samples={min_samples})."
            ),
        }

    # Earth radius in meters
    earth_radius_m = 6_371_000.0
    eps_radians = eps_meters / earth_radius_m

    # Convert coordinates to radians: [lat_rad, lon_rad]
    coords_rad = np.radians([[p["latitude"], p["longitude"]] for p in valid_points])

    db = DBSCAN(eps=eps_radians, min_samples=min_samples, metric="haversine")
    labels = db.fit_predict(coords_rad)

    cluster_assignments: Dict[str, Optional[int]] = {}
    clusters: Dict[int, List[str]] = {}
    num_noise = 0

    for p, label in zip(valid_points, labels):
        inc_id = p["incident_id"]
        if label >= 0:
            cluster_assignments[inc_id] = int(label)
            clusters.setdefault(int(label), []).append(inc_id)
        else:
            cluster_assignments[inc_id] = None
            num_noise += 1

    # Include points that had missing coordinates as unassigned
    for p in points:
        inc_id = p.get("incident_id")
        if inc_id and inc_id not in cluster_assignments:
            cluster_assignments[inc_id] = None

    num_clusters = len(clusters)
    summary = (
        f"DBSCAN clustering (eps={eps_meters}m, min_samples={min_samples}): "
        f"Identified {num_clusters} spatial cluster(s) across {len(valid_points)} valid incidents; "
        f"{num_noise} classified as noise/isolated."
    )

    return {
        "cluster_assignments": cluster_assignments,
        "clusters": clusters,
        "num_clusters": num_clusters,
        "num_noise": num_noise,
        "summary": summary,
    }


def find_nearby_and_duplicates(
    category: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    description_text: str = "",
    proximity_duplicate_threshold_m: float = 50.0,
    neighborhood_radius_m: float = 500.0,
    registry: Optional[List[SyntheticIncidentRecord]] = None,
    current_incident_id: str = "INC-NEW",
) -> Tuple[GeoAnalysis, List[DuplicateCandidateRecord]]:
    """
    Evaluate geospatial proximity, text similarity, and identify potential duplicate incidents.
    
    Guarantees:
    - Never silently merges or deletes candidate records.
    - Computes both spatial distance and TF-IDF text similarity.
    - All duplicate candidates are returned as UNCONFIRMED.
    """
    incidents = registry if registry is not None else SYNTHETIC_CIVIC_INCIDENTS
    duplicate_candidates: List[DuplicateCandidateRecord] = []

    has_coords = validate_coordinates(latitude, longitude)

    nearby_ids: List[str] = []
    min_dist: Optional[float] = None
    best_candidate_id: Optional[str] = None
    is_duplicate = False
    dup_conf = 0.0

    if has_coords:
        assert latitude is not None and longitude is not None
        scored_candidates: List[Tuple[float, SyntheticIncidentRecord]] = []

        for inc in incidents:
            if not validate_coordinates(inc.latitude, inc.longitude):
                continue
            dist = haversine_distance_meters(latitude, longitude, inc.latitude, inc.longitude)
            if dist <= neighborhood_radius_m:
                scored_candidates.append((dist, inc))

        scored_candidates.sort(key=lambda x: x[0])
        nearby_ids = [inc.incident_id for _, inc in scored_candidates]

        if scored_candidates:
            min_dist = scored_candidates[0][0]

        for dist, inc in scored_candidates:
            sim_score = compute_text_similarity(description_text, inc.description)
            norm_cat = category.lower().replace("_", "")
            inc_cat = inc.category.lower().replace("_", "")
            cat_match = norm_cat in inc_cat or inc_cat in norm_cat
            cat_comp = f"MATCH ({category} == {inc.category})" if cat_match else f"DIFFERENT ({category} != {inc.category})"

            # If within duplicate threshold (50m) or high text similarity with proximity
            if dist <= proximity_duplicate_threshold_m or (dist <= neighborhood_radius_m and sim_score >= 0.4):
                rationale = (
                    f"Reported {dist:.1f}m away from existing {inc.incident_id}. "
                    f"Category comparison: {cat_comp}. Text similarity: {sim_score:.2f}."
                )
                cand_record = DuplicateCandidateRecord(
                    candidate_id=f"dup_{uuid.uuid4().hex[:10]}",
                    incident_id=current_incident_id,
                    other_incident_id=inc.incident_id,
                    distance_meters=round(dist, 1),
                    text_similarity=sim_score,
                    category_comparison=cat_comp,
                    rationale=rationale,
                    review_status="UNCONFIRMED",
                )
                duplicate_candidates.append(cand_record)

                if dist <= proximity_duplicate_threshold_m and cat_match and not is_duplicate:
                    is_duplicate = True
                    best_candidate_id = inc.incident_id
                    dup_conf = round(max(0.6, 1.0 - (dist / proximity_duplicate_threshold_m) * 0.4), 2)

    else:
        # Fallback to text similarity when coordinates are missing
        for inc in incidents:
            sim_score = compute_text_similarity(description_text, inc.description)
            norm_cat = category.lower().replace("_", "")
            inc_cat = inc.category.lower().replace("_", "")
            cat_match = norm_cat in inc_cat or inc_cat in norm_cat
            cat_comp = f"MATCH ({category} == {inc.category})" if cat_match else f"DIFFERENT ({category} != {inc.category})"

            if sim_score >= 0.35:
                nearby_ids.append(inc.incident_id)
                rationale = (
                    f"Coordinates missing. Text similarity {sim_score:.2f} against {inc.incident_id}. "
                    f"Category comparison: {cat_comp}."
                )
                cand_record = DuplicateCandidateRecord(
                    candidate_id=f"dup_{uuid.uuid4().hex[:10]}",
                    incident_id=current_incident_id,
                    other_incident_id=inc.incident_id,
                    distance_meters=None,
                    text_similarity=sim_score,
                    category_comparison=cat_comp,
                    rationale=rationale,
                    review_status="UNCONFIRMED",
                )
                duplicate_candidates.append(cand_record)

                if sim_score >= 0.55 and cat_match and not is_duplicate:
                    is_duplicate = True
                    best_candidate_id = inc.incident_id
                    dup_conf = round(sim_score, 2)

    geo_analysis = GeoAnalysis(
        nearby_incident_ids=nearby_ids,
        is_duplicate=is_duplicate,
        duplicate_of_id=best_candidate_id,
        distance_to_nearest_meters=round(min_dist, 1) if min_dist is not None else None,
        duplicate_confidence=dup_conf,
    )

    return geo_analysis, duplicate_candidates
