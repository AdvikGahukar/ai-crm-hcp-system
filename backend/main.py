import os
import json
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from dotenv import load_dotenv

import schemas
import models
from database import get_db, init_db, SessionLocal
from agent import run_langgraph_agent, db_search_hcp, MockAgent

load_dotenv()

app = FastAPI(title="AI-First CRM HCP Module", version="1.0.0")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development. In production, specify front-end domain.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event to initialize the database
@app.on_event("startup")
def on_startup():
    print("Initializing Database...")
    init_db()

# 1. HCP Endpoints
@app.get("/api/hcps", response_model=List[schemas.HCPSchema])
def get_hcps(query: Optional[str] = None, db: Session = Depends(get_db)):
    if query:
        return db.query(models.HCP).filter(models.HCP.name.ilike(f"%{query}%")).all()
    return db.query(models.HCP).all()

@app.post("/api/hcps", response_model=schemas.HCPSchema)
def create_hcp(hcp: schemas.HCPCreate, db: Session = Depends(get_db)):
    db_hcp = models.HCP(**hcp.model_dump())
    db.add(db_hcp)
    db.commit()
    db.refresh(db_hcp)
    return db_hcp

# 2. Materials & Samples Endpoints
@app.get("/api/materials", response_model=List[schemas.MaterialSchema])
def get_materials(db: Session = Depends(get_db)):
    return db.query(models.Material).all()

@app.get("/api/samples", response_model=List[schemas.SampleSchema])
def get_samples(db: Session = Depends(get_db)):
    return db.query(models.Sample).all()

# 3. Interaction Endpoints
@app.get("/api/interactions", response_model=List[schemas.InteractionSchema])
def get_interactions(db: Session = Depends(get_db)):
    # Returns all interactions, ordered by latest
    # In SQLite, we can join with materials, samples, tasks
    interactions = db.query(models.Interaction).order_by(models.Interaction.id.desc()).all()
    
    # We construct the response matching the schemas manually if relationship loading is lazy
    result = []
    for i in interactions:
        result.append({
            "id": i.id,
            "hcp_id": i.hcp_id,
            "type": i.type,
            "date": i.date,
            "time": i.time,
            "attendees": i.attendees,
            "topics_discussed": i.topics_discussed,
            "sentiment": i.sentiment,
            "outcomes": i.outcomes,
            "follow_up_actions": i.follow_up_actions,
            "materials": i.materials,
            "samples": i.samples,
            "tasks": i.tasks
        })
    return result

@app.post("/api/interactions", response_model=schemas.InteractionSchema)
def create_interaction(interaction_in: schemas.InteractionCreate, db: Session = Depends(get_db)):
    try:
        # Check HCP
        hcp = db.query(models.HCP).filter(models.HCP.id == interaction_in.hcp_id).first()
        if not hcp:
            raise HTTPException(status_code=400, detail="HCP not found")
            
        db_interaction = models.Interaction(
            hcp_id=interaction_in.hcp_id,
            type=interaction_in.type,
            date=interaction_in.date,
            time=interaction_in.time,
            attendees=interaction_in.attendees or f"{hcp.name}, Sales Rep Alex",
            topics_discussed=interaction_in.topics_discussed,
            sentiment=interaction_in.sentiment,
            outcomes=interaction_in.outcomes,
            follow_up_actions=interaction_in.follow_up_actions
        )
        
        # Link materials
        if interaction_in.materials_shared:
            for m_id in interaction_in.materials_shared:
                material = db.query(models.Material).filter(models.Material.id == m_id).first()
                if material:
                    db_interaction.materials.append(material)
                    
        # Link samples and deduct stock
        if interaction_in.samples_distributed:
            for s_id in interaction_in.samples_distributed:
                sample = db.query(models.Sample).filter(models.Sample.id == s_id).first()
                if sample:
                    db_interaction.samples.append(sample)
                    if sample.stock_quantity > 0:
                        sample.stock_quantity -= 1
                        
        db.add(db_interaction)
        db.commit()
        db.refresh(db_interaction)
        
        # Auto-create follow-up task if follow-up action is specified
        if interaction_in.follow_up_actions:
            db_task = models.FollowUpTask(
                hcp_id=interaction_in.hcp_id,
                interaction_id=db_interaction.id,
                description=interaction_in.follow_up_actions,
                due_date=interaction_in.date, # default
                status="Pending"
            )
            db.add(db_task)
            db.commit()
            
        # Re-fetch with relationships
        db.refresh(db_interaction)
        return db_interaction
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to log interaction: {str(e)}")

@app.put("/api/interactions/{interaction_id}")
def update_interaction(interaction_id: int, updates: dict, db: Session = Depends(get_db)):
    interaction = db.query(models.Interaction).filter(models.Interaction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
        
    allowed_fields = ["type", "date", "time", "attendees", "topics_discussed", "sentiment", "outcomes", "follow_up_actions"]
    for key, value in updates.items():
        if key in allowed_fields:
            setattr(interaction, key, value)
            
    # Handle materials update
    if "materials_shared" in updates:
        interaction.materials = []
        for mat_id in updates["materials_shared"]:
            mat = db.query(models.Material).filter(models.Material.id == mat_id).first()
            if mat:
                interaction.materials.append(mat)
                
    # Handle samples update
    if "samples_distributed" in updates:
        interaction.samples = []
        for samp_id in updates["samples_distributed"]:
            samp = db.query(models.Sample).filter(models.Sample.id == samp_id).first()
            if samp:
                interaction.samples.append(samp)
                
    db.commit()
    db.refresh(interaction)
    
    # Return updated state
    return {
        "status": "success",
        "interaction": {
            "id": interaction.id,
            "hcp_id": interaction.hcp_id,
            "type": interaction.type,
            "date": interaction.date,
            "time": interaction.time,
            "attendees": interaction.attendees,
            "topics_discussed": interaction.topics_discussed,
            "sentiment": interaction.sentiment,
            "outcomes": interaction.outcomes,
            "follow_up_actions": interaction.follow_up_actions,
            "materials_shared": [m.id for m in interaction.materials],
            "samples_distributed": [s.id for s in interaction.samples]
        }
    }

# 4. Chat/AI Agent Endpoints
@app.post("/api/chat", response_model=schemas.ChatResponse)
def chat_endpoint(req: schemas.ChatRequest):
    try:
        result = run_langgraph_agent(
            message=req.message,
            current_form_state=req.current_form_state,
            session_id=req.session_id
        )
        return schemas.ChatResponse(
            response=result["response"],
            form_state=result["form_state"],
            logs=result["logs"],
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution error: {str(e)}")

# 5. Voice Dictation Summarization Endpoint
@app.post("/api/voice-summarize", response_model=schemas.VoiceNoteResponse)
def voice_summarize_endpoint(req: schemas.VoiceNoteRequest):
    # Simulated voice notes transcription summary logic
    text = req.audio_text
    api_key = os.getenv("GROQ_API_KEY")
    
    # Defaults
    extracted = {
        "hcp_name": "",
        "type": "Meeting",
        "sentiment": "Neutral",
        "topics_discussed": "",
        "outcomes": "",
        "follow_up_actions": ""
    }
    
    if api_key:
        try:
            from langchain_groq import ChatGroq
            from langchain_core.messages import HumanMessage, SystemMessage
            
            llm = ChatGroq(groq_api_key=api_key, model_name="llama-3.3-70b-versatile", temperature=0.1)
            sys_prompt = (
                "You are an assistant that summarizes medical field representative voice notes. "
                "Extract clinical information and return a JSON block with these keys: "
                "hcp_name, type (Meeting/Call/Email/Video Conference), sentiment (Positive/Neutral/Negative), "
                "topics_discussed, outcomes, follow_up_actions.\n"
                "Return ONLY a JSON object."
            )
            response = llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=text)])
            # Parse JSON from response
            import re
            json_blocks = re.findall(r"({.*?})", response.content, re.DOTALL)
            if json_blocks:
                extracted.update(json.loads(json_blocks[0]))
        except Exception as e:
            print(f"Error in LLM Voice Summary: {e}")
            
    if not extracted["hcp_name"]:
        # Mock parsing fallback
        text_lower = text.lower()
        if "sarah" in text_lower or "patel" in text_lower:
            extracted["hcp_name"] = "Dr. Sarah Patel"
        elif "robert" in text_lower or "chen" in text_lower:
            extracted["hcp_name"] = "Dr. Robert Chen"
        elif "amanda" in text_lower or "ross" in text_lower:
            extracted["hcp_name"] = "Dr. Amanda Ross"
        elif "jane" in text_lower or "smith" in text_lower:
            extracted["hcp_name"] = "Dr. Jane Smith"
            
        if "positive" in text_lower:
            extracted["sentiment"] = "Positive"
        elif "negative" in text_lower:
            extracted["sentiment"] = "Negative"
            
        if "call" in text_lower:
            extracted["type"] = "Call"
        elif "email" in text_lower:
            extracted["type"] = "Email"
            
        # Extract some content
        extracted["topics_discussed"] = text
        
    summary = f"Voice note summarized. Extracted details for {extracted['hcp_name'] or 'unknown HCP'}."
    return schemas.VoiceNoteResponse(summary=summary, extracted_fields=extracted)

# 6. Tasks Endpoint
@app.get("/api/tasks", response_model=List[schemas.FollowUpTaskSchema])
def get_tasks(db: Session = Depends(get_db)):
    return db.query(models.FollowUpTask).all()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
