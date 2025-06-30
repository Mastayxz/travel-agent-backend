from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Message(BaseModel):
    role: str
    content: str
    timestamp: Optional[datetime] = None
    file_name: Optional[str] = None
    image: Optional[str] = None

class ChatHistory(BaseModel):
    firebase_uid: str
    session_id: str
    messages: List[Message]
    timestamp: Optional[datetime] = None
