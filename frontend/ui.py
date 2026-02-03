import streamlit as st
import requests
import time
import os
from streamlit_mic_recorder import mic_recorder 
import streamlit.components.v1 as components

# Configuration
API_URL = "http://127.0.0.1:8001"
st.set_page_config(page_title="AI Interviewer", page_icon="🤖", layout="wide")

# --- 1. Anti-Cheat & Session Setup ---
if "cheat_count" not in st.session_state:
    st.session_state.cheat_count = 0
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "processing" not in st.session_state:
    st.session_state.processing = False

# JavaScript to detect tab switching (Anti-Cheat)
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

# --- 2. Sidebar (Setup) ---
with st.sidebar:
    st.title("⚙️ Settings")
    role = st.text_input("Target Role", "Generative AI Engineer")
    uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
    
    # Upload Resume Logic
    if uploaded_file and "resume_uploaded" not in st.session_state:
        with st.spinner("Processing Resume..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
            try:
                response = requests.post(f"{API_URL}/upload-resume", files=files)
                if response.status_code == 200:
                    st.success("✅ Resume Analyzed")
                    st.session_state.resume_uploaded = True
                else:
                    st.error("❌ Upload Failed")
            except Exception as e:
                st.error(f"Backend Error: {e}")

    st.markdown("---")
    st.subheader("🛡️ Proctor Status")
    st.success("✅ Session Active & Monitored")

# --- 3. Main Chat Interface ---
st.title("🤖 AI Technical Interviewer")

# Display History
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        
        # Display Audio if available
        if "audio" in msg and msg["audio"]:
            st.audio(msg["audio"])
            
        # Display Code Output if available
        if "code_output" in msg and msg["code_output"]:
            with st.expander("💻 View Code Execution Result"):
                st.code(msg["code_output"])

# --- 4. Input Area (Tabs) ---
st.markdown("### Your Answer")
tab_text, tab_voice, tab_code = st.tabs(["💬 Text Input", "🎤 Voice Answer", "💻 Code Sandbox"])

user_input = None
code_snippet = None

# A. Text Input
with tab_text:
    text_val = st.chat_input("Type your answer here...")
    if text_val:
        user_input = text_val

# B. Voice Input (Using streamlit-mic-recorder)
with tab_voice:
    st.write("Record your answer:")
    
    # This widget automatically returns audio bytes when recording stops
    audio = mic_recorder(
        start_prompt="🎤 Start Recording",
        stop_prompt="⏹️ Stop Recording",
        key='recorder',
        format='wav'
    )

    if audio:
        # 1. Save temp file
        with open("temp_mic.wav", "wb") as f:
            f.write(audio['bytes'])
        
        st.success("Audio captured!")
        
        # 2. Transcribe via Backend Button
        if st.button("📝 Send Audio Answer"):
            with st.spinner("Transcribing..."):
                try:
                    with open("temp_mic.wav", "rb") as f:
                        files = {"file": f}
                        resp = requests.post(f"{API_URL}/transcribe", files=files)
                        if resp.status_code == 200:
                            transcribed_text = resp.json()["text"]
                            st.info(f"Detected: '{transcribed_text}'")
                            user_input = transcribed_text  # Set as input
                        else:
                            st.error("Transcription failed.")
                except Exception as e:
                    st.error(f"Connection Error: {e}")

# C. Code Input
with tab_code:
    st.caption("Write Python code here to demonstrate your solution.")
    code_area = st.text_area("Python Code", height=150, key="code_area")
    if st.button("Run & Submit Code"):
        if code_area:
            user_input = f"I have written some code: \n{code_area}"
            code_snippet = code_area
        else:
            st.warning("Please write some code first.")

# --- 5. Submission Logic ---
if user_input and not st.session_state.processing:
    st.session_state.processing = True
    
    # 1. Add User Message to Chat
    st.session_state.chat_history.append({
        "role": "user", 
        "content": user_input,
        "code_snippet": code_snippet
    })
    
    # 2. Send to Backend
    payload = {
        "message": user_input,
        "history": st.session_state.chat_history,
        "role": role,
        "code_snippet": code_snippet
    }
    
    with st.spinner("Interviewer is thinking..."):
        try:
            response = requests.post(f"{API_URL}/chat", json=payload)
            if response.status_code == 200:
                data = response.json()
                
                # 3. Add Bot Response
                bot_reply = data["response"]
                audio_url = None
                
                # Construct Audio URL if backend sent a filename
                if data.get("audio_url"):
                    filename = os.path.basename(data["audio_url"])
                    audio_url = f"{API_URL}/audio/{filename}"

                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": bot_reply,
                    "audio": audio_url,
                    "code_output": data.get("code_output")
                })
                
                st.session_state.processing = False
                st.rerun()
                
            else:
                st.error(f"Server Error: {response.status_code}")
                st.session_state.processing = False
                
        except Exception as e:
            st.error(f"Connection Failed: {e}")
            st.session_state.processing = False