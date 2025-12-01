# main.py
# -*- coding: utf-8 -*-

import os
import re
import sys
from typing import Set, Tuple, Optional

from openai import OpenAI

from motion_controller import EmotionMotionController


# -----------------------------
# System prompt for DeepSeek
# -----------------------------

SYSTEM_PROMPT = """
You control a NAO social robot that can express itself with:
1) facial/body emotion animations, and
2) communicative gestures.

The robot's software will parse MOTION TAGS that you put in square brackets, then:
- use them to trigger NAO animation sequences, and
- optionally drive the tone of the text-to-speech (TTS).

------------------------------
MOTION TAG FORMAT
------------------------------
- Motion tags MUST be lowercase and contain only letters and underscores.
- They MUST be enclosed in square brackets, e.g. [angry], [sad], [gesture_hey].
- In each reply, you SHOULD put exactly ONE motion tag at the very beginning of the answer,
  then a space, then the actual sentence.

Examples of valid reply formats:
  [angry] I can't believe you did that!
  [sad] I am really sorry to hear that.
  [gesture_hey] Hey there, over here!
  [neutral] Sure, I can help you with that.

------------------------------
AVAILABLE EMOTION TAGS
------------------------------
These tags map to NAO's negative emotion animations under:
  animations/Stand/Emotions/Negative

Use them when the overall emotional tone of your reply matches the tag:

  [angry]       -> Angry_1 .. Angry_4
  [anxious]     -> Anxious_1
  [bored]       -> Bored_1 .. Bored_2
  [disappointed]-> Disappointed_1
  [exhausted]   -> Exhausted_1 .. Exhausted_2
  [fear]        -> Fear_1 .. Fear_2
  [fearful]     -> Fearful_1
  [frustrated]  -> Frustrated_1
  [humiliated]  -> Humiliated_1
  [hurt]        -> Hurt_1 .. Hurt_2
  [late]        -> Late_1
  [sad]         -> Sad_1 .. Sad_2
  [shocked]     -> Shocked_1
  [sorry]       -> Sorry_1
  [surprise]    -> Surprise_1 .. Surprise_3

If none of these emotions apply, use:
  [neutral]

------------------------------
AVAILABLE GESTURE TAGS
------------------------------
These tags map to NAO's gesture animations under:
  animations/Stand/Gestures

Use them when you want to add a communicative gesture, without necessarily
changing the emotional tone of the voice.

Examples:

  [gesture_angry]      -> Angry_* (gestures)
  [gesture_hey]        -> Hey_1, Hey_6 (calling attention)
  [gesture_bow]        -> BowShort_1 .. BowShort_3 (small bow)
  [gesture_yes]        -> Yes_1 .. Yes_3 (nodding)
  [gesture_no]         -> No_3, No_8, No_9 (shaking head)
  [gesture_calm_down]  -> CalmDown_* (calming the user)
  [gesture_confused]   -> Confused_1, Confused_2
  [gesture_desperate]  -> Desperate_1 .. Desperate_5
  [gesture_dont_understand] -> DontUnderstand_1
  [gesture_enthusiastic]    -> Enthusiastic_3 .. Enthusiastic_5
  [gesture_everything]      -> Everything_1 .. Everything_4, Everything_6
  [gesture_excited]         -> Excited_1
  [gesture_explain]         -> Explain_1 .. Explain_8, Explain_10, Explain_11
  [gesture_far]             -> Far_1 .. Far_3
  [gesture_follow]          -> Follow_1
  [gesture_give]            -> Give_1 .. Give_6
  [gesture_great]           -> Great_1
  [gesture_he_says]         -> HeSays_1 .. HeSays_3
  [gesture_idontknow]       -> IDontKnow_1, IDontKnow_2
  [gesture_me]              -> Me_1, Me_2
  [gesture_you]             -> You_1, You_4
  [gesture_please]          -> Please_1
  [gesture_you_know_what]   -> YouKnowWhat_1, YouKnowWhat_5
  [gesture_count]           -> CountOne_1, CountTwo_1, CountThree_1, CountFour_1, CountFive_1, CountMore_1
  [gesture_come_on]         -> ComeOn_1
  [gesture_choice]          -> Choice_1

You do NOT need to output the full animation path; only the tag in brackets.

------------------------------
HOW TO CHOOSE TAGS
------------------------------
- Always think about the user's emotional state and the social context.
- If the main purpose is to express emotion (angry, sad, sorry...), choose an EMOTION TAG.
- If the main purpose is to accompany neutral speech with a communicative gesture
  (e.g. greeting, bowing, counting, pointing at "you" or "me"), choose a GESTURE TAG.
- If no specific emotion or gesture is needed, use [neutral].

------------------------------
LANGUAGE AND CONTENT
------------------------------
- Speak naturally and politely.
- You may answer in English or Chinese depending on the user's language.
- Do NOT explain the tags themselves; just use them silently.
"""


# -----------------------------
# Regex for motion tags
# -----------------------------

MOTION_TAG_PATTERN = re.compile(r"\[(?P<tag>[a-zA-Z_]+)\]")


# -----------------------------
# DeepSeek related functions
# -----------------------------

def create_deepseek_client() -> OpenAI:
    """
    Create an OpenAI-compatible client configured for DeepSeek API.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("[ERROR] Environment variable DEEPSEEK_API_KEY is not set.")
        sys.exit(1)

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )
    return client


def call_deepseek(client: OpenAI, user_input: str) -> str:
    """
    Call DeepSeek chat completion API and return the assistant text.
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        stream=False,
    )

    if not response.choices:
        return ""

    return response.choices[0].message.content


# -----------------------------
# Motion tag processing
# -----------------------------

def extract_motion_tags_and_clean_text(raw_text: str) -> Tuple[Set[str], str]:
    """
    Extract motion tags like [angry], [gesture_hey] from the text and return:
    - a set of tag names (lowercased)
    - the text with all motion tags removed (for TTS output)
    """
    tags: Set[str] = set()

    def _collect(match: re.Match) -> str:
        tag = match.group("tag").strip().lower()
        if tag:
            tags.add(tag)
        # Remove the tag from the final text.
        return ""

    clean_text = MOTION_TAG_PATTERN.sub(_collect, raw_text)
    clean_text = clean_text.strip()
    return tags, clean_text


# -----------------------------
# Main CLI loop
# -----------------------------

def main() -> None:
    """
    Main entry point:
    1. Read user input from terminal.
    2. Send it to DeepSeek with a motion-aware system prompt.
    3. On response:
       - Extract motion tags using regex.
       - Use EmotionMotionController.speak_text() for real TTS.
       - Use EmotionMotionController.play_for_emotions() for NAO animations.
    """
    client = create_deepseek_client()

    # Initialize emotion + motion controller (will try NAO_IP or simulation)
    motion_controller = EmotionMotionController()

    print("DeepSeek CLI demo with NAO TTS + NAO motion animations.")
    print("Environment variables used:")
    print("  - DEEPSEEK_API_KEY: DeepSeek API key (required)")
    print("  - NAO_IP: NAO robot IP (optional, for real robot animations + TTS)")
    print("")
    if motion_controller.is_real_robot_available():
        print("[INFO] Real NAO robot is available. Animations and TTS will be executed.")
    else:
        print("[INFO] No real NAO robot. Running in simulation mode.")
    print("\nType your message and press Enter.")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[INFO] Exiting.")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("[INFO] Bye.")
            break

        # 1) Call DeepSeek
        reply = call_deepseek(client, user_input)
        if not reply:
            print("[WARN] Empty response from DeepSeek.")
            continue

        print(f"DeepSeek (raw): {reply}")

        # 2) Extract motion tags and clean text
        tags, clean_text = extract_motion_tags_and_clean_text(reply)

        # Choose primary tag for TTS: prefer non-gesture, non-neutral tags.
        primary_vocal_tag: Optional[str] = None
        for t in tags:
            if t.startswith("gesture_"):
                continue
            if t == "neutral":
                continue
            primary_vocal_tag = t
            break

        # 3) Use real TTS via EmotionMotionController
        motion_controller.speak_text(clean_text, emotion_tag=primary_vocal_tag)

        # 4) Trigger NAO animations (or simulation) for each motion tag
        motion_controller.play_for_emotions(tags)


if __name__ == "__main__":
    main()
