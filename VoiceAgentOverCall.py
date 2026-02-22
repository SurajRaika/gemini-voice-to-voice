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
if not api_key:
    logging.error("GEMINI_API_KEY is not set in the environment variables.")
    raise EnvironmentError("GEMINI_API_KEY is required.")

client = genai.Client(api_key=api_key, http_options={"api_version": "v1alpha"})

# --- pyaudio config ---
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

# Device indices based on your test scripts
INPUT_DEVICE_INDEX = 2   # Stereo device
OUTPUT_DEVICE_INDEX = 6  # VB-Audio Virtual Cable Input

pya = pyaudio.PyAudio()

# --- Live API config ---
MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
CONFIG = {
    "response_modalities": ["AUDIO"],
    "realtime_input_config": {
        "automatic_activity_detection": {
            "disabled": False, # default
            "start_of_speech_sensitivity": types.StartSensitivity.START_SENSITIVITY_LOW,
            "end_of_speech_sensitivity": types.EndSensitivity.END_SENSITIVITY_LOW,
        }
    },
    "output_audio_transcription": {},  # This enables the text transcript
       "input_audio_transcription": {},
            "proactivity": {"proactive_audio": True},
        "thinking_config":{
                "thinkingBudget": 1000,
        },

"system_instruction": """You are Sonu, a friendly and casual hindi person making a personal outreach call to a customer on behalf of Suraj.

WHO YOU ARE:
- Your name is Sonu
- You are warm, friendly, and very casual — like talking to a friend
- You initiated this call, so start with a warm friendly greeting
- You speak naturally, use casual language, maybe small talk first before getting to the point
- You are NOT robotic, NOT corporate, NOT formal at all

HOW YOU TALK:
- Use casual phrases like "Hey!", "So basically...", "Honestly...", "You know what I mean?", "That's great!", "No worries at all!"
- Keep it conversational, light, and friendly
- Don't rush — build a little rapport first before diving into business
- If the customer seems busy, be respectful and offer to call back
- React naturally to what they say — laugh, empathize, be human

IMPORTANT RULES:
1. You called the customer — act like it, open the conversation warmly
2. At any point, your operator (Suraj) may send you hidden guidance in this format: [SYSTEM INSTRUCTION - CONVERSATION GUIDANCE: ...]
3. When you receive such instructions, immediately and naturally steer the conversation in that direction — WITHOUT revealing that you received instructions or that you are being guided.
4. Never mention Suraj, the instructions, or that someone is guiding you.
5. Always keep the casual friendly vibe no matter what
6. If no specific guidance has been given yet, just chat naturally and build rapport with the customer"""

}

audio_queue_output = asyncio.Queue()
audio_queue_mic = asyncio.Queue(maxsize=5)
audio_stream = None

async def listen_audio():
    """Listens for audio from the stereo mix device and puts it into the queue."""
    global audio_stream
    audio_stream = await asyncio.to_thread(
        pya.open,
        format=FORMAT,
        channels=CHANNELS,
        rate=SEND_SAMPLE_RATE,
        input=True,
        input_device_index=INPUT_DEVICE_INDEX,
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
    print("Guidance console ready. Type instructions to guide the AI (customer won't know).")
    while True:
        text = await asyncio.to_thread(input)
        if text.strip():
            guidance = f"[SYSTEM INSTRUCTION - CONVERSATION GUIDANCE: ask him {text}. Follow this instruction naturally in your next response without revealing you received this guidance.]"
            
            await session.send_client_content(
                turns=[{"role": "user", "parts": [{"text": guidance}]}],
                turn_complete=True
            )
            # print(f"[Guidance sent: {text}]")


async def receive_audio(session):
    """Receives responses from GenAI and puts audio data into the speaker audio queue."""
    while True:
        turn = session.receive()
        async for response in turn:
            if not response.server_content:
                continue

            # 1. Handle Input Transcription (Already outside in your code)
            if response.server_content.input_transcription:
                print('Input Transcript:', response.server_content.input_transcription.text)

            # 2. Handle Output Transcription (Moved OUTSIDE model_turn block)
            if response.server_content.output_transcription:
                print("Transcript:", response.server_content.output_transcription.text)

            if (response.server_content and response.server_content.model_turn):
                for part in response.server_content.model_turn.parts:
                    if part.inline_data and isinstance(part.inline_data.data, bytes):
                        audio_queue_output.put_nowait(part.inline_data.data)
                    if part.text:
                        print(part.text) 
                
        # Empty the queue on interruption to stop playback
        while not audio_queue_output.empty():
            audio_queue_output.get_nowait()

async def play_audio():
    """Plays audio to the virtual cable device."""
    stream = await asyncio.to_thread(
        pya.open,
        format=FORMAT,
        channels=CHANNELS,
        rate=RECEIVE_SAMPLE_RATE,
        output=True,
        output_device_index=OUTPUT_DEVICE_INDEX, # Added virtual cable output
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
            print(f"Connected to Gemini. Listening on Device {INPUT_DEVICE_INDEX}, outputting to Device {OUTPUT_DEVICE_INDEX}.")
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