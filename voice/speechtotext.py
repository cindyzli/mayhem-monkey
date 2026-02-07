from dotenv import load_dotenv
import os
import asyncio
from elevenlabs import ElevenLabs, RealtimeEvents, RealtimeUrlOptions

load_dotenv()

async def main():
    elevenlabs = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

    # Create an event to signal when to stop
    stop_event = asyncio.Event()

    # Connect to a streaming audio URL
    connection = await elevenlabs.speech_to_text.realtime.connect(RealtimeUrlOptions(
        model_id="scribe_v2_realtime",
        url="http://localhost:30000/stream",
        include_timestamps=True,
    ))

    # Set up event handlers
    def on_session_started(data):
        print(f"Session started: {data}")

    def on_partial_transcript(data):
        print(f"Partial: {data.get('text', '')}")

    def on_committed_transcript(data):
        print(f"Committed: {data.get('text', '')}")

    # Committed transcripts with word-level timestamps. Only received when include_timestamps is set to True.
    def on_committed_transcript_with_timestamps(data):
        print(f"Committed with timestamps: {data.get('words', '')}")

    # Errors - will catch all errors, both server and websocket specific errors
    def on_error(error):
        print(f"Error: {error}")
        # Signal to stop on error
        stop_event.set()

    def on_close():
        print("Connection closed")

    # Register event handlers
    connection.on(RealtimeEvents.SESSION_STARTED, on_session_started)
    connection.on(RealtimeEvents.PARTIAL_TRANSCRIPT, on_partial_transcript)
    connection.on(RealtimeEvents.COMMITTED_TRANSCRIPT, on_committed_transcript)
    connection.on(RealtimeEvents.COMMITTED_TRANSCRIPT_WITH_TIMESTAMPS, on_committed_transcript_with_timestamps)
    connection.on(RealtimeEvents.ERROR, on_error)
    connection.on(RealtimeEvents.CLOSE, on_close)

    print("Transcribing audio stream... (Press Ctrl+C to stop)")

    try:
        # Wait until error occurs or connection closes
        await stop_event.wait()
    except KeyboardInterrupt:
        print("\nStopping transcription...")
    finally:
        await connection.close()

if __name__ == "__main__":
    asyncio.run(main())
