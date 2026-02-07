import pyaudio
import wave
import io
from flask import Flask, Response

app = Flask(__name__)

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024

audio = pyaudio.PyAudio()

def get_wav_header():
    """Generates a WAV header for a continuous stream"""
    output = io.BytesIO()
    with wave.open(output, 'wb') as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(audio.get_sample_size(FORMAT))
        wav_file.setframerate(RATE)
        # Write an empty set of frames to just get the header
        wav_file.writeframes(b'')
    return output.getvalue()

def generate_audio():
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)
    
    # First, send the WAV header so the API knows the format
    yield get_wav_header()
    
    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            yield data
    finally:
        stream.stop_stream()
        stream.close()

@app.route('/stream')
def stream():
    # Use audio/wav to be explicit
    return Response(generate_audio(), mimetype='audio/wav')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=30000, threaded=True)