from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.core.rag import ingest_resume, get_resume_context
from app.core.graph import interview_graph
from app.core.audio import transcribe_audio, text_to_speech
from app.core.sandbox import execute_code
from langchain_core.messages import HumanMessage
import shutil
import os
import uuid

app = FastAPI()

# Create temp dir for audio
os.makedirs("temp_audio", exist_ok=True)

class ChatRequest(BaseModel):
    message: str
    history: list
    role: str
    code_snippet: str = None  # Optional code input

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # 1. Context Retrieval
    context = get_resume_context(request.message)
    
    # 2. Code Execution (if code is provided)
    execution_result = ""
    if request.code_snippet:
        execution_result = await execute_code(request.code_snippet)
    
    # 3. LangGraph Inputs
    lc_messages = [HumanMessage(content=m['content']) for m in request.history]
    lc_messages.append(HumanMessage(content=f"{request.message} \n [CODE OUTPUT]: {execution_result}"))
    
    inputs = {
        "messages": lc_messages,
        "candidate_role": request.role,
        "resume_context": context,
        "question_count": len(request.history) // 2,
        "code_snippet": request.code_snippet,
        "code_output": execution_result
    }
    
    result = interview_graph.invoke(inputs)
    bot_text = result["messages"][-1].content
    
    # 4. Generate Voice Response (Async)
    audio_filename = f"temp_audio/{uuid.uuid4()}.mp3"
    await text_to_speech(bot_text, audio_filename)
    
    return {
        "response": bot_text,
        "audio_url": audio_filename,
        "code_output": execution_result
    }

@app.post("/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...)):
    """API to convert Microphone input to Text"""
    file_location = f"temp_audio/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    text = await transcribe_audio(file_location)
    os.remove(file_location)
    return {"text": text}

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    return FileResponse(f"temp_audio/{filename}")