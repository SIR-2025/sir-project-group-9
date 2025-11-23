import asyncio
import os
import sys
from dotenv import load_dotenv

# Import the Realtime components from the official SDK
from agents.realtime import RealtimeAgent, RealtimeRunner

# Load environment variables (API Key)
load_dotenv()

if not os.getenv("OPENAI_API_KEY"):
    print("Error: OPENAI_API_KEY not found. Please set it in your environment or .env file.")
    sys.exit(1)

# --- Configuration: Life Stages ---
STAGES = {
    "1": {
        "name": "Baby",
        "voice": "sage", 
        "instructions": "You are a baby. You use simple words, babble often, and are easily distracted."
    },
    "2": {
        "name": "Child",
        "voice": "coral",
        "instructions": "You are a 5-year-old child. You are curious, ask 'why?' often, and have a wild imagination."
    },
    "3": {
        "name": "Adolescent",
        "voice": "ash",
        "instructions": "You are a rebellious teenager. You use slang like 'cap' and 'vibes', and act cool/detached."
    },
    "4": {
        "name": "Adult",
        "voice": "alloy",
        "instructions": "You are a helpful, professional adult. You speak clearly and give sound advice."
    },
    "5": {
        "name": "Elderly",
        "voice": "verse",
        "instructions": "You are a wise elderly person. You speak slowly, use terms like 'dearie', and share old wisdom."
    }
}

def select_stage():
    """Displays the CLI menu and returns the selected config."""
    print("\n--- Select the Agent's Life Stage ---")
    for key, stage in STAGES.items():
        print(f"{key}. {stage['name']}")
    
    choice = input("\nEnter choice (1-5): ").strip()
    return STAGES.get(choice, STAGES["4"]) # Default to Adult

async def main():
    # 1. Get User Selection
    stage_config = select_stage()
    print(f"\nInitializing agent as: {stage_config['name']}...")
    print("Press Ctrl+C to stop the conversation.")

    # 2. Create the Realtime Agent
    agent = RealtimeAgent(
        name=stage_config["name"],
        instructions=stage_config["instructions"]
    )

    # 3. Configure the Runner
    runner = RealtimeRunner(
        starting_agent=agent,
        config={
            "model_settings": {
                "model": "gpt-4o-realtime-preview", 
                "voice": stage_config["voice"], 
                # FIX: Must be strictly ["audio"] for voice mode. 
                # You will still get transcripts via events.
                "modalities": ["audio"], 
            },
            "turn_detection": {
                "type": "server_vad",
            }
        }
    )

    # 4. Start the Session and KEEP IT ALIVE
    print("--- Connecting... ---")
    session = await runner.run()
    print("--- Connected! Start speaking now. ---")
    
    try:
        async with session:
            async for event in session:
                if event.type == "conversation.item.input_audio_transcription.completed":
                    print(f"\nYou: {event.transcript}")
                elif event.type == "response.audio_transcript.done":
                    print(f"Agent: {event.transcript}")
                elif event.type == "error":
                    print(f"Error: {event.error}")
                    
    except asyncio.CancelledError:
        print("\nSession cancelled.")
    except KeyboardInterrupt:
        print("\nSession ended by user.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")