import os
from groq import Groq
import edge_tts

# Initialize Groq Client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

async def transcribe_audio(file_path: str) -> str:
    """
    Transcribes audio using Groq's Whisper model.
    """
    try:
        with open(file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(file_path, file.read()),
                model="whisper-large-v3-turbo",
                response_format="json",
                language="en",
                temperature=0.0
            )
        return transcription.text
    except Exception as e:
        print(f"Transcription Error: {e}")
        raise e

async def text_to_speech(text: str, output_file: str):
    """
    Converts text to speech using Edge TTS.
    """
    try:
        communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
        await communicate.save(output_file)
    except Exception as e:
        print(f"TTS Error: {e}")
        with open(output_file, "wb") as f:
            pass