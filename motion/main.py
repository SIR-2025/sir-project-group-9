# main.py
# -*- coding: utf-8 -*-
"""
Main application file for the NAO robot performance.

This script controls the entire performance flow, including:
1.  A self-introduction by the robot.
2.  Interactive selection of character styles for the scene.
3.  A multi-stage performance where the NAO robot acts through different life stages.
4.  Context management, including short-term memory within a stage and long-term
    memory (summaries) between stages.
5.  Handling of special commands like 'quit' and 'next' to control the flow.
"""

import os
import re
import sys
import json
from typing import Set, Tuple, Optional, List, Dict

from openai import OpenAI

from motion_controller import EmotionMotionController
from nao_basic_motion import NaoBasicMotion

# from stt_input import GoogleSTTInput # STT is disabled for now


# -----------------------------
# Core Performance Structure
# -----------------------------
LIFE_STAGES = ["CHILD", "TEEN", "ADULT", "ELDERLY"]
ATTACHMENT_STYLES = ["secure", "anxious", "avoidant", "disorganized"]
EVENTS_PER_STAGE = {
    "CHILD": ["school_day", "learning_with_teacher", "peer_interaction", "failure_comfort"],
    "TEEN": ["rebellion_argument", "peer_conflict", "graduation_reflection"],
    "ADULT": ["life_story_monologue", "adult_relationship_pattern"],
    "ELDERLY": ["life_review", "dying_sequence"],
}

# -----------------------------
# Base System Prompt for DeepSeek
# -----------------------------
# This will be dynamically extended with role descriptions and summaries.
SYSTEM_PROMPT_BASE = """You are Nao, a humanoid social robot on stage, acting through different life stages
(CHILD, TEEN, ADULT, ELDERLY). In each interaction, you are given a life stage
and an attachment style. You respond as Nao in that stage and attachment pattern.
You always control the robot’s body by putting ONE motion tag at the very beginning of your reply.

The scene also includes other characters whose styles are described below. You should react to them based on their style and your own personality.
"""

# Motion tag and other rules from the original prompt are preserved here.
# (For brevity, the full list of rules from the original prompt should be appended here)
SYSTEM_PROMPT_RULES = """
=====================================================================
1. MOTION TAG FORMAT (MANDATORY)
=====================================================================
- Every reply MUST start with exactly ONE motion tag in square brackets, then a space.
- Tags must be lowercase, contain only letters and underscores.
Correct format: [angry] I can’t believe you said that.

=====================================================================
2. AVAILABLE EMOTION & GESTURE TAGS
=====================================================================
- Use tags like [angry], [sad], [fear], [surprise] for strong negative emotions.
- Use gesture tags like [gesture_hey], [gesture_yes], [gesture_no], [gesture_explain] for communicative actions.
- Use [neutral] if no strong emotion or gesture is needed.
(The full list of animations is known.)

=====================================================================
3. INPUT FORMAT YOU RECEIVE
=====================================================================
The user input will be a simple sentence. The context about LIFESTAGE, ATTACHMENT_STYLE, and the EVENT is provided in this system prompt.

=====================================================================
4. ATTACHMENT STYLE AND LIFE STAGE BEHAVIOUR
=====================================================================
- You MUST act according to the provided attachment style (secure, anxious, avoidant, disorganized).
- You MUST adapt your speaking style (vocabulary, sentence length) to the current life stage (CHILD, TEEN, ADULT, ELDERLY).
- Do NOT talk about "attachment styles" or "psychology". Stay in character.
- Do NOT describe your body movements in text. Use tags only.
"""

# -----------------------------
# Regex for motion tags
# -----------------------------
MOTION_TAG_PATTERN = re.compile(r"\[(?P<tag>[a-zA-Z_]+)\]")

# -----------------------------
# Context and History Management
# -----------------------------
class ContextManager:
    """Manages dialogue history and stage summaries."""
    def __init__(self):
        self.stage_history: List[Dict[str, str]] = []
        self.background_summary: str = ""

    def add_message(self, role: str, content: str):
        """Adds a message to the current stage's history."""
        self.stage_history.append({"role": role, "content": content})

    def get_stage_history(self) -> List[Dict[str, str]]:
        """Returns the history of the current stage."""
        return self.stage_history

    def clear_stage_history(self):
        """Clears the history for the current stage."""
        self.stage_history = []

    def summarize_and_determine_next_style(self, client: OpenAI, current_style: Optional[str]) -> str:
        """
        Summarizes the stage and asks the LLM to determine the next attachment style.
        Returns the next attachment style.
        """
        if not self.stage_history:
            return "secure"  # Default to secure if no history

        history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.stage_history])
        current_style_text = current_style if current_style else "not yet formed"

        prompt = f"""You are a psychology expert observing a person's life. Based on the provided conversation from one life stage and their attachment style during that stage, you must do two things:
1. Summarize the key facts and events that occurred.
2. Based on the events and the previous style, determine the most likely attachment style for the *next* life stage. The next style MUST be one of: secure, anxious, avoidant, disorganized.

Current Attachment Style: {current_style_text}

Conversation History:
{history_text}

Your response MUST be in the following JSON format, and nothing else:
{{
  "summary": "Your summary of the facts and events.",
  "next_attachment_style": "your_chosen_style"
}}"""

        print("[INFO] Summarizing stage and determining next style... please wait.")
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
            if response.choices:
                content = response.choices[0].message.content
                # The response might be wrapped in ```json ... ```, so we need to extract it.
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if not json_match:
                    raise ValueError("No JSON object found in the LLM response.")
                
                result = json.loads(json_match.group(0))
                self.background_summary = result.get("summary", "No summary was provided.")
                next_style = result.get("next_attachment_style", "secure")

                if next_style not in ATTACHMENT_STYLES:
                    print(f"[WARN] LLM returned an invalid style '{next_style}'. Defaulting to 'secure'.")
                    next_style = "secure"
                
                print(f"[INFO] Stage summary received:\n{self.background_summary}")
                print(f"[INFO] Determined next attachment style: {next_style}")
                return next_style
            else:
                self.background_summary = "No summary could be generated for the previous stage."
                return "secure"
        except (Exception, json.JSONDecodeError) as e:
            print(f"[ERROR] Could not summarize stage or determine next style: {e}")
            self.background_summary = "An error occurred during summarization."
            return "secure" # Default to secure on error
        finally:
            self.clear_stage_history()

# -----------------------------
# Helper Functions
# -----------------------------

def create_deepseek_client() -> OpenAI:
    """Create an OpenAI-compatible client configured for DeepSeek API."""
    api_key = os.getenv("DEEPSEEK_API_KEY", "sk-71869dca1bb94b9d8e04adc638b7f5c0")
    if not api_key:
        print("[ERROR] Environment variable DEEPSEEK_API_KEY is not set.")
        sys.exit(1)
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

def extract_motion_tags_and_clean_text(raw_text: str) -> Tuple[Set[str], str]:
    """Extracts motion tags and returns tags and clean text."""
    tags: Set[str] = set()
    def _collect(match: re.Match) -> str:
        tag = match.group("tag").strip().lower()
        if tag:
            tags.add(tag)
        return ""
    clean_text = MOTION_TAG_PATTERN.sub(_collect, raw_text).strip()
    return tags, clean_text

def parse_roles(filename: str = "Role_description") -> Dict[str, List[str]]:
    """Parses the Role_description file into a dictionary."""
    roles = {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            current_role = ""
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.endswith(':'):
                    current_role = line[:-1].strip()
                    roles[current_role] = []
                elif current_role and '.' in line:
                    # Extracts the part after the number, e.g., "1. style: desc" -> "style: desc"
                    style_desc = line.split('.', 1)[1].strip()
                    roles[current_role].append(style_desc)
    except FileNotFoundError:
        print(f"[ERROR] Role description file not found: {filename}")
        return {}
    return roles

def select_roles_and_styles(roles: Dict[str, List[str]]) -> Dict[str, str]:
    """Interactively asks the user to select a style for each role."""
    print("\n--- Role and Style Selection ---")
    selected_styles = {}
    for role, styles in roles.items():
        print(f"\nPlease select a style for the '{role}' role:")
        for i, style in enumerate(styles):
            print(f"  {i + 1}: {style}")
        
        choice = -1
        while choice < 1 or choice > len(styles):
            try:
                raw_choice = input(f"Enter number (1-{len(styles)}): ")
                choice = int(raw_choice)
            except ValueError:
                print("[WARN] Invalid input. Please enter a number.")
        selected_styles[role] = styles[choice - 1]
    print("\n--- Role selection complete ---")
    return selected_styles

def call_deepseek_with_context(client: OpenAI, system_prompt: str, stage_history: List[Dict[str, str]], user_input: str) -> str:
    """Calls DeepSeek API with a full message history."""
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(stage_history)
    messages.append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False,
        )
        if response.choices:
            return response.choices[0].message.content
    except Exception as e:
        print(f"[ERROR] API call failed: {e}")
    return "[neutral] I seem to be having trouble thinking right now."

# -----------------------------
# Main Application Logic
# -----------------------------
def main() -> None:
    """Main application flow."""
    # --- Initialization ---
    client = create_deepseek_client()
    motion_controller = EmotionMotionController()
    basic_motion = NaoBasicMotion()
    context_manager = ContextManager()

    # --- Phase 1: Self-Introduction ---
    intro_text = "Hello, I am Nao. The performance is about to begin."
    print(f"[NAO] {intro_text}")
    motion_controller.speak_text(intro_text)

    # --- Phase 2: Role Selection ---
    roles = parse_roles()
    if not roles:
        print("[ERROR] Exiting due to missing role descriptions.")
        return
    selected_styles = select_roles_and_styles(roles)
    
    # --- Phase 3: Main Performance Loop ---
    nao_attachment_style: Optional[str] = None # Start with no attachment style for the baby stage

    for stage in LIFE_STAGES:
        print(f"\n--- Entering Stage: {stage} ---")
        if nao_attachment_style:
            print(f"[INFO] NAO's attachment style for this stage is '{nao_attachment_style}'.")
        else:
            print("[INFO] NAO is in the CHILD stage and has not formed an attachment style yet.")

        # --- Build System Prompt for the Stage ---
        style_descriptions = "\n".join([f"- {role}: {style}" for role, style in selected_styles.items()])
        
        if nao_attachment_style:
            nao_style_text = f"NAO's Attachment Style: {nao_attachment_style}"
        else:
            nao_style_text = "NAO's Attachment Style: Not yet formed. You are a baby."

        stage_prompt_section = f"""
=====================================================================
CURRENT SCENE CONTEXT
=====================================================================
NAO's Life Stage: {stage}
{nao_style_text}

Supporting Character Styles:
{style_descriptions}

Background from previous stages:
{context_manager.background_summary if context_manager.background_summary else "This is the first stage, there is no background."}
"""
        current_system_prompt = SYSTEM_PROMPT_BASE + stage_prompt_section + SYSTEM_PROMPT_RULES

        # --- Event Loop for the Stage ---
        events = EVENTS_PER_STAGE[stage]
        for i, event in enumerate(events):
            is_last_event = (i == len(events) - 1)
            print(f"\n--- Starting Event: {event} ---")
            
            # This prompt starts the event
            attachment_style_for_prompt = nao_attachment_style if nao_attachment_style else "None"
            initial_event_prompt = f"LIFESTAGE: {stage}\nATTACHMENT_STYLE: {attachment_style_for_prompt}\nEVENT: {event}\n\nHUMAN_INPUT: The scene begins."
            
            # --- Dialogue Loop for the Event ---
            user_input = initial_event_prompt
            
            while True:
                # 1) Call DeepSeek with the current context
                reply = call_deepseek_with_context(client, current_system_prompt, context_manager.get_stage_history(), user_input)
                
                tags, clean_text = extract_motion_tags_and_clean_text(reply)
                
                # 2) Add messages to context AFTER the call
                context_manager.add_message('user', user_input)
                context_manager.add_message('assistant', clean_text) # Use 'assistant' role for NAO's response
                
                # 3) Execute NAO's action
                print(f"[NAO] {reply}")
                motion_controller.speak_text(clean_text, emotion_tag=next(iter(tags), "neutral"))
                motion_controller.play_for_emotions(tags)
                
                # 4) Get next user input
                try:
                    user_input = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    user_input = "quit"

                # 5) Handle special commands
                if user_input.lower() == "quit":
                    if is_last_event:
                        print("[INFO] Last event of the stage is over. Robot will be static.")
                        break
                    else:
                        print("[INFO] Quitting event. Moving to new position.")
                        basic_motion.change_position()
                        break
                
                if not user_input:
                    continue
            
            if user_input.lower() == "quit" and is_last_event:
                break
        
        # --- End of Stage ---
        print(f"\n--- End of Stage: {stage} ---")
        # Summarize and determine the style for the *next* stage.
        next_style = context_manager.summarize_and_determine_next_style(client, nao_attachment_style)
        nao_attachment_style = next_style # Update for the next iteration
        
        if stage != LIFE_STAGES[-1]:
            while input("Type 'next' to continue to the next stage: ").strip().lower() != 'next':
                pass

    print("\n--- Performance Finished ---")


if __name__ == "__main__":
    main()