import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs import ElevenLabs


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ElevenLabs text-to-speech")
    parser.add_argument("--text", help="Text to synthesize")
    parser.add_argument("--voice", default="onwK4e9ZLuTAKqWW03F9", help="Voice ID (default: Daniel)")
    parser.add_argument(
        "--out",
        default="tts_output.mp3",
        help="Output audio file path",
    )
    parser.add_argument(
        "--play",
        action="store_true",
        help="Play audio after synthesis",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = _parse_args()

    text = args.text or input("Enter text to speak: ").strip()
    if not text:
        raise SystemExit("No text provided.")

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise SystemExit("ELEVENLABS_API_KEY is not set.")

    client = ElevenLabs(api_key=api_key)
    audio = client.text_to_speech.convert(
        text=text,
        voice_id=args.voice,
        output_format="mp3_44100_128",
    )

    out_path = Path(args.out)
    if args.play and args.out == "tts_output.mp3":
        temp_handle = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        out_path = Path(temp_handle.name)
        temp_handle.close()
    with out_path.open("wb") as handle:
        for chunk in audio:
            handle.write(chunk)

    print(f"Wrote audio to {out_path}")
    if args.play:
        if sys.platform == "darwin":
            subprocess.run(["afplay", str(out_path)], check=False)
        else:
            print("Auto-play is only wired for macOS. Provide --out to play manually.")


if __name__ == "__main__":
    main()
