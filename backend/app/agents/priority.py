from app.schemas.incident import PriorityAssessment
from app.graph.state import IncidentState
from app.core.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate

def priority_node(state: IncidentState) -> dict:
    raw_input = state.get("raw_input", "")
    facts = state.get("extracted_facts")
    
    # We want a deterministic component plus LLM explanation
    llm = get_llm().with_structured_output(PriorityAssessment)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the Priority Intelligence Agent for JanSetu AI. Determine the priority score (0-100) and band (Low, Medium, High, Critical) based on severity and public exposure. Explain your reasoning."),
        ("user", "Complaint: {complaint}\nExtracted Facts: {facts}")
    ])
    
    chain = prompt | llm
    
    try:
        assessment = chain.invoke({
            "complaint": raw_input,
            "facts": facts.model_dump() if facts else {}
        })
    except Exception as e:
        assessment = PriorityAssessment(
            priority_score=50,
            priority_band="Medium",
            explanation="Failed to assess priority, defaulting to Medium."
        )
        
    audit_event = {
        "timestamp": "now",
        "agent": "Priority Intelligence",
        "action": "Calculated priority",
        "result": f"Band: {assessment.priority_band}, Score: {assessment.priority_score}"
    }
    
    return {
        "priority": assessment,
        "audit_timeline": [audit_event]
    }
