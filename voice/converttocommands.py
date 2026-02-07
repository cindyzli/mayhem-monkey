import json
import requests


def stream_transcripts():
    """Connect to the live transcript SSE stream and yield events as they arrive."""
    response = requests.get("http://localhost:30001/transcript", stream=True)

    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        payload = json.loads(line[len("data: "):])
        yield payload


if __name__ == "__main__":
    print("Listening for live transcripts...")
    for event in stream_transcripts():
        print(f"[{event['type']}] {event['text']}")
