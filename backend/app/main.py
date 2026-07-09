import datetime
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.database import engine, Base, get_db
from app.models import HCP, Interaction, ProductCatalog
from app.schemas import (
    HCPResponse, 
    InteractionResponse, 
    InteractionCreate, 
    InteractionUpdate, 
    ProductCatalogResponse, 
    AgentChatRequest, 
    AgentChatResponse
)
from app.agent.graph import run_agent_chat
from seed import seed_database

# Create tables and run seeder on startup
Base.metadata.create_all(bind=engine)
seed_database()

app = FastAPI(title="AI-First CRM HCP Module API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "AI-First CRM HCP Module API is running"}


# --- HCP ENDPOINTS ---

@app.get("/api/hcps", response_model=List[HCPResponse])
def get_hcps(db: Session = Depends(get_db)):
    return db.query(HCP).all()


@app.get("/api/hcps/search", response_model=List[HCPResponse])
def search_hcps_api(q: str = Query(..., min_length=1), db: Session = Depends(get_db)):
    hcps = db.query(HCP).filter(
        (HCP.name.ilike(f"%{q}%")) | 
        (HCP.specialty.ilike(f"%{q}%"))
    ).all()
    return hcps


# --- CATALOG ENDPOINTS ---

@app.get("/api/catalog", response_model=List[ProductCatalogResponse])
def get_catalog(
    category: str = Query(None, description="'material' or 'sample'"),
    db: Session = Depends(get_db)
):
    query = db.query(ProductCatalog)
    if category:
        query = query.filter(ProductCatalog.category == category)
    return query.all()


# --- INTERACTION ENDPOINTS ---

@app.get("/api/interactions", response_model=List[InteractionResponse])
def list_interactions(db: Session = Depends(get_db)):
    interactions = db.query(Interaction).order_by(Interaction.created_at.desc()).all()
    
    # Map raw models to response schemas, resolving hcp_name
    response = []
    for inter in interactions:
        hcp = db.query(HCP).filter(HCP.id == inter.hcp_id).first()
        hcp_name = hcp.name if hcp else "Unknown HCP"
        
        response.append(
            InteractionResponse(
                id=inter.id,
                hcp_id=inter.hcp_id,
                hcp_name=hcp_name,
                interaction_type=inter.interaction_type,
                date=inter.date,
                time=inter.time,
                attendees=inter.attendees,
                topics_discussed=inter.topics_discussed,
                materials_shared=inter.materials_shared,
                samples_distributed=inter.samples_distributed,
                sentiment=inter.sentiment,
                outcomes=inter.outcomes,
                follow_up_actions=inter.follow_up_actions,
                created_at=inter.created_at
            )
        )
    return response


@app.post("/api/interactions", response_model=InteractionResponse)
def log_interaction_api(interaction: InteractionCreate, db: Session = Depends(get_db)):
    # Validate HCP exists
    if not interaction.hcp_id:
         raise HTTPException(status_code=400, detail="HCP ID is required")
         
    hcp = db.query(HCP).filter(HCP.id == interaction.hcp_id).first()
    if not hcp:
        raise HTTPException(status_code=404, detail=f"HCP with ID {interaction.hcp_id} not found")
    
    # Fill in date/time if not provided
    date_val = interaction.date or datetime.datetime.now().strftime("%Y-%m-%d")
    time_val = interaction.time or datetime.datetime.now().strftime("%H:%M")

    new_inter = Interaction(
        hcp_id=interaction.hcp_id,
        interaction_type=interaction.interaction_type or "Meeting",
        date=date_val,
        time=time_val,
        topics_discussed=interaction.topics_discussed or "",
        sentiment=interaction.sentiment or "Neutral",
        outcomes=interaction.outcomes or "",
        follow_up_actions=interaction.follow_up_actions or ""
    )
    # Convert lists to JSON string using ORM properties setters
    new_inter.attendees = interaction.attendees or [hcp.name]
    new_inter.materials_shared = interaction.materials_shared or []
    new_inter.samples_distributed = interaction.samples_distributed or []

    db.add(new_inter)
    db.commit()
    db.refresh(new_inter)

    return InteractionResponse(
        id=new_inter.id,
        hcp_id=new_inter.hcp_id,
        hcp_name=hcp.name,
        interaction_type=new_inter.interaction_type,
        date=new_inter.date,
        time=new_inter.time,
        attendees=new_inter.attendees,
        topics_discussed=new_inter.topics_discussed,
        materials_shared=new_inter.materials_shared,
        samples_distributed=new_inter.samples_distributed,
        sentiment=new_inter.sentiment,
        outcomes=new_inter.outcomes,
        follow_up_actions=new_inter.follow_up_actions,
        created_at=new_inter.created_at
    )


@app.put("/api/interactions/{interaction_id}", response_model=InteractionResponse)
def edit_interaction_api(
    interaction_id: int, 
    interaction: InteractionUpdate, 
    db: Session = Depends(get_db)
):
    inter = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not inter:
        raise HTTPException(status_code=404, detail=f"Interaction with ID {interaction_id} not found")

    # Update fields if provided
    if interaction.hcp_id is not None:
        hcp = db.query(HCP).filter(HCP.id == interaction.hcp_id).first()
        if not hcp:
             raise HTTPException(status_code=404, detail="HCP not found")
        inter.hcp_id = interaction.hcp_id

    if interaction.interaction_type is not None:
        inter.interaction_type = interaction.interaction_type
    if interaction.date is not None:
        inter.date = interaction.date
    if interaction.time is not None:
        inter.time = interaction.time
    if interaction.topics_discussed is not None:
        inter.topics_discussed = interaction.topics_discussed
    if interaction.sentiment is not None:
        inter.sentiment = interaction.sentiment
    if interaction.outcomes is not None:
        inter.outcomes = interaction.outcomes
    if interaction.follow_up_actions is not None:
        inter.follow_up_actions = interaction.follow_up_actions

    if interaction.attendees is not None:
        inter.attendees = interaction.attendees
    if interaction.materials_shared is not None:
        inter.materials_shared = interaction.materials_shared
    if interaction.samples_distributed is not None:
        inter.samples_distributed = interaction.samples_distributed

    db.commit()
    db.refresh(inter)

    hcp = db.query(HCP).filter(HCP.id == inter.hcp_id).first()
    hcp_name = hcp.name if hcp else "Unknown HCP"

    return InteractionResponse(
        id=inter.id,
        hcp_id=inter.hcp_id,
        hcp_name=hcp_name,
        interaction_type=inter.interaction_type,
        date=inter.date,
        time=inter.time,
        attendees=inter.attendees,
        topics_discussed=inter.topics_discussed,
        materials_shared=inter.materials_shared,
        samples_distributed=inter.samples_distributed,
        sentiment=inter.sentiment,
        outcomes=inter.outcomes,
        follow_up_actions=inter.follow_up_actions,
        created_at=inter.created_at
    )


# --- AI AGENT CHAT ENDPOINT ---

@app.post("/api/agent/chat", response_model=AgentChatResponse)
def agent_chat_endpoint(payload: AgentChatRequest):
    try:
        # Convert request schemas to dictionary structures for run_agent_chat
        messages_dict = [{"role": msg.role, "content": msg.content} for msg in payload.messages]
        
        # Run agent
        result = run_agent_chat(messages_dict, payload.form_state)
        
        return AgentChatResponse(
            reply=result["reply"],
            updated_form=result["updated_form"],
            suggestions=result["suggestions"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent Error: {str(e)}")
