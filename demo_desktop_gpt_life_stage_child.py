from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging
import json
from os import environ
from dotenv import load_dotenv
from os.path import abspath, join

from sic_framework.services.openai_gpt.gpt import (
    GPT, 
    GPTConf, 
    GPTRequest
)

class ChildStage(SICApplication):
    def __init__(self, env_path=None):
        super().__init__()
        self.env_path = env_path
        self.set_log_level(sic_logging.INFO)
        self.gpt = None
        self.life_memory = []
        self.setup()

    def setup(self):
        if self.env_path:
            load_dotenv(self.env_path)

        conf = GPTConf(
            openai_key=environ.get("OPENAI_API_KEY", ""),
            system_message="You are NAO simulating the CHILD stage.",
            model="gpt-4o-mini",
            temp=0.7,
            max_tokens=70
        )
        self.gpt = GPT(conf=conf)

    def run(self):
        stage = "child"
        self.logger.info("Running CHILD stage")

        # --- LOAD CHILD BEHAVIOR ---
        with open("/home/urchin/Documents/Projects/sir-project-group-9/llm_prompts/child_behaviour.json", "r") as f:
            behavior = json.load(f)

        stage_events = behavior[stage]["events"]

        # --- LOAD ONLY CHILD DESCRIPTION DATA ---
        with open("/home/urchin/Documents/Projects/sir-project-group-9/llm_prompts/description/child_desription.json", "r") as f:
            role_data = json.load(f)

        valid_roles = [r for r in role_data if stage in role_data[r]]

        print("\n--- SELECT CHILD ROLE ---")
        for i, r in enumerate(valid_roles):
            print(f"{i+1}. {r} -> {role_data[r]['description']}")

        try:
            selected = valid_roles[int(input("\nChoose role: ")) - 1]
        except:
            selected = valid_roles[0]

        print(f"\nSelected role: {selected}")

        stage_memory = []

        for event_name, info in stage_events.items():
            print(f"\n--- Event: {event_name} ---")

            scene_desc = role_data[selected][stage][event_name]

            print(f"Context: {scene_desc}")
            input("Press Enter to execute event...")

            template = info["user_prompt_template"]
            memory_str = "\n".join(stage_memory) if stage_memory else "(none yet)"

            prompt = template.replace("{{CHILD_DESCRIPTION}}", scene_desc)
            prompt = prompt.replace("(none yet)", memory_str)

            reply = self.gpt.request(GPTRequest(input=prompt))
            resp = reply.response.strip()

            print(f"NAO: {resp}")

            stage_memory.append(
                f"Event: {event_name} | Action: {scene_desc} | Reaction: {resp}"
            )

        print("\nCHILD stage complete.")
        self.shutdown()


if __name__ == "__main__":
    ChildStage(env_path=abspath(join("..", "..", "conf", ".env"))).run()
