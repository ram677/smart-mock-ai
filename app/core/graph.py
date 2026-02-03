from typing import Any, TypedDict, List, Optional
from langgraph.graph import StateGraph, END, START
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.core.prompts import INTERVIEWER_SYSTEM_PROMPT
from app.core.sandbox import execute_code
import os

# 1. Define the State
class InterviewState(TypedDict):
    messages: List[Any]       # Chat history
    candidate_role: str       # Job role
    resume_context: str       # Resume data
    question_count: int       # Tracker
    code_snippet: Optional[str] # User's code
    code_output: Optional[str]  # Result from Piston API

# 2. Initialize Groq LLM
if not os.getenv("GROQ_API_KEY"):
    raise ValueError("GROQ_API_KEY is not set in .env file")

llm = ChatGroq(
    temperature=0.6,
    model_name="llama-3.3-70b-versatile", # Reliable, fast model
    groq_api_key=os.getenv("GROQ_API_KEY")
)

# 3. Nodes

async def run_code(state: InterviewState):
    """
    Node: Checks if there is code to run. 
    If yes, executes it via Piston and updates state.
    """
    code = state.get("code_snippet")
    if code and len(code.strip()) > 0:
        print(f"🖥️ Executing Code: {code[:20]}...")
        output = await execute_code(code, "python")
        return {"code_output": output}
    
    return {"code_output": "No code provided for this turn."}

def generate_response(state: InterviewState):
    """
    Node: Generates the Interviewer's response using Groq.
    """
    # Format the prompt
    sys_msg = SystemMessage(content=INTERVIEWER_SYSTEM_PROMPT.format(
        role=state["candidate_role"],
        context=state["resume_context"],
        stage=f"Question {state['question_count']}/5",
        code_output=state.get("code_output", "N/A")
    ))
    
    # Combine system prompt + conversation history
    # We filter out previous SystemMessages to avoid duplication, keeping only the latest logic
    history = [msg for msg in state["messages"] if not isinstance(msg, SystemMessage)]
    full_prompt = [sys_msg] + history
    
    # Call Groq
    response = llm.invoke(full_prompt)
    
    return {
        "messages": [response], # Appends to history
        "question_count": state["question_count"] + 1
    }

# 4. Build the Graph
workflow = StateGraph(InterviewState)

# Add Nodes
workflow.add_node("sandbox", run_code)
workflow.add_node("interviewer", generate_response)

# Define Edges (Flow)
# Start -> Sandbox (Check for code) -> Interviewer (Generate Reply) -> End
workflow.add_edge(START, "sandbox")
workflow.add_edge("sandbox", "interviewer")
workflow.add_edge("interviewer", END)

# Compile
interview_graph = workflow.compile()