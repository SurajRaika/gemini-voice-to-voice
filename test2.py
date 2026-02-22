import pyaudio
import wave

# Settings
FILENAME = 'sound.wav'
OUTPUT_DEVICE = 6  # VB-Audio Virtual Cable Input

# Load the wave file
wf = wave.open(FILENAME, 'rb')
p = pyaudio.PyAudio()

# Open stream
stream = p.open(
    format=p.get_format_from_width(wf.getsampwidth()),
    channels=wf.getnchannels(),
    rate=wf.getframerate(),
    output=True,
    output_device_index=OUTPUT_DEVICE
)

print(f"Streaming {FILENAME} to Device {OUTPUT_DEVICE}...")

# Read and play data
data = wf.readframes(2048)
# 2048
try:
    while len(data) > 0:
        stream.write(data)
        data = wf.readframes(2048)
except KeyboardInterrupt:
    pass

# Cleanup
stream.stop_stream()
stream.close()
p.terminate()
wf.close()