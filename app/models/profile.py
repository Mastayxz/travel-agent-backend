from pydantic import BaseModel
from typing import Optional

class UserProfile(BaseModel):
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None

class UpdateProfile(BaseModel):
    name: Optional[str] = None
    picture: Optional[str] = None
