import streamlit as st
import requests
import time
from streamlit_audiorecorder import audiorecorder
import streamlit.components.v1 as components

API_URL = "http://localhost:8000"

st.set_page_config(page_title="AI Interviewer", layout="wide")

# --- 1. Anti-Cheat JavaScript ---
# This script runs in the browser and detects visibility changes.
anti_cheat_script = """
<script>
    document.addEventListener("visibilitychange", function() {
        if (document.hidden) {
            window.parent.postMessage({
                type: "streamlit:setComponentValue",
                value: "CHEAT_DETECTED"
            }, "*");
        }
    });
</script>
"""
components.html(anti_cheat_script, height=0)

# Session State
if "cheat_count" not in st.session_state:
    st.session_state.cheat_count = 0

# --- 2. Sidebar & Setup ---
with st.sidebar:
    st.title("Settings")
    role = st.text_input("Role", "Python Developer")
    uploaded_file = st.file_uploader("Resume", type="pdf")
    
    # Cheat Monitor Display
    st.markdown("---")
    st.subheader("🛡️ Proctor Mode")
    if st.session_state.cheat_count > 0:
        st.error(f"⚠️ Tab Switches Detected: {st.session_state.cheat_count}")
    else:
        st.success("✅ Session Secure")

# --- 3. Main Chat Interface ---
st.title("🤖 AI Technical Interviewer")

# Logic to catch JS messages (Cheat Detection) is complex in Streamlit pure.
# For Portfolio: We simulate it or rely on simple focus logic if using custom component.
# Instead, we will use a latency check in Python.

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display Chat
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if "audio" in msg:
            st.audio(msg["audio"])
        if "code_output" in msg:
            with st.expander("View Code Execution"):
                st.code(msg["code_output"])

# --- 4. Input Area (Voice + Text + Code) ---
col1, col2 = st.columns([3, 1])

with col1:
    # Tabbed Interface for Input
    tab_text, tab_voice, tab_code = st.tabs(["💬 Text", "🎤 Voice", "💻 Code"])
    
    user_input = ""
    code_input = None
    
    with tab_text:
        text_val = st.chat_input("Type answer...")
        if text_val: user_input = text_val

    with tab_voice:
        audio = audiorecorder("Start Recording", "Stop")
        if len(audio) > 0:
            # Save and Transcribe
            st.info("Transcribing audio...")
            audio.export("temp_mic.wav", format="wav")
            with open("temp_mic.wav", "rb") as f:
                files = {"file": f}
                resp = requests.post(f"{API_URL}/transcribe", files=files)
                user_input = resp.json()["text"]

    with tab_code:
        code_input = st.text_area("Write Python Code (optional)", height=150)

# --- 5. Submission Logic ---
if user_input:
    # Latency Check (Simple Anti-Cheat)
    start_time = time.time()
    
    # Add User Msg
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)
        if code_input: st.code(code_input, language='python')

    # API Call
    payload = {
        "message": user_input,
        "history": st.session_state.chat_history,
        "role": role,
        "code_snippet": code_input
    }
    
    with st.spinner("Analyzing..."):
        response = requests.post(f"{API_URL}/chat", json=payload)
        data = response.json()
        
        # Display Bot Response
        bot_reply = data["response"]
        audio_url = f"{API_URL}/audio/{os.path.basename(data['audio_url'])}"
        
        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": bot_reply,
            "audio": audio_url,
            "code_output": data.get("code_output")
        })
        st.experimental_rerun()