from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from app.core.rag import ingest_resume, get_resume_context
from app.core.graph import interview_graph
from app.core.audio import transcribe_audio, text_to_speech
from app.core.sandbox import execute_code
from langchain_core.messages import HumanMessage
import shutil
import os
import uuid

# Load env vars
load_dotenv()

app = FastAPI(title="GenAI Interview Bot")

# Ensure temp directories exist
os.makedirs("temp_audio", exist_ok=True)

# --- DEBUGGING: Print exact error if 422 happens ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"❌ VAL ERROR: {exc.errors()}")
    print(f"📥 BODY: {exc.body}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

# --- Data Models ---
class ChatRequest(BaseModel):
    message: str
    history: List[Any] = [] 
    role: str = "Generative AI Engineer"
    code_snippet: Optional[str] = None 

# --- 1. Resume Upload Endpoint ---
@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """Uploads resume and triggers RAG ingestion."""
    file_location = f"temp_{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        ingest_resume(file_location)
        if os.path.exists(file_location):
            os.remove(file_location)
        return {"status": "success", "message": "Resume processed successfully."}
    except Exception as e:
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=str(e))

# --- 2. Chat Endpoint ---
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # 1. Context Retrieval
    context = get_resume_context(request.message)
    
    # 2. Code Execution
    execution_result = ""
    if request.code_snippet:
        execution_result = await execute_code(request.code_snippet)
    
    # 3. Format Messages
    lc_messages = []
    for m in request.history:
        content = m.get('content', '')
        lc_messages.append(HumanMessage(content=str(content)))
        
    full_content = request.message
    if execution_result:
        full_content += f"\n\n[CODE OUTPUT]: {execution_result}"
        
    lc_messages.append(HumanMessage(content=full_content))
    
    inputs = {
        "messages": lc_messages,
        "candidate_role": request.role,
        "resume_context": context,
        "question_count": len(request.history) // 2,
        "code_snippet": request.code_snippet,
        "code_output": execution_result
    }
    
    # --- FIX IS HERE: Use await ainvoke() ---
    result = await interview_graph.ainvoke(inputs)
    
    bot_text = result["messages"][-1].content
    
    # 5. Audio Generation
    audio_filename = f"temp_audio/{uuid.uuid4()}.mp3"
    await text_to_speech(bot_text, audio_filename)
    
    return {
        "response": bot_text,
        "audio_url": audio_filename,
        "code_output": execution_result
    }

# --- 3. Transcribe Endpoint ---
@app.post("/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...)):
    file_location = f"temp_audio/{file.filename}"
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        text = await transcribe_audio(file_location)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(file_location):
            os.remove(file_location)

# --- 4. Audio Playback ---
@app.get("/audio/{filename}")
async def get_audio(filename: str):
    file_path = f"temp_audio/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Audio not found")