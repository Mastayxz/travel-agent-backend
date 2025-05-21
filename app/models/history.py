from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

class Message(BaseModel):
    role: str  # "user" atau "assistant"
    content: str
    timestamp: Optional[datetime] = None

class ChatHistory(BaseModel):
    google_id: str
    session_id: str = Field(default_factory=lambda: str(ObjectId()))
    messages: List[Message]
    title: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None