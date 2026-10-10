from app.schemas.incident import GeoAnalysis
from app.graph.state import IncidentState
import random

def geocivic_node(state: IncidentState) -> dict:
    facts = state.get("extracted_facts")
    
    # Mocking geospatial lookup based on the extracted text
    # In a real app this would query PostGIS or similar
    
    is_duplicate = False
    duplicate_of_id = None
    nearby = []
    
    # Deterministic mock rule for demonstration
    if facts and "Main St" in state.get("raw_input", ""):
        is_duplicate = True
        duplicate_of_id = "INC-1002"
        nearby = ["INC-1002", "INC-0998"]
    else:
        # Just return some random nearby stuff
        nearby = [f"INC-{random.randint(1000, 9999)}" for _ in range(2)]
        
    analysis = GeoAnalysis(
        nearby_incident_ids=nearby,
        is_duplicate=is_duplicate,
        duplicate_of_id=duplicate_of_id
    )
    
    audit_event = {
        "timestamp": "now",
        "agent": "GeoCivic Agent",
        "action": "Geospatial duplicate check",
        "result": f"Duplicate: {is_duplicate}" + (f" of {duplicate_of_id}" if is_duplicate else "")
    }
    
    return {
        "geo_context": analysis,
        "audit_timeline": [audit_event]
    }
