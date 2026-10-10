from app.schemas.incident import ResolutionPlan
from app.graph.state import IncidentState
from app.core.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate

def resolution_planning_node(state: IncidentState) -> dict:
    facts = state.get("extracted_facts")
    geo = state.get("geo_context")
    priority = state.get("priority")
    
    llm = get_llm().with_structured_output(ResolutionPlan)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the Resolution Planning Agent for JanSetu AI. Create mitigation and permanent repair plans, required resources, roles, and closure criteria."),
        ("user", "Incident Facts: {facts}\nGeo Context: {geo}\nPriority: {priority}")
    ])
    
    chain = prompt | llm
    
    try:
        plan = chain.invoke({
            "facts": facts.model_dump() if facts else {},
            "geo": geo.model_dump() if geo else {},
            "priority": priority.model_dump() if priority else {}
        })
    except Exception as e:
        plan = ResolutionPlan(
            mitigation_steps=["Fallback mitigation"],
            permanent_repair_steps=["Fallback repair"],
            required_resources=["Standard crew"],
            assigned_roles=["Responder"],
            closure_criteria=["Work complete"]
        )
        
    audit_event = {
        "timestamp": "now",
        "agent": "Resolution Planning",
        "action": "Created resolution plan",
        "result": f"Assigned roles: {', '.join(plan.assigned_roles)}"
    }
    
    return {
        "current_plan": plan,
        "status": "VALIDATING",
        "audit_timeline": [audit_event]
    }
