import asyncio
import json
import os
import aiohttp
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# 1. Setup Gemini (Use 2.0-flash or 1.5-flash)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash", 
    generation_config={"response_mime_type": "application/json"}
)

COMMAND_LIST = [
    "turn on the lights", "turn off the lights", 
    "play music", "stop music", 
    "increase volume", "decrease volume"
]

async def check_for_commands(transcript_text):
    """
    Runs in the background without stopping the stream listener.
    """
    prompt = f"""
    Analyze the transcript and match strictly to this list: {json.dumps(COMMAND_LIST)}.
    Transcript: "{transcript_text}"
    Output JSON: {{ "command": "matched_command_or_null" }}
    """
    
    # We wrap the blocking sync call in to_thread so it doesn't freeze the loop
    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        result = json.loads(response.text)
        command = result.get("command")
        if command:
            print(f"\n\033[92m🚀 EXECUTE: {command}\033[0m")
    except Exception as e:
        print(f"Gemini Error: {e}")

async def main():
    print(f"Listening for live transcripts... (Commands: {len(COMMAND_LIST)})")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:30001/transcript") as response:
                # Iterate over lines as they arrive
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if not line.startswith("data: "):
                        continue

                    try:
                        payload = json.loads(line[len("data: "):])
                        text = payload.get('text', '')
                        event_type = payload.get('type', 'partial')
                        
                        # Print live transcript (end='' prevents newlines from cluttering)
                        if event_type == 'partial':
                            print(f"\r\033[K{text}", end='', flush=True)
                        
                        # ONLY check commands on 'committed' to be efficient
                        elif event_type == 'committed':
                            print(f"\r\033[K✅ {text}") # Print finalized line
                            if text.strip():
                                # Fire and forget: This runs entirely in background
                                asyncio.create_task(check_for_commands(text))
                                
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            print(f"Connection error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping...")