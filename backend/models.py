from pydantic import BaseModel, EmailStr
from typing import List, Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ProjectCreate(BaseModel):
    name: str
    system_prompt: str

class ChatMessage(BaseModel):
    message: str

class ChatHistory(BaseModel):
    role: str
    content: str