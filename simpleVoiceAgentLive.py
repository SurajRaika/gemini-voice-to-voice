import asyncio
import logging
from google import genai
import pyaudio
import os
from dotenv import load_dotenv
from google.genai import types

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Initialize API client
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key,http_options={"api_version": "v1alpha"})

# --- pyaudio config ---
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

pya = pyaudio.PyAudio()

# --- Live API config ---
MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
CONFIG = {
    "response_modalities": ["AUDIO"],
    "realtime_input_config": {
        "automatic_activity_detection": {
            "disabled": False, # default
            "start_of_speech_sensitivity": types.StartSensitivity.START_SENSITIVITY_HIGH,
            "end_of_speech_sensitivity": types.EndSensitivity.END_SENSITIVITY_LOW,
        }
    },
    "output_audio_transcription": {},  # This enables the text transcript
    "input_audio_transcription": {},
    "proactivity": {"proactive_audio": True},
    "thinking_config":{
        "thinkingBudget": 0,
    },
    "system_instruction": " you are ai agent talking to customer "
}

audio_queue_output = asyncio.Queue()
audio_queue_mic = asyncio.Queue(maxsize=5)
audio_stream = None

async def listen_audio():
    """Listens for audio and puts it into the mic audio queue."""
    global audio_stream
    mic_info = pya.get_default_input_device_info()
    audio_stream = await asyncio.to_thread(
        pya.open,
        format=FORMAT,
        channels=CHANNELS,
        rate=SEND_SAMPLE_RATE,
        input=True,
        input_device_index=mic_info["index"],
        frames_per_buffer=CHUNK_SIZE,
    )
    kwargs = {"exception_on_overflow": False} if __debug__ else {}
    while True:
        data = await asyncio.to_thread(audio_stream.read, CHUNK_SIZE, **kwargs)
        await audio_queue_mic.put({"data": data, "mime_type": "audio/pcm"})

async def send_realtime(session):
    """Sends audio from the mic audio queue to the GenAI session."""
    while True:
        msg = await audio_queue_mic.get()
        await session.send_realtime_input(audio=msg)

async def send_text_guidance(session):
    """Reads text input from the console to guide the AI mid-conversation."""
    while True:
        # Run input() in a thread so it doesn't block your audio streams
        text = await asyncio.to_thread(input)
        if text.strip():
            # Format as a system instruction
            guidance = f"[SYSTEM INSTRUCTION - CONVERSATION GUIDANCE: {text}]"
            
            # Using the new non-deprecated method
            await session.send_client_content(
    turns=[{"role": "user", "parts": [{"text": guidance}]}],
    turn_complete=True  # "Keep listening to the mic, don't interrupt yourself to reply to this text."
)

async def receive_audio(session):
    """Receives responses from GenAI and handles audio/transcriptions."""
    while True:
        # Note: session.receive() returns an async iterator
        async for response in session.receive():
            if not response.server_content:
                continue
            
            # 1. Handle Input Transcription 
            if response.server_content.input_transcription:
                print('Input Transcript:', response.server_content.input_transcription.text)

            # 2. Handle Output Transcription 
            if response.server_content.output_transcription:
                print("Transcript:", response.server_content.output_transcription.text)

            # 3. Handle Audio Data
            if response.server_content.model_turn:
                parts = response.server_content.model_turn.parts
                for part in parts:
                    if part.inline_data:
                        audio_queue_output.put_nowait(part.inline_data.data)
                    if part.text:
                        print(part.text)  # Print the text part for debugging

        # Empty the queue on interruption to stop playback
        while not audio_queue_output.empty():
            audio_queue_output.get_nowait()

async def play_audio():
    """Plays audio from the speaker audio queue."""
    stream = await asyncio.to_thread(
        pya.open,
        format=FORMAT,
        channels=CHANNELS,
        rate=RECEIVE_SAMPLE_RATE,
        output=True,
    )
    while True:
        bytestream = await audio_queue_output.get()
        await asyncio.to_thread(stream.write, bytestream)

async def run():
    """Main function to run the audio loop."""
    try:
        async with client.aio.live.connect(
            model=MODEL, config=CONFIG
        ) as live_session:
            print("Connected to Gemini. Start speaking! You can also type instructions here and press Enter to guide the AI.")
            async with asyncio.TaskGroup() as tg:
                tg.create_task(send_realtime(live_session))
                tg.create_task(listen_audio())
                tg.create_task(receive_audio(live_session))
                tg.create_task(play_audio())
                tg.create_task(send_text_guidance(live_session)) # Added text guidance task
    except asyncio.CancelledError:
        pass
    finally:
        if audio_stream:
            audio_stream.close()
        pya.terminate()
        print("\nConnection closed.")

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("Interrupted by user.")