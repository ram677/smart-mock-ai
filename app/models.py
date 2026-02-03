from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[Dict] # Explicitly allow a list of dictionaries
    role: str
    code_snippet: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    audio_url: Optional[str] = None
    code_output: Optional[str] = None