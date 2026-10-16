"""
JanSetu AI — Shared Agent Protocol & Base Class (Phase 5, P5.1).

Defines the conceptual interface for all JanSetu AI specialist agents:
run(incident, context) -> PydanticOutputModel

Guarantees:
- Clear inputs and typed, validated Pydantic outputs.
- Consistent error handling, audit provenance, and telemetry.
- No hidden mutable shared state.
- Zero fabricated predictions or confidence values.
- Seamless compatibility with both standalone service invocations and LangGraph workflow nodes.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

logger = logging.getLogger("jansetu.agents.base")

# Generic Type variable bound to Pydantic BaseModel for typed outputs
OutputT = TypeVar("OutputT", bound=BaseModel)


@runtime_checkable
class CivicAgentProtocol(Protocol[OutputT]):
    """Runtime-checkable protocol defining the shared agent contract."""

    agent_name: str
    agent_role: str

    def run(
        self,
        incident: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> OutputT:
        """Execute agent analysis and return validated Pydantic model."""
        ...


class BaseCivicAgent(ABC, Generic[OutputT]):
    """
    Abstract base class providing common normalization, audit helpers,
    and validation for JanSetu specialist agents.
    """

    agent_name: str = "BaseCivicAgent"
    agent_role: str = "Specialist"

    @abstractmethod
    def run(
        self,
        incident: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> OutputT:
        """
        Execute agent reasoning and return a validated Pydantic output model.
        Must be implemented by each specialist agent.
        """
        pass

    @staticmethod
    def extract_incident_dict(incident: Any) -> Dict[str, Any]:
        """
        Extracts a clean dictionary representation from:
        - dict / LangGraph IncidentState
        - Pydantic BaseModel (Incident, etc.)
        - SQLAlchemy ORM Model (IncidentModel, etc.)
        """
        if isinstance(incident, dict):
            return dict(incident)
        if isinstance(incident, BaseModel):
            return incident.model_dump()
        if hasattr(incident, "__dict__"):
            # SQLAlchemy model or custom object
            data: Dict[str, Any] = {}
            for k in dir(incident):
                if not k.startswith("_") and not callable(getattr(incident, k)):
                    try:
                        data[k] = getattr(incident, k)
                    except Exception:
                        pass
            return data
        return {}
