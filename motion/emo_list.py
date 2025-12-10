# -*- coding: utf-8 -*-
"""
motion_animations_demo.py

Use Social Interaction Cloud (SIC) to access NAO's built-in animation interface:
- List and print all predefined animations under the following two paths:
    * animations/Stand/Emotions/Negative
    * animations/Stand/Gestures
- Select and perform any of these animations

Note:
- This script only uses sic_framework, not naoqi / qi SDK directly.
- The animation list is from NAO's official documentation and example output. If you have custom behaviors
  installed on your robot, they will not automatically appear in this list and you need to add them manually.
"""

from __future__ import print_function

import argparse
import sys

from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_motion import (
    NaoPostureRequest,
    NaoqiAnimationRequest,
)

# ---------------------------------------------------------------------------
# 1. Predefined Animation List
# ---------------------------------------------------------------------------

NEGATIVE_EMOTION_ANIMATIONS = [
    "animations/Stand/Emotions/Negative/Angry_1",
    "animations/Stand/Emotions/Negative/Angry_2",
    "animations/Stand/Emotions/Negative/Angry_3",
    "animations/Stand/Emotions/Negative/Angry_4",
    "animations/Stand/Emotions/Negative/Anxious_1",
    "animations/Stand/Emotions/Negative/Bored_1",
    "animations/Stand/Emotions/Negative/Bored_2",
    "animations/Stand/Emotions/Negative/Disappointed_1",
    "animations/Stand/Emotions/Negative/Exhausted_1",
    "animations/Stand/Emotions/Negative/Exhausted_2",
    "animations/Stand/Emotions/Negative/Fear_1",
    "animations/Stand/Emotions/Negative/Fear_2",
    "animations/Stand/Emotions/Negative/Fearful_1",
    "animations/Stand/Emotions/Negative/Frustrated_1",
    "animations/Stand/Emotions/Negative/Humiliated_1",
    "animations/Stand/Emotions/Negative/Hurt_1",
    "animations/Stand/Emotions/Negative/Hurt_2",
    "animations/Stand/Emotions/Negative/Late_1",
    "animations/Stand/Emotions/Negative/Sad_1",
    "animations/Stand/Emotions/Negative/Sad_2",
    "animations/Stand/Emotions/Negative/Shocked_1",
    "animations/Stand/Emotions/Negative/Sorry_1",
    "animations/Stand/Emotions/Negative/Surprise_1",
    "animations/Stand/Emotions/Negative/Surprise_2",
    "animations/Stand/Emotions/Negative/Surprise_3",
]

GESTURE_ANIMATIONS = [
    # From example output
    "animations/Stand/Gestures/Angry_1",
    "animations/Stand/Gestures/Angry_2",
    "animations/Stand/Gestures/Angry_3",
    "animations/Stand/Gestures/BowShort_1",
    "animations/Stand/Gestures/BowShort_2",
    "animations/Stand/Gestures/BowShort_3",
    "animations/Stand/Gestures/But_1",
    "animations/Stand/Gestures/CalmDown_1",
    "animations/Stand/Gestures/CalmDown_2",
    "animations/Stand/Gestures/CalmDown_3",
    "animations/Stand/Gestures/CalmDown_4",
    "animations/Stand/Gestures/CalmDown_5",
    "animations/Stand/Gestures/CalmDown_6",
    "animations/Stand/Gestures/Choice_1",
    "animations/Stand/Gestures/ComeOn_1",
    "animations/Stand/Gestures/Confused_1",
    "animations/Stand/Gestures/Confused_2",
    "animations/Stand/Gestures/CountFive_1",
    "animations/Stand/Gestures/CountFour_1",
    "animations/Stand/Gestures/CountMore_1",
    "animations/Stand/Gestures/CountOne_1",
    "animations/Stand/Gestures/CountThree_1",
    "animations/Stand/Gestures/CountTwo_1",
    "animations/Stand/Gestures/Desperate_1",
    "animations/Stand/Gestures/Desperate_2",
    "animations/Stand/Gestures/Desperate_3",
    "animations/Stand/Gestures/Desperate_4",
    "animations/Stand/Gestures/Desperate_5",
    "animations/Stand/Gestures/DontUnderstand_1",
    "animations/Stand/Gestures/Enthusiastic_3",
    "animations/Stand/Gestures/Enthusiastic_4",
    "animations/Stand/Gestures/Enthusiastic_5",
    "animations/Stand/Gestures/Everything_1",
    "animations/Stand/Gestures/Everything_2",
    "animations/Stand/Gestures/Everything_3",
    "animations/Stand/Gestures/Everything_4",
    "animations/Stand/Gestures/Everything_6",
    "animations/Stand/Gestures/Excited_1",
    "animations/Stand/Gestures/Explain_1",
    "animations/Stand/Gestures/Explain_2",
    "animations/Stand/Gestures/Explain_3",
    "animations/Stand/Gestures/Explain_4",
    "animations/Stand/Gestures/Explain_5",
    "animations/Stand/Gestures/Explain_6",
    "animations/Stand/Gestures/Explain_7",
    "animations/Stand/Gestures/Explain_8",
    "animations/Stand/Gestures/Explain_10",
    "animations/Stand/Gestures/Explain_11",
    "animations/Stand/Gestures/Far_1",
    "animations/Stand/Gestures/Far_2",
    "animations/Stand/Gestures/Far_3",
    "animations/Stand/Gestures/Follow_1",
    "animations/Stand/Gestures/Give_1",
    "animations/Stand/Gestures/Give_2",
    "animations/Stand/Gestures/Give_3",
    "animations/Stand/Gestures/Give_4",
    "animations/Stand/Gestures/Give_5",
    "animations/Stand/Gestures/Give_6",
    "animations/Stand/Gestures/Great_1",
    "animations/Stand/Gestures/HeSays_1",
    "animations/Stand/Gestures/HeSays_2",
    "animations/Stand/Gestures/HeSays_3",
    # From Aldebaran's official NAO animation list (to add the missing ones)
    "animations/Stand/Gestures/Hey_1",
    "animations/Stand/Gestures/Hey_6",
    "animations/Stand/Gestures/IDontKnow_1",
    "animations/Stand/Gestures/IDontKnow_2",
    "animations/Stand/Gestures/Me_1",
    "animations/Stand/Gestures/Me_2",
    "animations/Stand/Gestures/No_3",
    "animations/Stand/Gestures/No_8",
    "animations/Stand/Gestures/No_9",
    "animations/Stand/Gestures/Please_1",
    "animations/Stand/Gestures/Yes_1",
    "animations/Stand/Gestures/Yes_2",
    "animations/Stand/Gestures/Yes_3",
    "animations/Stand/Gestures/YouKnowWhat_1",
    "animations/Stand/Gestures/YouKnowWhat_5",
    "animations/Stand/Gestures/You_1",
    "animations/Stand/Gestures/You_4",
]

ALL_ANIMATIONS = NEGATIVE_EMOTION_ANIMATIONS + GESTURE_ANIMATIONS


# ---------------------------------------------------------------------------
# 2. Utility function to print animation file names
# ---------------------------------------------------------------------------

def print_animation_lists():
    """Prints the names of all predefined animations under the two paths."""
    print("=" * 60)
    print("Predefined animations under animations/Stand/Emotions/Negative:")
    for idx, name in enumerate(NEGATIVE_EMOTION_ANIMATIONS):
        print("[{:02d}] {}".format(idx, name))

    print("\n" + "=" * 60)
    print("Predefined animations under animations/Stand/Gestures:")
    offset = len(NEGATIVE_EMOTION_ANIMATIONS)
    for i, name in enumerate(GESTURE_ANIMATIONS):
        print("[{:02d}] {}".format(i + offset, name))

    print("=" * 60)
    print("Total {} animations.".format(len(ALL_ANIMATIONS)))


# ---------------------------------------------------------------------------
# 3. Main App Class: Connect to NAO and Perform Animations
# ---------------------------------------------------------------------------

class MotionAnimationsApp(object):
    def __init__(self, nao_ip, auto_stand=True):
        """
        :param nao_ip: IP address of the robot
        :param auto_stand: Whether to automatically go to Stand posture before playing an animation
        """
        self.nao_ip = nao_ip
        self.auto_stand = auto_stand
        self.nao = None

    # ------ Initialization & Posture Control ------
    def setup(self):
        """Initializes the NAO device object."""
        print("[INFO] Connecting to Nao at {} via SIC...".format(self.nao_ip))
        # We don't use naoqi directly here, only SIC's Nao wrapper
        self.nao = Nao(ip=self.nao_ip)
        print("[INFO] Nao device created.")

    def go_to_stand(self):
        """Makes NAO go to Stand posture (if needed)."""
        if not self.auto_stand:
            return

        print("[INFO] Going to Stand posture...")
        try:
            self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
        except Exception as exc:  # pylint: disable=broad-except
            print("[WARN] Failed to change posture to Stand: {}".format(exc))

    # ------ Animation Playback ------
    def play_animation(self, animation_name):
        """Plays the animation with the specified name."""
        print("[INFO] Playing animation: {}".format(animation_name))
        try:
            self.nao.motion.request(NaoqiAnimationRequest(animation_name))
        except Exception as exc:  # pylint: disable=broad-except
            print("[ERROR] Failed to play animation {}: {}".format(animation_name, exc))

    # ------ Interactive Command Line ------
    def interactive_loop(self):
        """A simple command-line interface to select and play animations by index or name."""
        if self.nao is None:
            self.setup()

        self.go_to_stand()
        print_animation_lists()

        print("\nEnter the index, full path, or ending name of the animation to play, for example:")
        print("  - 0            # Play the 0th animation in the list")
        print("  - Angry_1      # Match by the ending name")
        print("  - animations/Stand/Gestures/Hey_1")
        print("Enter 'list' to print the list again, enter 'q' / 'quit' to exit.\n")

        if sys.version_info[0] < 3:
            input_func = raw_input  # type: ignore[name-defined]
        else:
            input_func = input

        while True:
            try:
                user_input = input_func("Select animation> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[INFO] Bye.")
                break

            if not user_input:
                continue

            if user_input.lower() in ("q", "quit", "exit"):
                print("[INFO] Quit.")
                break

            if user_input.lower() in ("l", "list"):
                print_animation_lists()
                continue

            # Try to treat the input as an index
            if user_input.isdigit():
                idx = int(user_input)
                if 0 <= idx < len(ALL_ANIMATIONS):
                    self.play_animation(ALL_ANIMATIONS[idx])
                else:
                    print("[WARN] Index out of range 0-{}.".format(len(ALL_ANIMATIONS) - 1))
                continue

            # If not a digit, try to match a path or ending name
            # Full path (starts with animations/)
            anim_name = None
            if user_input.startswith("animations/"):
                if user_input in ALL_ANIMATIONS:
                    anim_name = user_input
                else:
                    print("[WARN] Could not find this animation in the predefined list: {}".format(user_input))
                    continue
            else:
                # Match by ending name, e.g., "Angry_1"
                matches = [
                    name for name in ALL_ANIMATIONS
                    if name.endswith("/" + user_input)
                ]
                if len(matches) == 1:
                    anim_name = matches[0]
                elif len(matches) > 1:
                    print("[WARN] The name is not unique, multiple animations matched:")
                    for m in matches:
                        print("  -", m)
                    continue
                else:
                    print("[WARN] Could not find an animation with a name containing '{}'.".format(user_input))
                    continue

            if anim_name:
                self.play_animation(anim_name)


# ---------------------------------------------------------------------------
# 4. Command-line Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="List and play NAO's predefined emotion/gesture animations (SIC, no direct naoqi calls)"
    )
    parser.add_argument(
        "--ip",
        "-i",
        required=True,
        help="IP address of the NAO robot",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only output the animation list, do not connect to the robot or play actions",
    )
    parser.add_argument(
        "--no-stand",
        action="store_true",
        help="Do not automatically switch to Stand posture before playing",
    )
    parser.add_argument(
        "--play",
        help=(
            "Directly play the specified animation instead of entering interactive mode; "
            "can be an index (integer) or the animation's ending name / full path"
        ),
    )

    args = parser.parse_args()

    # 1) Mode to only print the list
    if args.list_only:
        print_animation_lists()
        return

    # 2) Mode that requires an actual connection to NAO
    app = MotionAnimationsApp(nao_ip=args.ip, auto_stand=not args.no_stand)

    app.setup()
    app.go_to_stand()

    if args.play:
        # Play directly once (reuse the same parsing logic as interactive mode)
        user_input = args.play.strip()
        if user_input.isdigit():
            idx = int(user_input)
            if 0 <= idx < len(ALL_ANIMATIONS):
                app.play_animation(ALL_ANIMATIONS[idx])
            else:
                print("[WARN] Index out of range 0-{}.".format(len(ALL_ANIMATIONS) - 1))
        elif user_input.startswith("animations/"):
            if user_input in ALL_ANIMATIONS:
                app.play_animation(user_input)
            else:
                print("[WARN] Could not find this animation in the predefined list: {}".format(user_input))
        else:
            matches = [
                name for name in ALL_ANIMATIONS
                if name.endswith("/" + user_input)
            ]
            if len(matches) == 1:
                app.play_animation(matches[0])
            elif len(matches) > 1:
                print("[WARN] The name is not unique, multiple animations matched:")
                for m in matches:
                    print("  -", m)
            else:
                print("[WARN] Could not find an animation with a name containing '{}'.".format(user_input))
    else:
        # Enter interactive loop
        app.interactive_loop()


if __name__ == "__main__":
    main()