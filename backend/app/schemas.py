from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# HCP Schemas
class HCPBase(BaseModel):
    name: str
    specialty: str
    hospital: str
    email: EmailStr

class HCPCreate(HCPBase):
    pass

class HCPResponse(HCPBase):
    id: int

    class Config:
        from_attributes = True


# Interaction Schemas
class InteractionBase(BaseModel):
    hcp_id: int
    interaction_type: str = "Meeting"
    date: str
    time: str
    attendees: List[str] = []
    topics_discussed: str = ""
    materials_shared: List[str] = []
    samples_distributed: List[str] = []
    sentiment: str = "Neutral"
    outcomes: str = ""
    follow_up_actions: str = ""

class InteractionCreate(BaseModel):
    hcp_id: Optional[int] = None
    interaction_type: Optional[str] = "Meeting"
    date: Optional[str] = None
    time: Optional[str] = None
    attendees: Optional[List[str]] = Field(default_factory=list)
    topics_discussed: Optional[str] = ""
    materials_shared: Optional[List[str]] = Field(default_factory=list)
    samples_distributed: Optional[List[str]] = Field(default_factory=list)
    sentiment: Optional[str] = "Neutral"
    outcomes: Optional[str] = ""
    follow_up_actions: Optional[str] = ""

class InteractionUpdate(BaseModel):
    hcp_id: Optional[int] = None
    interaction_type: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    attendees: Optional[List[str]] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[List[str]] = None
    samples_distributed: Optional[List[str]] = None
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None

class InteractionResponse(BaseModel):
    id: int
    hcp_id: int
    hcp_name: Optional[str] = None
    interaction_type: str
    date: str
    time: str
    attendees: List[str]
    topics_discussed: str
    materials_shared: List[str]
    samples_distributed: List[str]
    sentiment: str
    outcomes: str
    follow_up_actions: str
    created_at: datetime

    class Config:
        from_attributes = True


# Product Catalog Schemas
class ProductCatalogBase(BaseModel):
    name: str
    category: str
    description: Optional[str] = None

class ProductCatalogResponse(ProductCatalogBase):
    id: int

    class Config:
        from_attributes = True


# Agent Chat Schemas
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class AgentChatRequest(BaseModel):
    messages: List[ChatMessage]
    form_state: Dict[str, Any]  # Current state of form on frontend

class AgentChatResponse(BaseModel):
    reply: str
    updated_form: Dict[str, Any]
    suggestions: List[str]
