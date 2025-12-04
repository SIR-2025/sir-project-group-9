# Import basic preliminaries
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging
import json
from os.path import abspath, join
from dotenv import load_dotenv
from os import environ

# Import the OpenAI GPT service
from sic_framework.services.openai_gpt.gpt import (
    GPT, 
    GPTConf, 
    GPTRequest, 
    GPTResponse
)

class BabySimulation(SICApplication):
    """
    Simulation of life stages using OpenAI GPT.
    """
    
    def __init__(self, env_path=None):
        # Call parent constructor (handles singleton initialization)
        super(BabySimulation, self).__init__()
        
        # Simulation-specific initialization
        self.gpt = None
        self.env_path = env_path
        
        # Memory storage
        self.life_memory = []
        
        # Configure logging
        self.set_log_level(sic_logging.INFO)
        
        self.setup()
    
    def setup(self):
        """Initialize and configure the GPT service."""
        self.logger.info("Setting up GPT...")
        
        if self.env_path:
            load_dotenv(self.env_path)
        
        # Setup GPT
        conf = GPTConf(
            openai_key=environ.get("OPENAI_API_KEY", ""),
            system_message="You are a robotic actor simulating a human life stage.",
            model="gpt-4o-mini",
            temp=0.7,
            max_tokens=60
        )
        
        self.gpt = GPT(conf=conf)
    
    def run(self):
        """Main application loop."""
        self.logger.info("Starting Baby Simulation")
        
        # --- HARDCODED PATHS ---
        # Update these paths to match your exact local file locations
        behavior_path = '/home/urchin/Documents/Projects/sir-project-group-9/llm_prompts/baby_behaviour.json'
        role_path = '/home/urchin/Documents/Projects/sir-project-group-9/llm_prompts/baby_description.json'
        
        # Load JSON Data
        try:
            with open(behavior_path, 'r') as f:
                behavior_data = json.load(f)
            with open(role_path, 'r') as f:
                role_data = json.load(f)
        except FileNotFoundError as e:
            self.logger.error(f"Could not find JSON files: {e}")
            return

        # 1. Choose Role (Parent Persona)
        print("\n--- SELECT PARENT ROLE ---")
        available_roles = list(role_data.keys())
        for idx, role in enumerate(available_roles):
            print(f"{idx + 1}. {role}")
        
        selection = input("Enter number of parent role: ")
        try:
            parent_role_key = available_roles[int(selection) - 1]
            print(f"Selected: {parent_role_key}\n")
        except (ValueError, IndexError):
            print("Invalid selection, defaulting to parent_artist")
            parent_role_key = "parent_artist"

        # 2. Define Stages
        # Currently only testing "baby", but structure allows for more
        stages = ["baby"]
        
        try:
            for stage_name in stages:
                if self.shutdown_event.is_set():
                    break

                self.logger.info(f"Entering Stage: {stage_name}")
                print(f"\n=== CURRENT STAGE: {stage_name.upper()} ===")

                # Memory for this specific stage
                stage_memory = []

                # Get events for this stage
                stage_events = behavior_data.get(stage_name, {}).get("events", {})

                # 3. Iterate through events in the stage
                for event_name, event_info in stage_events.items():
                    if self.shutdown_event.is_set():
                        break
                    
                    print(f"\n--- Event: {event_name} ---")
                    
                    # Retrieve scene description for the specific role
                    try:
                        scene_description = role_data[parent_role_key][stage_name][event_name]
                    except KeyError:
                        scene_description = "The parent interacts with the baby."

                    print(f"Context: {scene_description}")
                    
                    # Wait for user input to trigger the event (simulating the actor readying)
                    input("Press Enter to execute event...")

                    # Prepare Prompt
                    raw_template = event_info['user_prompt_template']
                    
                    # Format Memory String
                    current_memory_str = "\n".join(stage_memory) if stage_memory else "(none yet)"

                    # Inject Context and Memory into Prompt
                    prompt = raw_template.replace("{{SCENE_DESCRIPTION}}", scene_description)
                    prompt = prompt.replace("(none yet)", current_memory_str)

                    # Request to GPT
                    reply = self.gpt.request(GPTRequest(input=prompt))
                    robot_response = reply.response.strip()
                    
                    print(f"NAO: {robot_response}")

                    # Store memory (summarize interaction)
                    interaction_log = f"Event: {event_name} | Action: {scene_description} | Reaction: {robot_response}"
                    stage_memory.append(interaction_log)

                # Summarize Life Memory
                self.life_memory.append({stage_name: stage_memory})
                print(f"\nCompleted Stage: {stage_name}")
                print("Stage Memory stored.")

            self.logger.info("Simulation ended")
            
        except Exception as e:
            self.logger.error("Exception: {}".format(e))
        finally:
            self.shutdown()

if __name__ == "__main__":
    # Create and run the demo
    # Ensure this points to the correct location of your .env file
    demo = BabySimulation(env_path=abspath(join("..", "..", "conf", ".env")))
    demo.run()