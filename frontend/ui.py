import streamlit as st
import requests
import streamlit.components.v1 as components

# --- CONFIGURATION ---
API_URL = "http://127.0.0.1:8001"

st.set_page_config(
    page_title="AI Technical Interviewer",
    page_icon="🤖",
    layout="wide"
)

# --- ANTI-CHEAT & PROCTORING (JavaScript Hook) ---
# This script listens for tab switching events
components.html(
    """
    <script>
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            console.log("Tab switch detected!");
        } else {
            alert("⚠️ WARNING: Tab switching detected! \\n\\nThis session is being monitored. Please stay on this tab to maintain interview integrity.");
        }
    });
    </script>
    """,
    height=0,
)

# --- SESSION STATE INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "resume_uploaded" not in st.session_state:
    st.session_state.resume_uploaded = False

# --- SIDEBAR: SETTINGS & RESUME ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # 1. Role Selection
    target_role = st.text_input("Target Role", value="Generative AI Engineer")
    
    # 2. Resume Upload
    st.subheader("Upload Resume (PDF)")
    uploaded_file = st.file_uploader("Drag and drop file here", type=["pdf"])
    
    if uploaded_file and not st.session_state.resume_uploaded:
        with st.spinner("Analyzing Resume..."):
            files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
            try:
                # Use a session that ignores proxies for localhost
                session = requests.Session()
                session.trust_env = False
                response = session.post(f"{API_URL}/upload-resume", files=files)
                
                if response.status_code == 200:
                    st.success("✅ Resume Analyzed")
                    st.session_state.resume_uploaded = True
                else:
                    st.error(f"Upload Failed: {response.text}")
            except Exception as e:
                st.error(f"Connection Error: {e}")

    st.divider()
    
    # 3. Proctor Status Badge
    st.markdown("### 🛡️ Proctor Status")
    st.success("✅ Session Active & Monitored")
    st.info("Note: Switching tabs will trigger a violation warning.")

# --- MAIN CHAT INTERFACE ---
st.title("🤖 AI Technical Interviewer")

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # If there is code output in the message, show it
        if "code_output" in message and message["code_output"]:
            with st.expander("💻 View Code Execution Result"):
                st.code(message["code_output"])
        
        # If there is an audio response, play it
        if "audio_url" in message and message["audio_url"]:
            # Construct full URL for the audio file
            audio_link = f"{API_URL}/audio/{message['audio_url'].split('/')[-1]}"
            st.audio(audio_link)

# --- INPUT AREA (TABS) ---
st.subheader("Your Answer")
tab1, tab2, tab3 = st.tabs(["💬 Text Input", "🎤 Voice Answer", "💻 Code Sandbox"])

# TAB 1: Text Input
with tab1:
    text_input = st.text_area("Type your answer here...", height=100, key="text_area_input")
    if st.button("Send Text Answer"):
        if text_input:
            user_msg = {"role": "user", "content": text_input}
            st.session_state.messages.append(user_msg)
            
            # Send to Backend
            with st.spinner("Interviewer is thinking..."):
                try:
                    session = requests.Session()
                    session.trust_env = False
                    payload = {
                        "message": text_input,
                        "history": st.session_state.messages,
                        "role": target_role,
                        "code_snippet": None
                    }
                    response = session.post(f"{API_URL}/chat", json=payload)
                    
                    if response.status_code == 200:
                        data = response.json()
                        bot_msg = {
                            "role": "assistant",
                            "content": data["response"],
                            "audio_url": data.get("audio_url"),
                            "code_output": data.get("code_output")
                        }
                        st.session_state.messages.append(bot_msg)
                        st.rerun()
                    else:
                        st.error(f"Server Error: {response.status_code}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")

# TAB 2: Voice Answer
with tab2:
    st.markdown("Record your answer:")
    # Streamlit 1.40+ native audio input
    audio_value = st.audio_input("Record")
    
    if audio_value:
        st.success("Audio captured!")
        if st.button("📝 Send Audio Answer"):
            with st.spinner("Transcribing..."):
                try:
                    # 1. Transcribe
                    files = {"file": ("temp_mic.wav", audio_value, "audio/wav")}
                    session = requests.Session()
                    session.trust_env = False
                    
                    transcribe_res = session.post(f"{API_URL}/transcribe", files=files)
                    
                    if transcribe_res.status_code == 200:
                        transcribed_text = transcribe_res.json()["text"]
                        st.info(f"Detected: '{transcribed_text}'")
                        
                        # 2. Send as Chat Message
                        user_msg = {"role": "user", "content": transcribed_text}
                        st.session_state.messages.append(user_msg)
                        
                        with st.spinner("Interviewer is thinking..."):
                            payload = {
                                "message": transcribed_text,
                                "history": st.session_state.messages,
                                "role": target_role,
                                "code_snippet": None
                            }
                            chat_res = session.post(f"{API_URL}/chat", json=payload)
                            
                            if chat_res.status_code == 200:
                                data = chat_res.json()
                                bot_msg = {
                                    "role": "assistant",
                                    "content": data["response"],
                                    "audio_url": data.get("audio_url")
                                }
                                st.session_state.messages.append(bot_msg)
                                st.rerun()
                            else:
                                st.error(f"Chat Error: {chat_res.status_code}")
                    else:
                        st.error("Transcription failed.")
                except Exception as e:
                    st.error(f"Error: {e}")

# TAB 3: Code Sandbox
with tab3:
    st.markdown("Write Python code here to demonstrate your solution.")
    code_input = st.text_area("Python Code", height=200, value="def solution():\n    pass")
    
    if st.button("Run & Submit Code"):
        if code_input:
            # Add code to chat history visibly
            user_msg = {"role": "user", "content": f"I have written some code: {code_input}"}
            st.session_state.messages.append(user_msg)
            
            with st.spinner("Running code and evaluating..."):
                try:
                    session = requests.Session()
                    session.trust_env = False
                    payload = {
                        "message": "Here is my code solution.",
                        "history": st.session_state.messages,
                        "role": target_role,
                        "code_snippet": code_input
                    }
                    response = session.post(f"{API_URL}/chat", json=payload)
                    
                    if response.status_code == 200:
                        data = response.json()
                        bot_msg = {
                            "role": "assistant",
                            "content": data["response"],
                            "audio_url": data.get("audio_url"),
                            "code_output": data.get("code_output")
                        }
                        st.session_state.messages.append(bot_msg)
                        st.rerun()
                    else:
                        st.error(f"Server Error: {response.status_code}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")