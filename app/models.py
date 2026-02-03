from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]] = Field(default_factory=list) # List of {"role": "user", "content": "..."}
    role: str = "Generative AI Engineer"
    code_snippet: Optional[str] = None # Optional code input from the user

class ChatResponse(BaseModel):
    response: str
    audio_url: Optional[str] = None
    code_output: Optional[str] = None