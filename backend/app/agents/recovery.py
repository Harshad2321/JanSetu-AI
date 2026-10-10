from app.schemas.incident import RevisedPlan
from app.graph.state import IncidentState
from app.core.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate

def recovery_node(state: IncidentState) -> dict:
    plan = state.get("current_plan")
    failure_reason = state.get("failure_reason", "Unknown failure")
    
    llm = get_llm().with_structured_output(RevisedPlan)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the Adaptive Recovery Agent. The previous intervention failed. Propose an alternative plan or escalate if no options exist."),
        ("user", "Previous Plan: {plan}\nFailure Reason: {failure_reason}")
    ])
    
    try:
        revised = chain.invoke({
            "plan": plan.model_dump() if plan else {},
            "failure_reason": failure_reason
        })
    except Exception as e:
        revised = RevisedPlan(
            new_steps=["Escalate to human review"],
            new_resources=[],
            escalation_required=True,
            reasoning="Fallback execution failed."
        )
        
    audit_event = {
        "timestamp": "now",
        "agent": "Adaptive Recovery",
        "action": "Proposed revised plan",
        "result": revised.reasoning
    }
    
    return {
        # Update current plan with the revised steps so critic can evaluate
        "current_plan": {
            "mitigation_steps": revised.new_steps,
            "permanent_repair_steps": plan.permanent_repair_steps if plan else [],
            "required_resources": revised.new_resources,
            "assigned_roles": plan.assigned_roles if plan else [],
            "closure_criteria": plan.closure_criteria if plan else []
        } if not revised.escalation_required else state.get("current_plan"),
        "status": "ESCALATED" if revised.escalation_required else "VALIDATING",
        "audit_timeline": [audit_event]
    }
