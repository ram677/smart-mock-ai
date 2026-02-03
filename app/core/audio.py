import os
import edge_tts
from groq import Groq

# Initialize Groq Client for Transcription
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

async def transcribe_audio(file_path: str):
    """Uses Groq's Distil-Whisper for ultra-fast transcription."""
    with open(file_path, "rb") as file:
        transcription = groq_client.audio.transcriptions.create(
            file=(file_path, file.read()),
            model="distil-whisper-large-v3-en",
            response_format="text"
        )
    return transcription

async def text_to_speech(text: str, output_file: str):
    """Generates MP3 using Microsoft Edge's Free Neural Voices."""
    # Voice options: 'en-US-AriaNeural', 'en-US-GuyNeural', etc.
    communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
    await communicate.save(output_file)
    return output_file