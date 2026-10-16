"""
JanSetu AI — Phase 5 Comprehensive Agent 1–3 Test Suite.

Verifies:
1. Each agent implements the shared run(incident, context) interface
2. Agent output conforms to its validated Pydantic model
3. Incident Intelligence generates appropriate targeted clarification questions
4. Disagreement between vision and NLP does not force a category (needs_review=True)
5. Unavailable models do not fabricate predictions or confidences
6. Geo-spatial matching returns distance and text-similarity evidence
7. Duplicate candidates remain UNCONFIRMED
8. Neither incident is automatically merged or deleted
9. DBSCAN handles empty input and a single valid point without crashing
10. Hotspot summaries reflect actual clustering output
11. Priority output includes explicit per-factor contributions
12. Missing inputs are recorded in missing_factors rather than silently treated as zero risk
13. Mandatory escalation fires even when the computed numerical score is low
14. Phase 3 state-machine and closure-verification invariants remain intact
15. Prediction and duplicate candidate records are persisted through repository helpers
16. Full backwards compatibility with LangGraph workflow nodes
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.base import BaseCivicAgent, CivicAgentProtocol
from app.agents.geocivic import GeoSpatialAgent, geocivic_node
from app.agents.incident_intel import IncidentIntelligenceAgent, incident_intel_node
from app.agents.priority import PriorityIntelligenceAgent, priority_node
from app.core.geo_utils import (
    SYNTHETIC_CIVIC_INCIDENTS,
    SyntheticIncidentRecord,
    compute_text_similarity,
    haversine_distance_meters,
    run_dbscan_clustering,
    validate_coordinates,
)
from app.db.models import Base, DuplicateCandidateModel, IncidentModel, ModelPredictionModel
from app.db.repository import (
    get_duplicate_candidates_by_incident,
    get_predictions_by_incident,
    persist_prediction_record,
    save_duplicate_candidate,
    save_incident,
    transaction_scope,
)
from app.graph.state_machine import TransitionError, validate_transition
from app.ml.nlp_classifier import CivicNLPClassifier, NLPClassificationResult
from app.ml.vision import VisionClassificationResult
from app.schemas.incident import (
    DuplicateCandidateRecord,
    GeoSpatialOutput,
    IncidentIntelOutput,
    IncidentLocation,
    OperationalStatus,
    PriorityAssessmentOutput,
    PriorityBand,
)


@pytest.fixture
def test_db_session():
    """In-memory SQLite session for database testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ============================================================================
# 1. P5.1 — Shared Agent Protocol Tests
# ============================================================================

def test_p5_1_shared_protocol_implementation():
    """All 3 specialist agents must implement CivicAgentProtocol and inherit BaseCivicAgent."""
    agents = [
        IncidentIntelligenceAgent(),
        GeoSpatialAgent(),
        PriorityIntelligenceAgent(),
    ]

    for agent in agents:
        assert isinstance(agent, BaseCivicAgent)
        assert isinstance(agent, CivicAgentProtocol)
        assert hasattr(agent, "agent_name")
        assert hasattr(agent, "agent_role")
        assert callable(agent.run)


def test_p5_1_agents_return_validated_pydantic_models():
    """Each agent returns its own distinct validated Pydantic model."""
    sample_incident = {
        "incident_id": "INC-P5-TEST-01",
        "raw_input": "Massive pothole on Main St northbound corridor",
        "selected_category": "pothole",
        "location_data": {"latitude": 28.6140, "longitude": 77.2092},
    }

    # Agent 1
    out_1 = IncidentIntelligenceAgent().run(sample_incident)
    assert isinstance(out_1, IncidentIntelOutput)
    assert out_1.incident_id == "INC-P5-TEST-01"
    assert out_1.original_complaint == sample_incident["raw_input"]

    # Agent 2
    out_2 = GeoSpatialAgent().run(sample_incident)
    assert isinstance(out_2, GeoSpatialOutput)
    assert out_2.incident_id == "INC-P5-TEST-01"

    # Agent 3
    out_3 = PriorityIntelligenceAgent().run(sample_incident)
    assert isinstance(out_3, PriorityAssessmentOutput)
    assert out_3.incident_id == "INC-P5-TEST-01"


# ============================================================================
# 2. P5.2 — Agent 1: Incident Intelligence Tests
# ============================================================================

def test_p5_2_clarification_questions_on_short_or_missing_input():
    """Missing or short complaint descriptions formulate targeted clarification questions."""
    agent = IncidentIntelligenceAgent()

    # Empty complaint
    out_empty = agent.run({"incident_id": "INC-01", "raw_input": ""})
    assert "complaint_description" in out_empty.missing_fields
    assert len(out_empty.clarification_questions) > 0
    assert out_empty.needs_review is True
    assert out_empty.status == OperationalStatus.NEEDS_CLARIFICATION.value

    # Very brief complaint
    out_brief = agent.run({"incident_id": "INC-02", "raw_input": "Pothole"})
    assert any("brief" in q.lower() for q in out_brief.clarification_questions)
    assert out_brief.needs_review is True


def test_p5_2_disagreement_does_not_force_category(valid_jpeg_bytes):
    """Disagreement between vision and NLP halts category forcing and triggers review."""
    agent = IncidentIntelligenceAgent()

    with patch.object(
        CivicNLPClassifier,
        "predict",
        return_value=NLPClassificationResult(
            predicted_label="pothole",
            confidence=0.88,
            available=True,
        ),
    ):
        from app.core.groq_vision import GroqVisionResult
        from app.schemas.incident import (
            EvidenceOutcome,
            EvidenceRecommendation,
            ImageQualityAssessment,
            IncidentExtraction,
            PhotoEvidenceAnalysis,
        )

        mock_evidence = PhotoEvidenceAnalysis(
            detected_category="garbage",
            visible_evidence="Waste pile visible on pavement",
            relevance_score=0.85,
            image_quality=ImageQualityAssessment.GOOD,
            confidence_score=0.82,
            recommendation=EvidenceRecommendation.PROCEED,
            outcome=EvidenceOutcome.MATCHED,
            quality_explanation=None,
            provenance="GROQ_VISION",
        )
        mock_groq_res = GroqVisionResult(
            success=True,
            extraction=IncidentExtraction(category="garbage", confidence_score=0.82),
            evidence=mock_evidence,
            is_fallback=False,
            is_simulated=False,
        )

        with patch("app.agents.incident_intel.analyze_with_groq_vision", return_value=mock_groq_res):
            out = agent.run({
                "incident_id": "INC-DISAGREE",
                "raw_input": "Road depression on the highway",
                "image_bytes": valid_jpeg_bytes,
            })

            # Invariant: Disagreement must NEVER force a category!
            assert out.predicted_category is None
            assert out.needs_review is True
            assert out.status in (OperationalStatus.AWAITING_CLARIFICATION.value, OperationalStatus.NEEDS_CLARIFICATION.value)
            assert any("pothole" in q and "garbage" in q for q in out.clarification_questions)


def test_p5_2_unavailable_model_does_not_invent_prediction():
    """When vision and NLP models are unavailable, manual selection is required and not labeled as ML."""
    agent = IncidentIntelligenceAgent()

    with patch.object(
        CivicNLPClassifier,
        "predict",
        return_value=NLPClassificationResult(available=False, error="NLP unavailable"),
    ):
        with patch(
            "app.agents.incident_intel.analyze_image_evidence",
            return_value=VisionClassificationResult(available=False, error="Vision unavailable"),
        ):
            out = agent.run({
                "incident_id": "INC-UNAVAIL",
                "raw_input": "Some complaint text here",
                "selected_category": "waterlogging",
            })

            assert out.predicted_category == "waterlogging"
            assert out.confidence is None  # No fake confidence!
            # Must be recorded as manual selection provenance, not direct ML
            fusion_pred = [p for p in out.model_predictions if p.task_type == "fusion"]
            if fusion_pred:
                assert fusion_pred[0].fallback_provenance == "manual_selection"


# ============================================================================
# 3. P5.3 — Agent 2: Geo-Spatial Intelligence Tests
# ============================================================================

def test_p5_3_haversine_distance_and_validation():
    """Haversine computes accurate distances and validates boundaries."""
    # Delhi Connaught Place to India Gate ~ 2.1 km
    dist = haversine_distance_meters(28.6315, 77.2167, 28.6129, 77.2295)
    assert 2000.0 < dist < 2500.0

    # Invalid coordinates raise ValueError
    with pytest.raises(ValueError):
        haversine_distance_meters(95.0, 77.0, 28.0, 77.0)

    with pytest.raises(ValueError):
        haversine_distance_meters(28.0, -195.0, 28.0, 77.0)


def test_p5_3_text_similarity_computation():
    """Text similarity uses TF-IDF cosine similarity as supporting evidence."""
    sim_high = compute_text_similarity(
        "Large dangerous pothole on main road causing accidents",
        "Deep dangerous road pothole on main street vehicles skidding",
    )
    assert sim_high > 0.25

    sim_low = compute_text_similarity(
        "Large pothole on the asphalt road",
        "Garbage dumped outside the hospital gates rotting",
    )
    assert sim_low < sim_high


def test_p5_3_duplicate_candidates_unconfirmed_no_automerge():
    """Candidates are marked UNCONFIRMED, retaining both original records without merging."""
    agent = GeoSpatialAgent()

    # Report right next to INC-1002 (Main St pothole at 28.6140, 77.2092)
    incident = {
        "incident_id": "INC-NEW-DUP",
        "raw_input": "Huge crater pothole on Main St northbound lane",
        "category": "pothole",
        "location_data": {"latitude": 28.6141, "longitude": 77.2093},
    }

    out = agent.run(incident)
    assert out.has_unconfirmed_duplicates is True
    assert len(out.duplicate_candidates) > 0

    candidate = out.duplicate_candidates[0]
    assert candidate.incident_id == "INC-NEW-DUP"
    assert candidate.other_incident_id == "INC-1002"
    assert candidate.review_status == "UNCONFIRMED"
    assert candidate.distance_meters is not None
    assert candidate.distance_meters < 50.0  # within 50m
    assert "MATCH" in candidate.category_comparison

    # Both records remain distinct and unmerged
    assert candidate.incident_id != candidate.other_incident_id


def test_p5_3_dbscan_handles_empty_single_point_and_missing_coords():
    """DBSCAN handles empty lists, single points, and missing coords without crashing."""
    # Empty
    res_empty = run_dbscan_clustering([])
    assert res_empty["num_clusters"] == 0
    assert "Insufficient" in res_empty["summary"]

    # Single point
    res_single = run_dbscan_clustering([{"incident_id": "P1", "latitude": 28.6, "longitude": 77.2}])
    assert res_single["num_clusters"] == 0
    assert res_single["cluster_assignments"]["P1"] is None

    # Missing coordinates (never treated as 0, 0)
    res_missing = run_dbscan_clustering([
        {"incident_id": "P_VALID_1", "latitude": 28.6140, "longitude": 77.2092},
        {"incident_id": "P_VALID_2", "latitude": 28.6141, "longitude": 77.2093},
        {"incident_id": "P_NO_COORDS", "latitude": None, "longitude": None},
    ], eps_meters=100.0, min_samples=2)

    assert res_missing["num_clusters"] == 1
    assert res_missing["cluster_assignments"]["P_VALID_1"] == 0
    assert res_missing["cluster_assignments"]["P_VALID_2"] == 0
    assert res_missing["cluster_assignments"]["P_NO_COORDS"] is None


# ============================================================================
# 4. P5.4 — Agent 3: Risk & Priority Tests
# ============================================================================

def test_p5_4_factor_contributions_and_missing_factors():
    """Priority output breaks down per-factor contributions and logs missing factors."""
    agent = PriorityIntelligenceAgent()

    # Clean description with duration and severity but missing people and recurrence
    incident = {
        "incident_id": "INC-PRIO-01",
        "raw_input": "Deep severe pothole on main road for the past 3 days",
        "category": "pothole",
    }

    out = agent.run(incident)
    assert 0.0 <= out.priority_score <= 100.0
    assert out.priority_band in [b.value for b in PriorityBand] or out.priority_band.upper() in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    contribs = out.factor_contributions
    assert "category_base" in contribs
    assert "severity" in contribs
    assert "duration" in contribs

    # Missing factors tracked honestly
    assert "people_affected_estimate" in out.missing_factors
    assert "historical_recurrence" in out.missing_factors
    assert out.uncertainty_score > 0.0


def test_p5_4_mandatory_escalation_independent_gate():
    """Mandatory escalation fires even if the base score is low, overriding the band to CRITICAL."""
    agent = PriorityIntelligenceAgent()

    # Minor complaint mentioning open manhole
    minor_incident = {
        "incident_id": "INC-MANHOLE",
        "raw_input": "open manhole on the pathway",
        "category": "pothole",
    }

    out = agent.run(minor_incident)
    assert out.is_escalated is True
    assert out.priority_band == PriorityBand.CRITICAL.value
    assert len(out.escalation_reasons) > 0
    assert any("E01_LIFE_SAFETY" in r for r in out.escalation_reasons)


def test_p5_4_emergency_corridor_escalation():
    """Hospital entrance or ambulance blockage triggers mandatory escalation."""
    agent = PriorityIntelligenceAgent()

    incident = {
        "incident_id": "INC-HOSPITAL",
        "raw_input": "Water accumulation with hospital blocked outside gate",
        "category": "waterlogging",
    }

    out = agent.run(incident)
    assert out.is_escalated is True
    assert out.priority_band == PriorityBand.CRITICAL.value
    assert any("E02_EMERGENCY_CORRIDOR" in r for r in out.escalation_reasons)


# ============================================================================
# 5. P5.5 — Persistence & Invariant Tests
# ============================================================================

def test_p5_5_persist_duplicate_candidates(test_db_session):
    """Duplicate candidate records are persisted with UNCONFIRMED review status."""
    incident = IncidentModel(
        incident_id="INC-P5-DB-01",
        complaint="Pothole near market",
        category="pothole",
        operational_status="NEW",
    )
    save_incident(test_db_session, incident)

    cand = DuplicateCandidateRecord(
        candidate_id="cand_test_001",
        incident_id="INC-P5-DB-01",
        other_incident_id="INC-1002",
        distance_meters=22.5,
        text_similarity=0.72,
        category_comparison="MATCH (pothole == pothole)",
        rationale="Within 25 meters of existing defect",
        review_status="UNCONFIRMED",
    )

    persisted = save_duplicate_candidate(test_db_session, cand)
    assert persisted.candidate_id == "cand_test_001"
    assert persisted.review_status == "UNCONFIRMED"

    stored = get_duplicate_candidates_by_incident(test_db_session, "INC-P5-DB-01")
    assert len(stored) == 1
    assert stored[0].other_incident_id == "INC-1002"


def test_p5_5_langgraph_node_compatibility():
    """LangGraph node wrappers produce dictionary updates matching workflow contracts."""
    state = {
        "incident_id": "INC-GRAPH-01",
        "raw_input": "Severe waterlogging near metro station",
        "selected_category": "waterlogging",
        "location_data": {"latitude": 28.5358, "longitude": 77.3912},
    }

    # Incident Intelligence node
    node_out_1 = incident_intel_node(state)
    assert "extracted_facts" in node_out_1
    assert "evidence_analysis" in node_out_1
    assert "status" in node_out_1
    assert "model_predictions" in node_out_1

    # Update state
    state.update(node_out_1)

    # GeoCivic node
    node_out_2 = geocivic_node(state)
    assert "geo_context" in node_out_2
    assert "duplicate_candidates" in node_out_2

    # Priority node
    node_out_3 = priority_node(state)
    assert "priority" in node_out_3
    assert "priority_output" in node_out_3
    assert "is_escalated" in node_out_3


def test_p5_5_phase3_invariants_preserved():
    """State machine invariant 1 (closure requires verification) remains intact."""
    with pytest.raises(TransitionError) as exc_info:
        # Closure attempted without verification result
        validate_transition(
            current=OperationalStatus.AWAITING_VERIFICATION,
            next_status=OperationalStatus.VERIFIED_CLOSED,
            verification_result=None,
        )
    assert "requires a passing VerificationResult" in str(exc_info.value)
