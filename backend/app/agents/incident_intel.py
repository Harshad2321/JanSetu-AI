from app.schemas.incident import IncidentExtraction
from app.graph.state import IncidentState
from app.core.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
import json

def incident_intel_node(state: IncidentState) -> dict:
    raw_input = state["raw_input"]
    llm = get_llm().with_structured_output(IncidentExtraction)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are the Incident Intelligence Agent for JanSetu AI. Extract facts from the civic complaint. Categories must be one of: 'pothole', 'waterlogging', 'garbage', 'other'."),
        ("user", "Complaint: {complaint}")
    ])
    
    chain = prompt | llm
    
    # In a real app we might want to catch parsing errors
    try:
        extraction = chain.invoke({"complaint": raw_input})
    except Exception as e:
        # Fallback if parsing fails or LLM is unavailable
        extraction = IncidentExtraction(
            category="other",
            severity_indicators=["Extraction failed"],
            missing_info=["All info missing due to error"],
            confidence_score=0.0
        )
    
    audit_event = {
        "timestamp": "now", # We'll fix timestamps later
        "agent": "Incident Intelligence",
        "action": "Extracted facts",
        "result": f"Category: {extraction.category}, Confidence: {extraction.confidence_score}"
    }
    
    return {
        "extracted_facts": extraction,
        "audit_timeline": [audit_event] # LangGraph will append this if we define the reducer
    }
