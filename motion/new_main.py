# main.py
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import time
from typing import Set, Tuple, Optional, Dict, List

from openai import OpenAI
from dotenv import load_dotenv

# Import the provided motion controller
from motion_controller import EmotionMotionController

# -----------------------------
# Configuration & File Paths
# -----------------------------

# Mapping stage names to the uploaded JSON filenames
JSON_FILES = {
    "baby": {
        "behaviour": "/home/urchin/Documents/Projects/sir-project-group-9/llm_prompts/behaviour/baby_behaviour.json",
        "description": "/home/urchin/Documents/Projects/sir-project-group-9/llm_prompts/description/baby_description.json"
    },
    "child": {
        "behaviour": "/home/urchin/Documents/Projects/sir-project-group-9/llm_prompts/behaviour/child_behaviour.json",
        # Note: Preserving the typo 'desription' found in your uploaded file name
        "description": "/home/urchin/Documents/Projects/sir-project-group-9/llm_prompts/description/child_desription.json" 
    },
    "teen": {
        "behaviour": "/home/urchin/Documents/Projects/sir-project-group-9/llm_prompts/behaviour/teen_behaviour.json",
        "description": "/home/urchin/Documents/Projects/sir-project-group-9/llm_prompts/description/teen_description.json"
    }
}

# -----------------------------
# System Prompts
# -----------------------------

# Technical prompt: Tells the robot how to use [tags] for motion and gestures
MOTION_SYSTEM_PROMPT = """
You control a NAO social robot. Your goal is to roleplay a specific life stage (Baby, Child, or Teen) while acting out emotions physically.

To express yourself, you must use MOTION TAGS in square brackets at the start of your response.
The robot software parses these tags to trigger animations and voice intonations.

FORMAT:
[motion_tag] Your spoken response here.

AVAILABLE EMOTION TAGS (Use for tone/mood):
[angry], [anxious], [bored], [disappointed], [exhausted], [fear], 
[fearful], [frustrated], [humiliated], [hurt], [late], [sad], 
[shocked], [sorry], [surprise], [neutral]

AVAILABLE GESTURE TAGS (Use for specific actions):
[gesture_hey] (greeting), [gesture_bow], [gesture_yes], [gesture_no], 
[gesture_calm_down], [gesture_confused], [gesture_desperate], 
[gesture_dont_understand], [gesture_enthusiastic], [gesture_everything], 
[gesture_excited], [gesture_explain], [gesture_far], [gesture_follow], 
[gesture_give], [gesture_great], [gesture_he_says], [gesture_idontknow], 
[gesture_me], [gesture_you], [gesture_please], [gesture_you_know_what], 
[gesture_count], [gesture_come_on], [gesture_choice]

GUIDELINES:
1. Choose ONE tag that best fits the emotion or action of the scene.
2. If no strong emotion is needed, use [neutral].
3. Do NOT explain the tag, just output it.
4. Keep your spoken response consistent with the restrictions of the life stage (e.g., a baby speaks in single words, a teen acts rebellious).
"""

# -----------------------------
# Regex for motion tags
# -----------------------------

MOTION_TAG_PATTERN = re.compile(r"\[(?P<tag>[a-zA-Z_]+)\]")

# -----------------------------
# Helper Functions
# -----------------------------

def create_openai_client() -> OpenAI:
    """
    Create a standard OpenAI client.
    Ensures OPENAI_API_KEY is loaded from environment or .env file.
    """
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY not found in environment variables or .env file.")
        print("Please create a .env file with: OPENAI_API_KEY=sk-...")
        sys.exit(1)

    # Standard OpenAI client
    return OpenAI(api_key=api_key)


def load_json_data(stage_name: str) -> Tuple[Dict, Dict]:
    """
    Load the behaviour and description JSON files for a specific stage.
    """
    paths = JSON_FILES.get(stage_name)
    if not paths:
        return {}, {}

    beh_file = paths["behaviour"]
    desc_file = paths["description"]

    try:
        if not os.path.exists(beh_file) or not os.path.exists(desc_file):
            print(f"[ERROR] Missing JSON files for {stage_name}: {beh_file} or {desc_file}")
            return {}, {}

        with open(beh_file, 'r', encoding='utf-8') as f:
            b_data = json.load(f)
        with open(desc_file, 'r', encoding='utf-8') as f:
            d_data = json.load(f)
        return b_data, d_data
        
    except Exception as e:
        print(f"[ERROR] Failed to load JSON for stage '{stage_name}': {e}")
        return {}, {}


def extract_motion_tags_and_clean_text(raw_text: str) -> Tuple[Set[str], str]:
    """
    Parses '[angry] Hello' into ({'angry'}, 'Hello').
    """
    tags: Set[str] = set()

    def _collect(match: re.Match) -> str:
        tag = match.group("tag").strip().lower()
        if tag:
            tags.add(tag)
        return "" # Remove tag from spoken text

    clean_text = MOTION_TAG_PATTERN.sub(_collect, raw_text)
    clean_text = clean_text.strip()
    return tags, clean_text


def construct_base_system_prompt(motion_instructions: str, event_template: str, scene_context: str, life_memory: str) -> str:
    """
    Creates the initial system message for the chat history.
    """
    # 1. Inject the specific scene description
    scenario_prompt = re.sub(r"\{\{.*?DESCRIPTION\}\}", scene_context, event_template)
    
    # 2. Add life memory context
    memory_str = life_memory if life_memory else "(none yet)"
    scenario_prompt = scenario_prompt.replace("(none yet)", memory_str)

    # 3. Combine with motion instructions
    full_system_prompt = (
        f"{motion_instructions}\n\n"
        f"--- CURRENT SCENE CONTEXT ---\n"
        f"{scenario_prompt}\n"
    )
    return full_system_prompt

# -----------------------------
# Main Application
# -----------------------------

def main() -> None:
    client = create_openai_client()
    motion_controller = EmotionMotionController()

    print("\n=== OPENAI GPT + NAO ROBOT SIMULATION (Multi-turn) ===")
    if motion_controller.is_real_robot_available():
        print("[INFO] Connected to REAL NAO Robot.")
    else:
        print("[INFO] No robot found. Running in SIMULATION mode (text only).")

    # 1. Load Initial Data to find Roles
    print("\n[INFO] Loading initial configuration...")
    b_data, d_data = load_json_data("baby")
    if not d_data:
        print("[CRITICAL] Could not load configuration. Exiting.")
        return

    # 2. Parent Role Selection
    print("\n--- SELECT PARENT ROLE ---")
    available_roles = [k for k in d_data.keys() if k.startswith("parent")]
    if not available_roles: 
        available_roles = ["parent_artist", "parent_businessman", "parent_unstable"]

    for idx, role in enumerate(available_roles):
        print(f"{idx + 1}. {role}")
    
    parent_role = available_roles[0] # Default
    while True:
        selection = input("Enter number: ").strip()
        if selection.isdigit():
            idx = int(selection) - 1
            if 0 <= idx < len(available_roles):
                parent_role = available_roles[idx]
                break
        print("Invalid selection, please try again.")
    
    print(f"Selected: {parent_role}")

    # 3. Life Stages Loop
    stages = ["baby", "child", "teen"]
    life_memory_log = [] 

    for stage_name in stages:
        print(f"\n\n{'#'*40}")
        print(f"ENTERING LIFE STAGE: {stage_name.upper()}")
        print(f"{'#'*40}")

        beh_data, desc_data = load_json_data(stage_name)
        if not beh_data:
            continue
        
        events_map = beh_data.get(stage_name, {}).get("events", {})
        
        for event_key, event_info in events_map.items():
            print(f"\n--- Scene: {event_key} ---")
            
            # Determine Scene Description
            try:
                scene_description = desc_data[parent_role][stage_name][event_key]
            except KeyError:
                try:
                    scene_description = desc_data[parent_role][event_key]
                except KeyError:
                    scene_description = event_info.get("description", "Interaction with parent.")

            print(f"[Situation]: {scene_description}")
            print(f"[Action]: You are the {parent_role}. Start the conversation.")
            
            # --- START OF EVENT CONVERSATION LOOP ---
            
            # Initialize Chat History for this event
            prompt_template = event_info.get("user_prompt_template", "")
            base_system_prompt = construct_base_system_prompt(
                MOTION_SYSTEM_PROMPT,
                prompt_template,
                scene_description,
                str(life_memory_log)
            )
            
            messages = [{"role": "system", "content": base_system_prompt}]
            
            # Flag to control the conversation loop
            event_active = True
            
            while event_active:
                # A. Get User Dialogue
                user_dialogue = input("\nYou (Dialogue): ").strip()
                if not user_dialogue:
                    print("Please say something.")
                    continue
                    
                if user_dialogue.lower() in ["quit", "exit"]:
                    print("Exiting simulation.")
                    return

                # Add user message to history
                messages.append({"role": "user", "content": user_dialogue})

                # B. Call LLM
                print("[Thinking] ...")
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o", 
                        messages=messages,
                        temperature=0.7,
                        max_tokens=100
                    )
                    robot_reply_raw = response.choices[0].message.content
                except Exception as e:
                    print(f"[ERROR] OpenAI API Error: {e}")
                    break

                # C. Process and Perform Robot Response
                tags, spoken_text = extract_motion_tags_and_clean_text(robot_reply_raw)
                messages.append({"role": "assistant", "content": robot_reply_raw}) # Save full response to history

                print(f"NAO: {spoken_text}")
                
                # Determine emotion for TTS
                primary_emotion = "neutral"
                for t in tags:
                    if not t.startswith("gesture_") and t != "neutral":
                        primary_emotion = t
                        break

                motion_controller.speak_text(spoken_text, emotion_tag=primary_emotion)
                motion_controller.play_for_emotions(tags)

                # D. Control Step: Continue or Wrap Up?
                while True:
                    control_input = input(">> Enter '0' to continue, '1' to wrap up: ").strip()
                    if control_input == '0':
                        # Continue conversation loop
                        break 
                    elif control_input == '1':
                        # Trigger Wrap Up
                        print("[System] Wrapping up event...")
                        
                        # Add a system instruction to force a conclusion
                        wrap_msg = "The user is ending the interaction. Provide a brief concluding remark consistent with your role and emotion to finish the scene."
                        messages.append({"role": "system", "content": wrap_msg})
                        
                        try:
                            # One final generation for the closing remark
                            final_resp = client.chat.completions.create(
                                model="gpt-4o",
                                messages=messages,
                                temperature=0.7,
                                max_tokens=60
                            )
                            final_raw = final_resp.choices[0].message.content
                            f_tags, f_spoken = extract_motion_tags_and_clean_text(final_raw)
                            
                            print(f"NAO (Closing): {f_spoken}")
                            
                            motion_controller.speak_text(f_spoken, emotion_tag="neutral")
                            motion_controller.play_for_emotions(f_tags)
                            
                            # Save interaction summary to life memory
                            # We summarize the last assistant message as the result
                            life_memory_log.append(f"Stage: {stage_name} | Event: {event_key} | Result: Interaction completed.")
                            
                        except Exception as e:
                            print(f"[ERROR] Failed to wrap up: {e}")

                        # End the While Loop for this event
                        event_active = False 
                        break
                    else:
                        print("Invalid input. Please enter 0 or 1.")
            
            # --- END OF EVENT LOOP ---
            time.sleep(1.0)

    print("\n=== Simulation Complete ===")
    print("Final Life Memory:")
    for mem in life_memory_log:
        print(f"- {mem}")

if __name__ == "__main__":
    main()