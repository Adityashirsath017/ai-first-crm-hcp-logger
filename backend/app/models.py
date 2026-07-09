import datetime
import json
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class HCP(Base):
    __tablename__ = "hcps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    specialty = Column(String(255), nullable=False)
    hospital = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)

    # Relationships
    interactions = relationship("Interaction", back_populates="hcp", cascade="all, delete-orphan")


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id", ondelete="CASCADE"), nullable=False)
    interaction_type = Column(String(50), default="Meeting", nullable=False)
    date = Column(String(20), nullable=False)  # Format: YYYY-MM-DD
    time = Column(String(10), nullable=False)  # Format: HH:MM
    
    # Store lists as JSON-serialized strings
    _attendees = Column("attendees", Text, default="[]", nullable=False)
    topics_discussed = Column(Text, default="", nullable=False)
    _materials_shared = Column("materials_shared", Text, default="[]", nullable=False)
    _samples_distributed = Column("samples_distributed", Text, default="[]", nullable=False)
    
    sentiment = Column(String(50), default="Neutral", nullable=False)
    outcomes = Column(Text, default="", nullable=False)
    follow_up_actions = Column(Text, default="", nullable=False)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Relationships
    hcp = relationship("HCP", back_populates="interactions")

    # Helper properties for JSON columns
    @property
    def attendees(self):
        try:
            return json.loads(self._attendees or "[]")
        except Exception:
            return []

    @attendees.setter
    def attendees(self, value):
        self._attendees = json.dumps(value or [])

    @property
    def materials_shared(self):
        try:
            return json.loads(self._materials_shared or "[]")
        except Exception:
            return []

    @materials_shared.setter
    def materials_shared(self, value):
        self._materials_shared = json.dumps(value or [])

    @property
    def samples_distributed(self):
        try:
            return json.loads(self._samples_distributed or "[]")
        except Exception:
            return []

    @samples_distributed.setter
    def samples_distributed(self, value):
        self._samples_distributed = json.dumps(value or [])


class ProductCatalog(Base):
    __tablename__ = "product_catalog"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    category = Column(String(50), nullable=False)  # 'material' or 'sample'
    description = Column(String(500), nullable=True)
