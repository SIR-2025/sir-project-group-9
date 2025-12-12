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
from stt_whisper_direct import VADWhisperSTT

# -----------------------------
# Configuration & File Paths
# -----------------------------

# Mapping stage names to the uploaded JSON filenames
JSON_FILES = {
    "baby": {
        "behaviour": r"D:\\研二\\代码文件\\SIC\\sir-project-group-9\\llm_prompts\\behaviour\\baby_behaviour.json",
        "description": r"D:\\研二\\代码文件\\SIC\\sir-project-group-9\\llm_prompts\\description\\baby_description.json"
    },
    "child": {
        "behaviour": r"D:\\研二\\代码文件\\SIC\\sir-project-group-9\\llm_prompts\\behaviour\\child_behaviour.json",
        # Note: Preserving the typo 'desription' found in your uploaded file name
        "description": r"D:\\研二\\代码文件\\SIC\\sir-project-group-9\\llm_prompts\\description\\child_desription.json" 
    },
    "teen": {
        "behaviour": r"D:\\研二\\代码文件\\SIC\\sir-project-group-9\\llm_prompts\\behaviour\\teen_behaviour.json",
        "description": r"D:\\研二\\代码文件\\SIC\\sir-project-group-9\\llm_prompts\\description\\teen_description.json"
    },
    "adult": {
        "behaviour": r"D:\\研二\\代码文件\\SIC\\sir-project-group-9\\llm_prompts\\behaviour\\adult_behaviour.json",
        "description": r"D:\\研二\\代码文件\\SIC\\sir-project-group-9\\llm_prompts\\description\\adult_description.json"
    },
    "elderly": {
        "behaviour": r"D:\\研二\\代码文件\\SIC\\sir-project-group-9\\llm_prompts\\behaviour\\elderly_behaviour.json",
        "description": r"D:\\研二\\代码文件\\SIC\\sir-project-group-9\\llm_prompts\\description\\elderly_description.json"
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

# Specialized prompt for the Baby stage
BABY_MOTION_SYSTEM_PROMPT = """
You are roleplaying as a BABY controlling a NAO robot. You can only express basic emotions.

To express how you feel, you MUST use ONE of the following MOTION TAGS at the start of your response.

FORMAT:
[motion_tag] Your spoken response (usually just one or two simple words).

AVAILABLE EMOTION TAGS:
[Fear]
[Hurt]
[Sad]
[Excited]
[neutral] (Use this if you are calm or just observing)

GUIDELINES:
1. CHOOSE ONLY ONE TAG from the list above.
2. Your spoken words should be very simple, like "Mama," "Dada," "toy," "no," "want."
3. Do NOT use any other tags or gestures.
"""

# -----------------------------
# Regex for motion tags
# -----------------------------

MOTION_TAG_PATTERN = re.compile(r"""\[(?P<tag>[a-zA-Z_]+)\]""")

# -----------------------------
# Helper Functions
# -----------------------------

def create_openai_client() -> OpenAI:
    """
    Create a standard OpenAI client.
    Ensures OPENAI_API_KEY is loaded from environment or .env file.
    """
    load_dotenv()
    
    api_key = ""
    #if not api_key:
    #    print("[ERROR] OPENAI_API_KEY not found in environment variables or .env file.")
    #    print("Please create a .env file with: OPENAI_API_KEY=sk-...")
    #    sys.exit(1)

    # Standard OpenAI client
    return OpenAI(api_key="",
                  )


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


def collect_roles_by_type(desc_sources: List[Dict], role_type: str) -> List[str]:
    """
    Collect distinct role names from multiple description dicts by type.
    role_type: 'parent', 'teacher', 'peer', 'therapist', or 'caregiver'.
    """
    roles: List[str] = []

    def _match(name: str) -> bool:
        lowered = name.lower()
        if role_type == "parent":
            return lowered.startswith("parent")
        if role_type == "teacher":
            return "teacher" in lowered
        if role_type == "peer":
            return "peer" in lowered
        if role_type == "therapist":
            return "therapist" in lowered
        if role_type == "caregiver":
            return "caregiver" in lowered
        return False

    for data in desc_sources:
        for key in data.keys():
            if _match(key) and key not in roles:
                roles.append(key)
    return roles


def prompt_role_selection(role_label: str, available_roles: List[str]) -> str:
    """
    Prompt the user to choose a role from the provided list.
    Returns the selected role name.
    """
    if not available_roles:
        print(f"[WARN] No roles found for {role_label}. Using default '{role_label}_default'.")
        return f"{role_label}_default"

    print(f"\n--- SELECT {role_label.upper()} ROLE ---")
    for idx, role in enumerate(available_roles):
        print(f"{idx + 1}. {role}")

    selected = available_roles[0]
    while True:
        selection = input("Enter number: ").strip()
        if selection.isdigit():
            idx = int(selection) - 1
            if 0 <= idx < len(available_roles):
                selected = available_roles[idx]
                break
        print("Invalid selection, please try again.")

    print(f"Selected {role_label}: {selected}")
    return selected


def pick_role_for_event(stage_name: str, event_key: str, parent_role: str, teacher_role: str, peer_role: str, therapist_role: str, caregiver_role: str) -> str:
    """
    Choose which role persona to inject for the given stage/event.
    """
    if stage_name == "baby":
        return parent_role

    if stage_name == "child":
        if event_key == "learning_with_teacher":
            return teacher_role
        if event_key == "peer_interaction":
            return peer_role
        # Default to parent for other child events
        return parent_role

    if stage_name == "teen":
        if event_key == "peer_conflict":
            return peer_role
        return parent_role

    if stage_name == "adult":
        return therapist_role or parent_role

    if stage_name == "elderly":
        return caregiver_role or parent_role

    return parent_role


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


SPEAKING_STYLE = {
    "baby": (
        "SPEAKING STYLE (BABY): Babbling, syllables, simple words like 'up' or 'mom'. "
        "No full sentences."
    ),
    "child": (
        "SPEAKING STYLE (CHILD): Short, concrete sentences. Tone depends on BABY_MEMORY: "
        "warm/consistent care -> more trusting and open; distant/chaotic care -> more cautious, clingy, or avoidant. "
        "Child still reacts to the current scene but subtle patterns from BABY_MEMORY influence tone and how quickly trust or withdrawal happens."
    ),
    "teen": (
        "SPEAKING STYLE (TEEN): Emotional, casual, may include light cursing/vulgarisms, sometimes defensive or sarcastic. "
        "Use BABY_MEMORY and CHILD_MEMORY: stable care -> more secure/open (though frustrated at times); inconsistent/rejecting care -> more reactive, dramatic, push–pull, afraid of rejection, or shutting down. "
        "Teen reactions should feel like a continuation of earlier patterns, voiced in adolescent language."
    ),
    "adult": (
        "SPEAKING STYLE (ADULT): Reflective, coherent sentences. Use all prior MEMORY to explain how childhood/teen shaped adult relationships, work, and attachment patterns."
    ),
    "elderly": (
        "SPEAKING STYLE (ELDERLY): Slow, heartfelt reflection. Use all MEMORY to express regrets, longings, meaning, and nearing shutdown."
    ),
}


def construct_base_system_prompt(stage_name: str, motion_instructions: str, event_template: str, scene_context: str, life_memory: str) -> str:
    """
    Creates the initial system message for the chat history.
    """
    # 1. Inject the specific scene description
    scenario_prompt = re.sub(r"""\{\{.*?DESCRIPTION\}\}""", scene_context, event_template)
    
    # 2. Add life memory context
    memory_str = life_memory if life_memory else "(none yet)"
    scenario_prompt = scenario_prompt.replace("(none yet)", memory_str)

    # 3. Combine with motion instructions
    style = SPEAKING_STYLE.get(stage_name, "")
    full_system_prompt = (
        f"{motion_instructions}\n\n"
        f"{style}\n\n"
        f"--- CURRENT SCENE CONTEXT ---"
        f"{scenario_prompt}\n"
    )
    return full_system_prompt

# -----------------------------
# Main Application
# -----------------------------

def main() -> None:
    client = create_openai_client()
    motion_controller = EmotionMotionController()
    stt_controller = VADWhisperSTT(client=client) # Initialize STT controller

    # Pre-warm LLM to reduce first-turn latency
    try:
        print("[INFO] Warming up LLM for faster first response...")
        _ = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": "Warmup ping for latency reduction."},
                      {"role": "user", "content": "Say OK."}],
            max_tokens=4,
            temperature=0.0
        )
    except Exception as warm_err:  # pylint: disable=broad-except
        print(f"[WARN] LLM warmup skipped due to error: {warm_err}")

    print("\n=== OPENAI GPT + NAO ROBOT SIMULATION (Multi-turn) ===")
    if motion_controller.is_real_robot_available():
        print("[INFO] Connected to REAL NAO Robot.")
    else:
        print("[INFO] No robot found. Running in SIMULATION mode (text only).")

    # 1. Load Initial Data to find Roles
    print("\n[INFO] Loading initial configuration...")
    b_data, d_data = load_json_data("baby")
    child_behaviour, child_desc = load_json_data("child")
    teen_behaviour, teen_desc = load_json_data("teen")

    if not d_data:
        print("[CRITICAL] Could not load configuration. Exiting.")
        return

    # 2. Role Selection
    role_sources = [d_data, child_desc, teen_desc]
    adult_desc = load_json_data("adult")[1]
    elderly_desc = load_json_data("elderly")[1]
    role_sources.extend([adult_desc, elderly_desc])
    parent_options = collect_roles_by_type(role_sources, "parent")
    teacher_options = collect_roles_by_type(role_sources, "teacher")
    peer_options = collect_roles_by_type(role_sources, "peer")
    allowed_peers = {"bully_peer", "ignoring_peer", "friend_peer"}
    peer_options = [p for p in peer_options if p in allowed_peers] or list(allowed_peers)
    therapist_options = collect_roles_by_type(role_sources, "therapist")
    caregiver_options = collect_roles_by_type(role_sources, "caregiver")

    parent_role = prompt_role_selection("parent", parent_options)
    teacher_role = prompt_role_selection("teacher", teacher_options)
    peer_role = prompt_role_selection("peer", peer_options)
    therapist_role = prompt_role_selection("therapist", therapist_options)
    caregiver_role = prompt_role_selection("caregiver", caregiver_options)

    # 3. Pre-performance Menu
    while True:
        print("\n--- CHOOSE AN ACTION ---")
        print("1. Self-introduction and performance introduction")
        print("0. Start performance")
        choice = input("Enter number: ").strip()

        if choice == '1':
            intro_text = "Hi I’m Nao, the parent simulation device that makes you go wow. Traumatize me, so your kids don't have to be."

            print(f"NAO (Intro): {intro_text}")
            motion_controller.play_for_emotions({'gesture_hey'}) # Perform greeting
            motion_controller.speak_text(intro_text, block=True) # Speak and wait
            print("[System] Introduction finished.")
        
        elif choice == '0':
            print("[System] Starting performance...")
            break # Exit menu and start the main loop
        
        else:
            print("Invalid selection. Please enter 0 or 1.")


    # 4. Select starting life stage (then continue sequentially)
    stages = ["baby", "child", "teen", "adult", "elderly"]
    print("\n--- SELECT STARTING LIFE STAGE ---")
    for idx, stg in enumerate(stages):
        print(f"{idx + 1}. {stg}")

    start_stage = stages[0]
    while True:
        sel = input("Enter number to choose starting stage: ").strip()
        if sel.isdigit():
            idx = int(sel) - 1
            if 0 <= idx < len(stages):
                start_stage = stages[idx]
                break
        print("Invalid selection, please try again.")

    start_index = stages.index(start_stage)
    print(f"[System] Performance will start from: {start_stage.upper()}")

    # 5. Life Stages Loop
    life_memory_log = [] 

    for stage_name in stages[start_index:]:
        print(f"\n\n{'#'*40}")
        print(f"ENTERING LIFE STAGE: {stage_name.upper()}")
        print(f"{'#'*40}")

        beh_data, desc_data = load_json_data(stage_name)
        if not beh_data:
            continue

        # Stage posture management at entry
        if stage_name == "baby":
            motion_controller.go_to_crouch()
        elif stage_name == "adult":
            motion_controller.go_to_lying_back()
        elif stage_name == "elderly":
            motion_controller.go_to_sit_relax()

        # Preview full stage prompt for transparency
        stage_motion_prompt = (
            BABY_MOTION_SYSTEM_PROMPT if stage_name == "baby" else MOTION_SYSTEM_PROMPT
        )
        print("\n--- FULL STAGE PROMPT ---")
        print(stage_motion_prompt)
        print("--- END STAGE PROMPT ---\n")
        
        events_map = beh_data.get(stage_name, {}).get("events", {})
        event_items = list(events_map.items())
        
        force_stage_end = False

        for event_idx, (event_key, event_info) in enumerate(event_items):
            is_last_event = event_idx == len(event_items) - 1
            if stage_name == "baby" and event_key == "first_words":
                # Treat first_words as the final baby event
                is_last_event = True
                force_stage_end = True
            print(f"\n--- Scene: {event_key} ---")
            
            # Determine Scene Description
            role_for_scene = pick_role_for_event(stage_name, event_key, parent_role, teacher_role, peer_role, therapist_role, caregiver_role)
            scene_description = event_info.get("description", "Interaction.")
            role_block = desc_data.get(role_for_scene, {})

            if isinstance(role_block, dict):
                try:
                    scene_description = role_block[stage_name][event_key]
                except Exception:
                    scene_description = role_block.get(event_key, scene_description)

            print(f"[Situation]: {scene_description}")
            print(f"[Role in use]: {role_for_scene}")
            print(f"[Action]: You are the {role_for_scene}. Start the conversation.")
            
            # --- START OF EVENT CONVERSATION LOOP ---
            
            # Initialize Chat History for this event
            prompt_template = event_info.get("user_prompt_template", "")
            
            # Select the appropriate motion prompt based on the stage
            current_motion_prompt = (
                BABY_MOTION_SYSTEM_PROMPT 
                if stage_name == "baby" 
                else MOTION_SYSTEM_PROMPT
            )
            
            base_system_prompt = construct_base_system_prompt(
                stage_name,
                current_motion_prompt,
                prompt_template,
                scene_description,
                str(life_memory_log)
            )
            
            messages = [{"role": "system", "content": base_system_prompt}]

            # Robot opens the scene with a first line
            opening_instruction = {
                "role": "system",
                "content": "Begin this scene with a brief opening line before the user speaks. Use exactly one motion tag as the first token."
            }
            # If child stage, inject salutation reference
            if stage_name == "child":
                if event_key == "school_day":
                    opening_instruction["content"] += " Mention mom in this first line."
                elif event_key == "learning_with_teacher":
                    opening_instruction["content"] += " Mention teacher in this first line."
            messages.append(opening_instruction)

            try:
                opening_resp = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=200
                )
                opening_raw = opening_resp.choices[0].message.content
                messages.append({"role": "assistant", "content": opening_raw})

                o_tags, o_spoken = extract_motion_tags_and_clean_text(opening_raw)
                print(f"NAO (Opener): {o_spoken}")

                opener_primary_emotion = "neutral"
                for t in o_tags:
                    if not t.startswith("gesture_") and t != "neutral":
                        opener_primary_emotion = t
                        break
                motion_controller.speak_text(o_spoken, emotion_tag=opener_primary_emotion)
                try:
                    motion_controller.play_for_emotions(o_tags)
                except Exception as motion_err:  # pylint: disable=broad-except
                    print(f"[MOTION] Skipped opener motion due to error: {motion_err}")
                if stage_name == "baby":
                    motion_controller.go_to_crouch()
                elif stage_name == "adult":
                    motion_controller.go_to_lying_back()
                elif stage_name == "elderly":
                    motion_controller.go_to_sit_relax()
            except Exception as e:
                print(f"[ERROR] Failed to generate opening line: {e}")
            
            # Flag to control the conversation loop
            event_active = True
            
            while event_active:
                # A. Get User Dialogue via STT
                print("\nYou (Speak now):")
                user_dialogue = stt_controller.listen_and_transcribe()
                
                if not user_dialogue:
                    print("Could not hear anything. Please try again.")
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
                        model="gpt-4o", ###############################################################################################
                        #model = "deepseek-chat",
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1000
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
                try:
                    motion_controller.play_for_emotions(tags)
                except Exception as motion_err:  # pylint: disable=broad-except
                    print(f"[MOTION] Skipped motion due to error: {motion_err}")
                if stage_name == "baby":
                    motion_controller.go_to_crouch()
                elif stage_name == "adult":
                    motion_controller.go_to_lying_back()
                elif stage_name == "elderly":
                    motion_controller.go_to_sit_relax()

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
                                model="gpt-4o",####################################################################################################################################
                                #model = "deepseek-chat",
                                messages=messages,
                                temperature=0.7,
                                max_tokens=60
                            )
                            final_raw = final_resp.choices[0].message.content
                            f_tags, f_spoken = extract_motion_tags_and_clean_text(final_raw)
                            
                            print(f"NAO (Closing): {f_spoken}")
                            
                            # Make this call blocking to wait for speech to finish
                            motion_controller.speak_text(f_spoken, emotion_tag="neutral", block=True)
                            try:
                                motion_controller.play_for_emotions(f_tags)
                            except Exception as motion_err:  # pylint: disable=broad-except
                                print(f"[MOTION] Skipped closing motion due to error: {motion_err}")
                            if stage_name == "baby":
                                motion_controller.go_to_crouch()
                            elif stage_name == "adult":
                                # During adult stage keep lying, but after the final event we will stand.
                                if is_last_event:
                                    motion_controller.go_to_stand()
                                else:
                                    motion_controller.go_to_lying_back()
                            elif stage_name == "elderly":
                                # For elderly, stay low; final shutdown will move to LyingBelly.
                                pass

                            # Wait for speech to finish, then perform the final action
                            print("[System] Wrap-up speech finished. Performing final action.")
                            try:
                                if stage_name == "elderly" and is_last_event:
                                    motion_controller.perform_elderly_shutdown()
                                elif stage_name == "baby":
                                    # Always spin for baby stage transitions
                                    motion_controller.perform_wrap_up_action(use_spin=True)
                                else:
                                    motion_controller.perform_wrap_up_action(use_spin=is_last_event)
                            except Exception as motion_err:  # pylint: disable=broad-except
                                print(f"[MOTION] Skipped wrap-up action due to error: {motion_err}")
                            if stage_name == "baby":
                                motion_controller.go_to_crouch()
                            elif stage_name == "adult":
                                if is_last_event:
                                    motion_controller.go_to_stand()
                                else:
                                    motion_controller.go_to_lying_back()
                            elif stage_name == "elderly":
                                # After final shutdown, remain in LyingBelly; do not reset to sit or stand.
                                pass

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
            if force_stage_end:
                break

    print("\n=== Simulation Complete ===")
    print("Final Life Memory:")
    for mem in life_memory_log:
        print(f"- {mem}")

if __name__ == "__main__":
    main()
