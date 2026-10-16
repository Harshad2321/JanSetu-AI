"""
JanSetu AI — Dedicated Deterministic Execution Simulator (Phase 6, P6.2).

Responsible for:
- Simulating physical intervention attempts under explicit, deterministic scenarios
- Supporting tracker-defined failure modes:
  * SUCCESS
  * CREW_UNAVAILABLE
  * MATERIAL_UNAVAILABLE
  * WEATHER_BLOCK
  * RELIEF_EXPIRED
  * COMPLETE_MISSING_EVIDENCE
- Providing a synthetic resource registry for Adaptive Recovery alternatives
- Emitting validated ExecutionAttempt models marked strictly with simulated=True
- Enforcing that a simulation never contacts real citizens or performs real municipal repairs
"""

from __future__ import annotations

import logging
import random
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.incident import (
    ClosureEvidence,
    ExecutionAttempt,
    PlanType,
    ResponsePlan,
)

logger = logging.getLogger("jansetu.simulator")


class SimulationScenario(str, Enum):
    """Tracker-defined simulation scenarios for academic demonstration."""
    SUCCESS = "SUCCESS"
    CREW_UNAVAILABLE = "CREW_UNAVAILABLE"
    MATERIAL_UNAVAILABLE = "MATERIAL_UNAVAILABLE"
    WEATHER_BLOCK = "WEATHER_BLOCK"
    RELIEF_EXPIRED = "RELIEF_EXPIRED"
    COMPLETE_MISSING_EVIDENCE = "COMPLETE_MISSING_EVIDENCE"


class SyntheticResource(BaseModel):
    """Synthetic municipal resource or contractor asset available in the simulation."""
    model_config = ConfigDict(use_enum_values=True)

    resource_id: str = Field(description="Unique resource identifier")
    name: str = Field(description="Human-readable resource name")
    resource_type: str = Field(description="crew, material, equipment, contractor")
    category_affinity: List[str] = Field(default_factory=lambda: ["all"], description="pothole, waterlogging, garbage, all")
    available: bool = Field(default=True, description="Current availability in inventory or shift")
    safety_certified: bool = Field(default=True, description="Meets municipal labor & engineering safety guidelines")
    authorized: bool = Field(default=True, description="Authorized under municipal vendor contract")
    cost_estimate: float = Field(default=0.0, ge=0.0, description="Estimated mobilization or material cost")
    lead_time_hours: float = Field(default=1.0, ge=0.0, description="Lead time in hours")
    weather_safe: bool = Field(default=True, description="True if certified for deployment in monsoon/rain")
    description: str = Field(default="", description="Capability and constraint details")


# ============================================================================
# Synthetic Resource Registry
# ============================================================================

SYNTHETIC_RESOURCES: Dict[str, SyntheticResource] = {
    "res_crew_municipal_primary": SyntheticResource(
        resource_id="res_crew_municipal_primary",
        name="Primary Municipal Road Maintenance Crew",
        resource_type="crew",
        category_affinity=["pothole", "all"],
        available=True,
        safety_certified=True,
        authorized=True,
        cost_estimate=5000.0,
        lead_time_hours=2.0,
        weather_safe=False,
        description="Standard municipal road gang for asphalt compaction and surface patching.",
    ),
    "res_crew_contractor_standby": SyntheticResource(
        resource_id="res_crew_contractor_standby",
        name="Emergency Standby Contractor Paving Team",
        resource_type="crew",
        category_affinity=["pothole", "all"],
        available=True,
        safety_certified=True,
        authorized=True,
        cost_estimate=12000.0,
        lead_time_hours=1.0,
        weather_safe=True,
        description="Certified on-call contractor team with rapid-deployment hydraulic equipment.",
    ),
    "res_crew_uncertified_labor": SyntheticResource(
        resource_id="res_crew_uncertified_labor",
        name="Uncertified Casual Day Labor Gang",
        resource_type="crew",
        category_affinity=["all"],
        available=True,
        safety_certified=False,  # Unsafe -> Must be rejected by Recovery Agent
        authorized=False,
        cost_estimate=1500.0,
        lead_time_hours=0.5,
        weather_safe=False,
        description="Unvetted casual laborers without safety helmets or traffic protection training.",
    ),
    "res_crew_unauthorized_private": SyntheticResource(
        resource_id="res_crew_unauthorized_private",
        name="Unauthorized Private Fleet Subcontractor",
        resource_type="crew",
        category_affinity=["all"],
        available=True,
        safety_certified=True,
        authorized=False,  # Unauthorized -> Must be rejected by Recovery Agent
        cost_estimate=7500.0,
        lead_time_hours=1.5,
        weather_safe=True,
        description="Private operator lacking an active municipal public-works procurement agreement.",
    ),
    "res_mat_hot_mix_asphalt": SyntheticResource(
        resource_id="res_mat_hot_mix_asphalt",
        name="Hot-Mix Asphalt Batch (500kg)",
        resource_type="material",
        category_affinity=["pothole"],
        available=True,
        safety_certified=True,
        authorized=True,
        cost_estimate=4500.0,
        lead_time_hours=3.0,
        weather_safe=False,  # Incompatible with monsoon rain
        description="High-temperature asphalt requiring dry surface and roller compaction.",
    ),
    "res_mat_cold_mix_polymer": SyntheticResource(
        resource_id="res_mat_cold_mix_polymer",
        name="High-Performance Cold-Mix Polymer Asphalt (400kg)",
        resource_type="material",
        category_affinity=["pothole"],
        available=True,
        safety_certified=True,
        authorized=True,
        cost_estimate=6500.0,
        lead_time_hours=0.5,
        weather_safe=True,  # Weather-safe alternative
        description="Pre-mixed polymer additive asphalt that cures rapidly even in damp conditions.",
    ),
    "res_mat_steel_trench_plate": SyntheticResource(
        resource_id="res_mat_steel_trench_plate",
        name="Heavy Structural Steel Road Plates (20mm)",
        resource_type="material",
        category_affinity=["pothole"],
        available=True,
        safety_certified=True,
        authorized=True,
        cost_estimate=3500.0,
        lead_time_hours=1.0,
        weather_safe=True,
        description="Interlocking heavy-gauge skid-resistant steel plates to bridge roadway cavities.",
    ),
    "res_mat_substandard_rubble": SyntheticResource(
        resource_id="res_mat_substandard_rubble",
        name="Uncompacted Construction Debris & Rubble Fill",
        resource_type="material",
        category_affinity=["pothole"],
        available=True,
        safety_certified=False,  # Unsafe -> Must be rejected by Recovery Agent
        authorized=False,
        cost_estimate=500.0,
        lead_time_hours=0.5,
        weather_safe=False,
        description="Demolition waste and dirt lacking compaction testing; prone to immediate washout.",
    ),
    "res_equip_suction_tanker_municipal": SyntheticResource(
        resource_id="res_equip_suction_tanker_municipal",
        name="Municipal Suction Pump Truck (5000L)",
        resource_type="equipment",
        category_affinity=["waterlogging"],
        available=True,
        safety_certified=True,
        authorized=True,
        cost_estimate=6000.0,
        lead_time_hours=2.0,
        weather_safe=True,
        description="Vacuum tanker for clearing standing rainwater from blocked arterial culverts.",
    ),
    "res_equip_high_capacity_submersible": SyntheticResource(
        resource_id="res_equip_high_capacity_submersible",
        name="Emergency High-Flow Submersible Pump Array",
        resource_type="equipment",
        category_affinity=["waterlogging"],
        available=True,
        safety_certified=True,
        authorized=True,
        cost_estimate=8500.0,
        lead_time_hours=1.0,
        weather_safe=True,
        description="Heavy-duty continuous electric trash pumps with auxiliary diesel generator.",
    ),
    "res_equip_compactor_municipal": SyntheticResource(
        resource_id="res_equip_compactor_municipal",
        name="Municipal Solid Waste Compactor Truck",
        resource_type="equipment",
        category_affinity=["garbage"],
        available=True,
        safety_certified=True,
        authorized=True,
        cost_estimate=4000.0,
        lead_time_hours=2.5,
        weather_safe=True,
        description="Standard hydraulic compactor vehicle for domestic and municipal waste clearing.",
    ),
    "res_equip_tipper_truck_contractor": SyntheticResource(
        resource_id="res_equip_tipper_truck_contractor",
        name="Contractor Heavy Tipper Truck & Loader",
        resource_type="equipment",
        category_affinity=["garbage"],
        available=True,
        safety_certified=True,
        authorized=True,
        cost_estimate=9500.0,
        lead_time_hours=1.0,
        weather_safe=True,
        description="High-volume open-bed tipper truck with front-end mechanical loader.",
    ),
    "res_relief_steel_barricade": SyntheticResource(
        resource_id="res_relief_steel_barricade",
        name="Reinforced Steel Traffic Barricade Kit with Solar Beacons",
        resource_type="equipment",
        category_affinity=["all"],
        available=True,
        safety_certified=True,
        authorized=True,
        cost_estimate=2200.0,
        lead_time_hours=0.5,
        weather_safe=True,
        description="Heavy-duty weather-resistant physical barricades to isolate civic defects.",
    ),
}


class ExecutionSimulator:
    """
    Dedicated deterministic execution simulator.
    Simulates field intervention outcomes without real-world municipal interaction.
    """

    def __init__(self, resource_registry: Optional[Dict[str, SyntheticResource]] = None):
        self.resources = dict(resource_registry or SYNTHETIC_RESOURCES)

    def simulate_execution(
        self,
        plan: Any,
        scenario: Union[str, SimulationScenario] = SimulationScenario.SUCCESS,
        seed: int = 42,
        incident_id: Optional[str] = None,
    ) -> ExecutionAttempt:
        """
        Executes a deterministic simulated intervention attempt based on explicit scenario.
        
        Guarantees:
        - simulated=True on every returned ExecutionAttempt.
        - Deterministic outcome for given seed and scenario.
        - FAILED outcomes are never converted to SUCCESS.
        - Does not contact real citizens, dispatch real crews, or close tickets.
        """
        if isinstance(scenario, SimulationScenario):
            scen_val = scenario.value
        else:
            scen_val = str(scenario).upper().strip()

        # Deterministic random generator keyed by seed
        rng = random.Random(seed)

        # Plan ID extraction
        if isinstance(plan, dict):
            plan_id = plan.get("plan_id") or f"plan_synth_{rng.randint(1000, 9999)}"
            inc_id = incident_id or plan.get("incident_id") or "INC-SIM"
            plan_type = plan.get("plan_type", "PERMANENT_RESOLUTION")
            criteria = plan.get("closure_criteria") or []
        elif hasattr(plan, "plan_id"):
            plan_id = plan.plan_id
            inc_id = incident_id or getattr(plan, "incident_id", None) or "INC-SIM"
            plan_type = getattr(plan, "plan_type", "PERMANENT_RESOLUTION")
            criteria = getattr(plan, "closure_criteria", []) or []
        else:
            plan_id = f"plan_synth_{rng.randint(1000, 9999)}"
            inc_id = incident_id or "INC-SIM"
            plan_type = "PERMANENT_RESOLUTION"
            criteria = []

        attempt_id = f"att_{inc_id}_{scen_val.lower()}_{seed}_{rng.randint(100, 999)}"
        attempted_time = datetime.now(timezone.utc)

        if scen_val == SimulationScenario.SUCCESS.value:
            return ExecutionAttempt(
                attempt_id=attempt_id,
                incident_id=inc_id,
                plan_id=plan_id,
                resource="Primary Municipal Field Operations Crew",
                outcome="SUCCESS",
                failure_reason=None,
                evidence_reference=f"evid_verified_completion_{inc_id}_{seed}",
                simulated=True,
                attempted_at=attempted_time,
            )

        elif scen_val == SimulationScenario.CREW_UNAVAILABLE.value:
            return ExecutionAttempt(
                attempt_id=attempt_id,
                incident_id=inc_id,
                plan_id=plan_id,
                resource="Primary Municipal Road Maintenance Crew",
                outcome="FAILED",
                failure_reason="Primary municipal crew unavailable: staffing deficit or emergency reassignment",
                evidence_reference=None,
                simulated=True,
                attempted_at=attempted_time,
            )

        elif scen_val == SimulationScenario.MATERIAL_UNAVAILABLE.value:
            return ExecutionAttempt(
                attempt_id=attempt_id,
                incident_id=inc_id,
                plan_id=plan_id,
                resource="Hot-Mix Asphalt Batch (500kg)",
                outcome="FAILED",
                failure_reason="Specified material unavailable: hot-mix asphalt batch deficit / plant shutdown",
                evidence_reference=None,
                simulated=True,
                attempted_at=attempted_time,
            )

        elif scen_val == SimulationScenario.WEATHER_BLOCK.value:
            return ExecutionAttempt(
                attempt_id=attempt_id,
                incident_id=inc_id,
                plan_id=plan_id,
                resource="Road Maintenance Division",
                outcome="FAILED",
                failure_reason="Adverse weather block: monsoon rainfall exceeds safe application threshold (>25mm/hr)",
                evidence_reference=None,
                simulated=True,
                attempted_at=attempted_time,
            )

        elif scen_val == SimulationScenario.RELIEF_EXPIRED.value:
            return ExecutionAttempt(
                attempt_id=attempt_id,
                incident_id=inc_id,
                plan_id=plan_id,
                resource="Temporary Relief Safety Perimeter",
                outcome="FAILED",
                failure_reason="Temporary relief expired: safety barricades damaged by heavy traffic before permanent repair commenced",
                evidence_reference=None,
                simulated=True,
                attempted_at=attempted_time,
            )

        elif scen_val == SimulationScenario.COMPLETE_MISSING_EVIDENCE.value:
            # Field work simulated, but mandatory evidence omitted
            return ExecutionAttempt(
                attempt_id=attempt_id,
                incident_id=inc_id,
                plan_id=plan_id,
                resource="Municipal Operations Unit",
                outcome="SUCCESS",
                failure_reason="Intervention completed but mandatory photographic completion evidence was not captured",
                evidence_reference=None,
                simulated=True,
                attempted_at=attempted_time,
            )

        else:
            # Custom or generic failure injection
            return ExecutionAttempt(
                attempt_id=attempt_id,
                incident_id=inc_id,
                plan_id=plan_id,
                resource="Municipal Intervention Team",
                outcome="FAILED",
                failure_reason=f"Intervention halted due to obstacle: {scen_val}",
                evidence_reference=None,
                simulated=True,
                attempted_at=attempted_time,
            )


_SIMULATOR_INSTANCE: Optional[ExecutionSimulator] = None


def get_simulator() -> ExecutionSimulator:
    """Return shared deterministic execution simulator instance."""
    global _SIMULATOR_INSTANCE
    if _SIMULATOR_INSTANCE is None:
        _SIMULATOR_INSTANCE = ExecutionSimulator()
    return _SIMULATOR_INSTANCE
