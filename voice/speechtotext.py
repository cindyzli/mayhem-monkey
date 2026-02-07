from dotenv import load_dotenv
import os
import asyncio
import json
import queue
import threading
from flask import Flask, Response
from elevenlabs import ElevenLabs, RealtimeEvents, RealtimeUrlOptions
from elevenlabs import AudioFormat, CommitStrategy, ElevenLabs, RealtimeAudioOptions
from selenium import webdriver

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from web.selenium_adapter import SeleniumAdapter
from chaos_methods import ChaosMonkey
from command_router import ChaosCommandRouter


load_dotenv()

app = Flask(__name__)
listeners = []
listeners_lock = threading.Lock()


def broadcast(event_type, text):
    """Push an SSE event to all connected listeners immediately."""
    data = json.dumps({"type": event_type, "text": text})
    msg = f"event: transcript\ndata: {data}\n\n"
    with listeners_lock:
        for q in listeners:
            q.put(msg)


@app.route("/transcript")
def transcript_stream():
    """Live SSE endpoint — streams transcript events in real-time."""
    q = queue.Queue()
    with listeners_lock:
        listeners.append(q)

    def generate():
        try:
            while True:
                msg = q.get()
                yield msg
        finally:
            with listeners_lock:
                listeners.remove(q)

    return Response(generate(), mimetype="text/event-stream")


async def main():
    # Start Flask SSE server in a background thread
    server_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=30001, threaded=True),
        daemon=True,
    )
    server_thread.start()
    print("Live transcript server running on http://localhost:30001/transcript")
    selenium_driver = webdriver.Chrome()
    adapter = SeleniumAdapter(selenium_driver)
    monkey = ChaosMonkey()
    router = ChaosCommandRouter(monkey, driver=adapter, dry_run=False)

    elevenlabs = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    
    stop_event = asyncio.Event()

    connection = await elevenlabs.speech_to_text.realtime.connect(RealtimeUrlOptions(
        model_id="scribe_v2_realtime",
        url="http://localhost:30000/stream",
        commit_strategy=CommitStrategy.VAD,
        vad_silence_threshold_secs=1.5,
        vad_threshold=0.4,
        min_speech_duration_ms=100,
        min_silence_duration_ms=100,
        include_timestamps=False,
    ))

    def on_session_started(data):
        print(f"Session started: {data}")

    # def on_partial_transcript(data):
    #     text = data.get("text", "")
    #     print(f"Partial: {text}")
    #     broadcast("partial", text)

    def on_committed_transcript(data):
        text = data.get("text", "")
        print(f"Committed: {text}")
        broadcast("committed", text)
        router.handle_text(text)

    def on_committed_transcript_with_timestamps(data):
        print(f"Committed with timestamps: {data.get('words', '')}")

    def on_error(error):
        print(f"Error: {error}")
        stop_event.set()

    def on_close():
        print("Connection closed")

    connection.on(RealtimeEvents.SESSION_STARTED, on_session_started)
    # connection.on(RealtimeEvents.PARTIAL_TRANSCRIPT, on_partial_transcript)
    connection.on(RealtimeEvents.COMMITTED_TRANSCRIPT, on_committed_transcript)
    connection.on(RealtimeEvents.COMMITTED_TRANSCRIPT_WITH_TIMESTAMPS, on_committed_transcript_with_timestamps)
    connection.on(RealtimeEvents.ERROR, on_error)
    connection.on(RealtimeEvents.CLOSE, on_close)

    print("Transcribing audio stream... (Press Ctrl+C to stop)")

    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        print("\nStopping transcription...")
    finally:
        await connection.close()

if __name__ == "__main__":
    asyncio.run(main())
