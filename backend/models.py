from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# Link tables for materials and samples associated with an interaction
interaction_materials = Table(
    'interaction_materials',
    Base.metadata,
    Column('interaction_id', Integer, ForeignKey('interactions.id', ondelete='CASCADE'), primary_key=True),
    Column('material_id', Integer, ForeignKey('materials.id', ondelete='CASCADE'), primary_key=True)
)

interaction_samples = Table(
    'interaction_samples',
    Base.metadata,
    Column('interaction_id', Integer, ForeignKey('interactions.id', ondelete='CASCADE'), primary_key=True),
    Column('sample_id', Integer, ForeignKey('samples.id', ondelete='CASCADE'), primary_key=True),
    Column('quantity', Integer, default=1)
)

class HCP(Base):
    __tablename__ = 'hcps'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    specialty = Column(String(100), nullable=False)
    clinic = Column(String(200), nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    
    interactions = relationship("Interaction", back_populates="hcp", cascade="all, delete-orphan")
    tasks = relationship("FollowUpTask", back_populates="hcp", cascade="all, delete-orphan")

class Interaction(Base):
    __tablename__ = 'interactions'
    
    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey('hcps.id', ondelete='CASCADE'), nullable=False)
    type = Column(String(50), nullable=False, default="Meeting") # Meeting, Email, Call, Video Conference
    date = Column(String(20), nullable=False) # YYYY-MM-DD
    time = Column(String(20), nullable=False) # HH:MM
    attendees = Column(String(200), nullable=True) # comma separated
    topics_discussed = Column(Text, nullable=True)
    sentiment = Column(String(20), nullable=True, default="Neutral") # Positive, Neutral, Negative
    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)
    
    hcp = relationship("HCP", back_populates="interactions")
    materials = relationship("Material", secondary=interaction_materials, back_populates="interactions")
    samples = relationship("Sample", secondary=interaction_samples, back_populates="interactions")
    tasks = relationship("FollowUpTask", back_populates="interaction")

class Material(Base):
    __tablename__ = 'materials'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    type = Column(String(50), nullable=False) # PDF, Brochure, Study
    description = Column(Text, nullable=True)
    
    interactions = relationship("Interaction", secondary=interaction_materials, back_populates="materials")

class Sample(Base):
    __tablename__ = 'samples'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    stock_quantity = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    
    interactions = relationship("Interaction", secondary=interaction_samples, back_populates="samples")

class FollowUpTask(Base):
    __tablename__ = 'follow_up_tasks'
    
    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey('hcps.id', ondelete='CASCADE'), nullable=False)
    interaction_id = Column(Integer, ForeignKey('interactions.id', ondelete='SET NULL'), nullable=True)
    description = Column(Text, nullable=False)
    due_date = Column(String(20), nullable=False) # YYYY-MM-DD
    status = Column(String(20), default="Pending") # Pending, Completed
    
    hcp = relationship("HCP", back_populates="tasks")
    interaction = relationship("Interaction", back_populates="tasks")
