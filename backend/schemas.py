from pydantic import BaseModel
from typing import List, Optional

class HCPBase(BaseModel):
    name: str
    specialty: str
    clinic: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class HCPCreate(HCPBase):
    pass

class HCPSchema(HCPBase):
    id: int

    class Config:
        from_attributes = True

class MaterialBase(BaseModel):
    name: str
    type: str
    description: Optional[str] = None

class MaterialSchema(MaterialBase):
    id: int

    class Config:
        from_attributes = True

class SampleBase(BaseModel):
    name: str
    stock_quantity: int
    description: Optional[str] = None

class SampleSchema(SampleBase):
    id: int

    class Config:
        from_attributes = True

class FollowUpTaskBase(BaseModel):
    hcp_id: int
    interaction_id: Optional[int] = None
    description: str
    due_date: str
    status: str = "Pending"

class FollowUpTaskCreate(FollowUpTaskBase):
    pass

class FollowUpTaskSchema(FollowUpTaskBase):
    id: int

    class Config:
        from_attributes = True

class InteractionBase(BaseModel):
    hcp_id: int
    type: str
    date: str
    time: str
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    sentiment: Optional[str] = "Neutral"
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None

class InteractionCreate(InteractionBase):
    materials_shared: Optional[List[int]] = [] # list of material IDs
    samples_distributed: Optional[List[int]] = [] # list of sample IDs

class InteractionSchema(InteractionBase):
    id: int
    materials: List[MaterialSchema] = []
    samples: List[SampleSchema] = []
    tasks: List[FollowUpTaskSchema] = []

    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    current_form_state: Optional[dict] = None

class ChatResponse(BaseModel):
    response: str
    form_state: Optional[dict] = None # Updated state of the form to sync with frontend
    logs: Optional[List[str]] = [] # List of tools executed
    status: str = "success"

class VoiceNoteRequest(BaseModel):
    audio_text: str

class VoiceNoteResponse(BaseModel):
    summary: str
    extracted_fields: dict
