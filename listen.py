import pyaudio
import wave

# Settings
RECORD_SECONDS = 10
WAVE_OUTPUT_FILENAME = "test_capture.wav"
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
# Try 48000 if 44100 fails (standard for Windows Realtek)
RATE = 48000 
DEVICE_INDEX = 26
# Voicemeeter Out B2 (VB-Audio Voicemeeter VAIO)
# sterio device
p = pyaudio.PyAudio()

print(f"Opening Device {DEVICE_INDEX} for 10 seconds...")

try:
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    input_device_index=DEVICE_INDEX,
                    frames_per_buffer=CHUNK)

    print("* Recording system audio...")

    frames = []

    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

    print("* Done recording.")

    # Stop and close the stream
    stream.stop_stream()
    stream.close()
    p.terminate()

    # Save to WAV file
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    print(f"Saved to: {WAVE_OUTPUT_FILENAME}")

except Exception as e:
    print(f"Error: {e}")
    print("TIP: If it fails, try changing DEVICE_INDEX to 10 or 2 from your list.")