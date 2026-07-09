import json
from typing import List, Optional
from langchain_core.tools import tool
from app.database import SessionLocal
from app.models import HCP, Interaction, ProductCatalog

@tool
def search_hcps(query: str) -> str:
    """
    Search the database for Healthcare Professionals (HCPs) by name or specialty.
    Use this tool when you need to find an HCP's details or confirm their spelling/specialty.
    """
    db = SessionLocal()
    try:
        hcps = db.query(HCP).filter(
            (HCP.name.ilike(f"%{query}%")) | 
            (HCP.specialty.ilike(f"%{query}%"))
        ).all()
        
        if not hcps:
            return f"No HCPs found matching query: '{query}'."
        
        result_list = []
        for hcp in hcps:
            result_list.append({
                "id": hcp.id,
                "name": hcp.name,
                "specialty": hcp.specialty,
                "hospital": hcp.hospital,
                "email": hcp.email
            })
        return json.dumps(result_list, indent=2)
    finally:
        db.close()


@tool
def get_hcp_history(hcp_name: str) -> str:
    """
    Retrieve the last 3 logged interactions with a specific HCP.
    Use this to get context on the relationship history before logging a new interaction.
    """
    db = SessionLocal()
    try:
        hcp = db.query(HCP).filter(HCP.name.ilike(f"%{hcp_name}%")).first()
        if not hcp:
            return f"HCP '{hcp_name}' not found."
        
        interactions = db.query(Interaction).filter(
            Interaction.hcp_id == hcp.id
        ).order_by(Interaction.created_at.desc()).limit(3).all()
        
        if not interactions:
            return f"No past interactions found for {hcp.name}."
        
        history = []
        for idx, inter in enumerate(interactions):
            history.append({
                "index": idx + 1,
                "interaction_id": inter.id,
                "type": inter.interaction_type,
                "date": inter.date,
                "time": inter.time,
                "topics": inter.topics_discussed,
                "sentiment": inter.sentiment,
                "outcomes": inter.outcomes,
                "follow_up": inter.follow_up_actions
            })
        return json.dumps(history, indent=2)
    finally:
        db.close()


@tool
def suggest_clinical_content(topic: str) -> str:
    """
    Search the product catalog for relevant brochures (materials) and drug samples matching a topic (e.g. 'OncoBoost', 'CardioLife').
    Use this to suggest materials to share or samples to distribute during or after an interaction.
    """
    db = SessionLocal()
    try:
        items = db.query(ProductCatalog).filter(
            (ProductCatalog.name.ilike(f"%{topic}%")) | 
            (ProductCatalog.description.ilike(f"%{topic}%"))
        ).all()
        
        if not items:
            return f"No materials or samples found for topic: '{topic}'."
        
        materials = []
        samples = []
        for item in items:
            item_data = {"name": item.name, "description": item.description}
            if item.category == "material":
                materials.append(item_data)
            else:
                samples.append(item_data)
                
        return json.dumps({
            "materials_suggested": materials,
            "samples_suggested": samples
        }, indent=2)
    finally:
        db.close()


@tool
def log_interaction(
    hcp_name: str,
    date: str,
    time: str,
    interaction_type: str = "Meeting",
    attendees: Optional[List[str]] = None,
    topics_discussed: str = "",
    materials_shared: Optional[List[str]] = None,
    samples_distributed: Optional[List[str]] = None,
    sentiment: str = "Neutral",
    outcomes: str = "",
    follow_up_actions: str = ""
) -> str:
    """
    Save/Log a new HCP interaction to the database.
    Required fields: hcp_name (full name, e.g. 'Dr. Ramesh Sharma'), date (YYYY-MM-DD), time (HH:MM).
    """
    db = SessionLocal()
    try:
        # Resolve HCP Name
        hcp = db.query(HCP).filter(HCP.name.ilike(f"%{hcp_name}%")).first()
        if not hcp:
            return f"Error: HCP '{hcp_name}' not found. Please verify spelling or search for HCPs first."
        
        # Create interaction
        new_inter = Interaction(
            hcp_id=hcp.id,
            interaction_type=interaction_type,
            date=date,
            time=time,
            topics_discussed=topics_discussed,
            sentiment=sentiment,
            outcomes=outcomes,
            follow_up_actions=follow_up_actions
        )
        # SQLAlchemy setter helper triggers on properties
        new_inter.attendees = attendees or []
        new_inter.materials_shared = materials_shared or []
        new_inter.samples_distributed = samples_distributed or []
        
        db.add(new_inter)
        db.commit()
        db.refresh(new_inter)
        
        return json.dumps({
            "status": "success",
            "message": f"Successfully logged new interaction with {hcp.name}.",
            "interaction_id": new_inter.id,
            "details": {
                "hcp_id": hcp.id,
                "hcp_name": hcp.name,
                "date": new_inter.date,
                "time": new_inter.time,
                "type": new_inter.interaction_type
            }
        })
    except Exception as e:
        db.rollback()
        return f"Error logging interaction: {str(e)}"
    finally:
        db.close()


@tool
def edit_interaction(
    interaction_id: int,
    interaction_type: Optional[str] = None,
    date: Optional[str] = None,
    time: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    topics_discussed: Optional[str] = None,
    materials_shared: Optional[List[str]] = None,
    samples_distributed: Optional[List[str]] = None,
    sentiment: Optional[str] = None,
    outcomes: Optional[str] = None,
    follow_up_actions: Optional[str] = None
) -> str:
    """
    Modify/Edit an existing logged interaction in the database using its interaction_id.
    Only provided fields will be updated.
    """
    db = SessionLocal()
    try:
        inter = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not inter:
            return f"Error: Interaction with ID {interaction_id} not found."
        
        # Track changes for response message
        changes = {}
        
        if interaction_type is not None:
            inter.interaction_type = interaction_type
            changes["interaction_type"] = interaction_type
        if date is not None:
            inter.date = date
            changes["date"] = date
        if time is not None:
            inter.time = time
            changes["time"] = time
        if attendees is not None:
            inter.attendees = attendees
            changes["attendees"] = attendees
        if topics_discussed is not None:
            inter.topics_discussed = topics_discussed
            changes["topics_discussed"] = topics_discussed
        if materials_shared is not None:
            inter.materials_shared = materials_shared
            changes["materials_shared"] = materials_shared
        if samples_distributed is not None:
            inter.samples_distributed = samples_distributed
            changes["samples_distributed"] = samples_distributed
        if sentiment is not None:
            inter.sentiment = sentiment
            changes["sentiment"] = sentiment
        if outcomes is not None:
            inter.outcomes = outcomes
            changes["outcomes"] = outcomes
        if follow_up_actions is not None:
            inter.follow_up_actions = follow_up_actions
            changes["follow_up_actions"] = follow_up_actions
            
        db.commit()
        db.refresh(inter)
        
        hcp = db.query(HCP).filter(HCP.id == inter.hcp_id).first()
        hcp_name = hcp.name if hcp else "Unknown"
        
        return json.dumps({
            "status": "success",
            "message": f"Successfully updated interaction {interaction_id} for {hcp_name}.",
            "changes": changes,
            "interaction_id": inter.id
        })
    except Exception as e:
        db.rollback()
        return f"Error editing interaction: {str(e)}"
    finally:
        db.close()

# List of all sales tools
sales_tools = [search_hcps, get_hcp_history, suggest_clinical_content, log_interaction, edit_interaction]
