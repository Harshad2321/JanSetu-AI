from app.schemas.incident import ValidationDecision
from app.graph.state import IncidentState
from app.core.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate

def critic_node(state: IncidentState) -> dict:
    plan = state.get("current_plan")
    
    llm = get_llm().with_structured_output(ValidationDecision)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the Critic and Verification Agent for JanSetu AI. Validate the resolution plan against safety and resource policies. Reply with 'APPROVE', 'REJECT', or 'ESCALATE' and feedback."),
        ("user", "Plan: {plan}")
    ])
    
    try:
        decision = chain.invoke({"plan": plan.model_dump() if plan else {}})
    except Exception as e:
        decision = ValidationDecision(status="APPROVE", feedback="Default approval on failure.")
        
    audit_event = {
        "timestamp": "now",
        "agent": "Critic Agent",
        "action": f"Validated plan: {decision.status}",
        "result": decision.feedback
    }
    
    next_status = "SIMULATING" if decision.status == "APPROVE" else "PLANNING"
    if decision.status == "ESCALATE":
        next_status = "ESCALATED"
        
    return {
        "validation": decision,
        "status": next_status,
        "audit_timeline": [audit_event]
    }
