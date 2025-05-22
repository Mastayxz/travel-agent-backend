# models/query_input.py
from pydantic import BaseModel
from typing import Optional

class QueryInput(BaseModel):
    email: str
    query: str
    session_id: Optional[str] = None  # tambahkan ini
