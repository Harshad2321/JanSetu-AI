from langgraph.graph import StateGraph, START, END
from app.graph.state import IncidentState
from app.agents.incident_intel import incident_intel_node
from app.agents.geocivic import geocivic_node
from app.agents.priority import priority_node
from app.agents.resolution import resolution_planning_node
from app.agents.critic import critic_node
from app.agents.recovery import recovery_node

def route_from_critic(state: IncidentState):
    status = state.get("status")
    if status == "SIMULATING":
        return "simulate"
    elif status == "PLANNING":
        return "resolution_planning"
    else:
        return END

def simulate_intervention(state: IncidentState):
    # Mock simulation
    # If the user injected a failure via lab, we use it. Otherwise, assume success.
    failure_reason = state.get("failure_reason")
    
    if failure_reason:
        audit_event = {
            "timestamp": "now",
            "agent": "Simulation Lab",
            "action": "Intervention failed",
            "result": failure_reason
        }
        return {
            "simulation_result": "FAILURE",
            "status": "RECOVERING",
            "audit_timeline": [audit_event]
        }
    else:
        audit_event = {
            "timestamp": "now",
            "agent": "Simulation Lab",
            "action": "Intervention succeeded",
            "result": "Resolved"
        }
        return {
            "simulation_result": "SUCCESS",
            "status": "RESOLVED",
            "audit_timeline": [audit_event]
        }

def route_from_simulation(state: IncidentState):
    if state.get("status") == "RECOVERING":
        return "adaptive_recovery"
    return END

def build_graph():
    builder = StateGraph(IncidentState)
    
    # Add nodes
    builder.add_node("incident_intel", incident_intel_node)
    builder.add_node("geocivic", geocivic_node)
    builder.add_node("priority_intel", priority_node)
    builder.add_node("resolution_planning", resolution_planning_node)
    builder.add_node("critic", critic_node)
    builder.add_node("simulate", simulate_intervention)
    builder.add_node("adaptive_recovery", recovery_node)
    
    # Edges
    builder.add_edge(START, "incident_intel")
    
    # Parallel execution
    builder.add_edge("incident_intel", "geocivic")
    builder.add_edge("incident_intel", "priority_intel")
    
    # We need a merge node or direct edges to planning
    # LangGraph waits for all incoming edges to complete automatically in newer versions if configured,
    # or we just connect both to resolution_planning.
    builder.add_edge("geocivic", "resolution_planning")
    builder.add_edge("priority_intel", "resolution_planning")
    
    builder.add_edge("resolution_planning", "critic")
    
    builder.add_conditional_edges("critic", route_from_critic, {
        "simulate": "simulate",
        "resolution_planning": "resolution_planning",
        END: END
    })
    
    builder.add_conditional_edges("simulate", route_from_simulation, {
        "adaptive_recovery": "adaptive_recovery",
        END: END
    })
    
    builder.add_edge("adaptive_recovery", "critic")
    
    return builder.compile()

graph = build_graph()
