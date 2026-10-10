from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import uuid
from app.graph.orchestrator import graph

app = FastAPI(title="JanSetu AI API", description="Adaptive Civic Incident Resolution")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IncidentRequest(BaseModel):
    complaint: str
    failure_reason: str | None = None

@app.post("/api/incidents")
async def process_incident(req: IncidentRequest):
    # Initialize state
    state = {
        "incident_id": f"INC-{str(uuid.uuid4())[:8]}",
        "raw_input": req.complaint,
        "status": "NEW",
        "retry_count": 0,
        "audit_timeline": [],
        "failure_reason": req.failure_reason
    }
    
    # Run graph
    result = graph.invoke(state)
    return result

@app.get("/")
def health_check():
    return {"status": "ok", "message": "JanSetu AI API is running"}
