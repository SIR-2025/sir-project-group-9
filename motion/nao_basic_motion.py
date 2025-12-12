# nao_basic_motion.py
# -*- coding: utf-8 -*-
"""
This script provides simple, REUSABLE wrappers for basic NAO motions.
The functions are designed to be imported and used with an EXISTING Nao connection object.

- spin_in_place(nao, turns, direction): Spin on the spot.
- change_position(nao): A sequence of turning and walking.

This script can also be run directly for interactive testing.
"""

import math
import os
import time
from typing import Optional

from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_motion import (
    NaoqiMoveToRequest,
    NaoqiAnimationRequest,
    NaoPostureRequest,
)

# ------------------------------------------------------------------
# Reusable Motion Functions (for import)
# ------------------------------------------------------------------

def spin_in_place(nao: Nao, turns: float = 1.0, direction: str = "left") -> None:
    """
    Makes the NAO robot spin on the spot using an existing Nao object.

    :param nao: An initialized and connected Nao object from the sic_framework.
    :param turns: How many full rotations to make (e.g., 1.0 for 360°).
    :param direction: "left" (counter-clockwise) or "right" (clockwise).
    """
    if not nao:
        print("[ERROR] spin_in_place: Nao object is None.")
        return
    if turns == 0:
        return

    total_angle = 2.0 * math.pi * abs(turns)
    if direction.lower() == "right":
        total_angle = -total_angle

    max_step = math.pi
    remaining = total_angle

    while abs(remaining) > 1e-3:
        step = min(remaining, max_step) if remaining > 0 else max(remaining, -max_step)
        move_req = NaoqiMoveToRequest(x=0.0, y=0.0, theta=step)
        nao.motion.request(move_req)
        remaining -= step
        time.sleep(0.1) # Small delay between steps

def change_position(nao: Nao) -> None:
    """
    A combination of moves using an existing Nao object:
    1. Turn 90 degrees to the right.
    2. Move forward 1 meter.
    3. Turn 90 degrees to the left.
    
    :param nao: An initialized and connected Nao object from the sic_framework.
    """
    if not nao:
        print("[ERROR] change_position: Nao object is None.")
        return

    print("[INFO] Starting 'change_position' sequence...")

    print("[INFO] Step 1: Turning right 90 degrees.")
    spin_in_place(nao, turns=0.25, direction="right")
    time.sleep(0.5)

    print("[INFO] Step 2: Moving forward 1 meter.")
    move_req = NaoqiMoveToRequest(x=1.0, y=0.0, theta=0.0)
    nao.motion.request(move_req)
    time.sleep(0.5)

    print("[INFO] Step 3: Turning left 90 degrees.")
    spin_in_place(nao, turns=0.25, direction="left")

    print("[INFO] 'change_position' sequence finished.")

# ----------------------------------------------------------------------
# Standalone Class & Interactive Menu (for testing)
# ----------------------------------------------------------------------

class NaoBasicMotionStandalone:
    """
    A standalone class for testing that creates its own Nao connection.
    """
    # Official NAOqi postures from Aldebaran documentation (ALRobotPosture)
    BUILTIN_POSTURES = [
        "Crouch",
        "LyingBack",
        "LyingBelly",
        "Sit",
        "SitRelax",
        "Stand",
        "StandInit",
        "StandZero",
    ]

    def __init__(self, nao_ip: Optional[str] = None):
        if nao_ip is None:
            nao_ip = os.getenv("NAO_IP", "10.0.0.137")
        self.nao_ip = nao_ip
        self.nao = Nao(ip=self.nao_ip)

    def lie_down(self, speed: float = 0.3) -> None:
        req = NaoPostureRequest("LyingBack", speed)
        self.nao.motion.request(req)

    def stand_up(self, speed: float = 0.4, use_init: bool = True) -> None:
        """
        Go to a stable upright posture using official Stand/StandInit.
        """
        posture = "StandInit" if use_init else "Stand"
        speed = max(0.05, min(speed, 1.0))
        req = NaoPostureRequest(posture, speed)
        self.nao.motion.request(req)

    def lie_down_feet_straight(self, speed: float = 0.25) -> None:
        """
        Lie on the back with legs kept straight by transitioning through a neutral stand.
        """
        speed = max(0.05, min(speed, 1.0))
        for posture in ("StandZero", "LyingBack"):
            req = NaoPostureRequest(posture, speed)
            self.nao.motion.request(req)
            time.sleep(0.2)

    def death_reach_and_fall(self, reach_animation: str = "animations/Stand/Gestures/You_1", speed: float = 0.2) -> None:
        """
        From a lying posture: curl up, reach forward with one arm, then slowly sink back down.
        Uses only NAO built-in postures and gesture animations.
        """
        speed = max(0.05, min(speed, 1.0))
        try:
            # Move to a compact posture to safely play the gesture.
            self.nao.motion.request(NaoPostureRequest("Sit", speed))
            time.sleep(0.2)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[WARN] Could not move to Sit posture before gesture: {exc}")

        try:
            self.nao.motion.request(NaoqiAnimationRequest(reach_animation))
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[WARN] Failed to play reach gesture '{reach_animation}': {exc}")

        # Slowly return to lying back to mimic a gentle drop.
        try:
            slow_speed = max(0.05, speed / 2.0)
            self.nao.motion.request(NaoPostureRequest("LyingBack", slow_speed))
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[WARN] Could not return to LyingBack posture: {exc}")

    def sit_down(self, speed: float = 0.3, relaxed: bool = True) -> None:
        """
        Valid sit posture (Sit or SitRelax) from NAO official posture set.
        """
        posture = "SitRelax" if relaxed else "Sit"
        speed = max(0.05, min(speed, 1.0))
        req = NaoPostureRequest(posture, speed)
        self.nao.motion.request(req)

    def crouch(self, speed: float = 0.3) -> None:
        """
        Go to the builtin Crouch posture (default rest-like pose on knees).
        """
        speed = max(0.05, min(speed, 1.0))
        self.nao.motion.request(NaoPostureRequest("Crouch", speed))

    def walk_in_place(self, step_distance: float = 0.05, repeats: int = 4, pause: float = 0.2) -> None:
        """
        Simulate walking in place by stepping forward and back around the same spot.
        Uses small MoveTo displacements; adjust distances cautiously.
        """
        repeats = max(1, repeats)
        step_distance = max(0.01, min(step_distance, 0.1))
        pause = max(0.0, pause)

        for i in range(repeats):
            try:
                # Small step forward
                self.nao.motion.request(NaoqiMoveToRequest(x=step_distance, y=0.0, theta=0.0))
                time.sleep(pause)
                # Step back to original spot
                self.nao.motion.request(NaoqiMoveToRequest(x=-step_distance, y=0.0, theta=0.0))
                time.sleep(pause)
            except Exception as exc:  # pylint: disable=broad-except
                print(f"[WARN] Walk-in-place step {i+1} failed: {exc}")
                break

    def list_builtin_actions(self) -> None:
        """
        Print built-in NAO postures and the gesture animations defined in emo_list.
        """
        try:
            from emo_list import GESTURE_ANIMATIONS, NEGATIVE_EMOTION_ANIMATIONS
            animations = NEGATIVE_EMOTION_ANIMATIONS + GESTURE_ANIMATIONS
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[WARN] Could not import animation lists from emo_list: {exc}")
            animations = []

        print("\n[INFO] NAO built-in postures (ALRobotPosture):")
        for p in self.BUILTIN_POSTURES:
            print(f" - {p}")

        if animations:
            print("\n[INFO] Built-in gesture/emotion animations (NAOqi choregraphe library):")
            for name in animations:
                print(f" - {name}")
        print()

    def upup(self, speed: float = 0.25, arms_animation: str = "animations/Stand/Gestures/Enthusiastic_5", wait_after_animation: float = 2.0) -> None:
        """
        Sit on the ground with legs straight (Sit posture) and raise both hands using a built-in gesture.
        Sequence: StandInit (stabilize) -> Sit -> gesture (from StandInit for reliability) -> return to Sit to end seated.
        """
        speed = max(0.05, min(speed, 1.0))
        # Stabilize to StandInit, go Sit (legs forward), stand briefly to ensure animation plays, then return to Sit.
        for posture in ("StandInit", "Sit", "StandInit"):
            try:
                self.nao.motion.request(NaoPostureRequest(posture, speed))
                time.sleep(0.25)
            except Exception as exc:  # pylint: disable=broad-except
                print(f"[WARN] Could not move to {posture} before upup: {exc}")
                break

        played = False
        resolved = self._resolve_animation_name(arms_animation) or arms_animation
        try:
            self.nao.motion.request(NaoqiAnimationRequest(resolved))
            played = True
            time.sleep(max(0.5, wait_after_animation))
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[WARN] Failed to play arms-up animation '{resolved}': {exc}")

        # Return to sit to finish with legs forward.
        try:
            self.nao.motion.request(NaoPostureRequest("Sit", speed))
        except Exception as exc:  # pylint: disable=broad-except
            if played:
                print(f"[WARN] Could not return to Sit after upup: {exc}")

    def go_to_posture(self, posture: str, speed: float = 0.3) -> None:
        """
        Generic helper to move to any official posture in BUILTIN_POSTURES.
        If the name matches a known animation (full path or suffix), play that instead.
        """
        posture = posture.strip()
        speed = max(0.05, min(speed, 1.0))

        if posture in self.BUILTIN_POSTURES:
            self.nao.motion.request(NaoPostureRequest(posture, speed))
            return

        # Try to interpret as animation (full path or suffix)
        anim_name = self._resolve_animation_name(posture)
        if anim_name:
            try:
                self.nao.motion.request(NaoqiAnimationRequest(anim_name))
                return
            except Exception as exc:  # pylint: disable=broad-except
                print(f"[WARN] Failed to play animation '{anim_name}': {exc}")
                return

        print(f"[WARN] '{posture}' is not a builtin posture or known animation.")

    def _resolve_animation_name(self, name: str) -> Optional[str]:
        """
        Resolve user input to a full animation path using emo_list lists.
        Accepts:
          - Full path starting with 'animations/'
          - Suffix like 'Angry_1' or 'Enthusiastic_5' (case-insensitive)
        """
        try:
            from emo_list import GESTURE_ANIMATIONS, NEGATIVE_EMOTION_ANIMATIONS
            animations = NEGATIVE_EMOTION_ANIMATIONS + GESTURE_ANIMATIONS
        except Exception:
            return None

        name = name.strip()
        if not name:
            return None

        lowered = name.lower()

        # Exact full-path match (case-sensitive first, then insensitive)
        if name.startswith("animations/"):
            if name in animations:
                return name
            for anim in animations:
                if anim.lower() == lowered:
                    return anim

        # Suffix match, case-insensitive
        matches = [a for a in animations if a.lower().endswith("/" + lowered)]
        if not matches:
            return None
        if len(matches) == 1:
            return matches[0]
        # Prefer gesture path if duplicate names exist (e.g., Angry_1 in both emotion and gesture lists).
        gesture_matches = [m for m in matches if "/gestures/" in m.lower()]
        if gesture_matches:
            return gesture_matches[0]
        return matches[0]

    def tantrum(self, speed: float = 0.2, repeats: int = 2, flail_animation: str = "animations/Stand/Gestures/Angry_1", wait_after_flail: float = 1.5) -> None:
        """
        Lie on the belly and repeatedly flail arms/legs using a built-in gesture to mimic a tantrum.
        Sequence: StandInit -> LyingBelly -> gesture x N -> return to LyingBelly.
        """
        speed = max(0.05, min(speed, 1.0))
        repeats = max(1, repeats)
        # Stabilize then go down.
        try:
            self.nao.motion.request(NaoPostureRequest("StandInit", speed))
            time.sleep(0.2)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[WARN] Could not move to StandInit before tantrum: {exc}")

        try:
            self.nao.motion.request(NaoPostureRequest("LyingBelly", speed))
            time.sleep(0.25)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[WARN] Could not move to LyingBelly for tantrum: {exc}")

        resolved_anim = self._resolve_animation_name(flail_animation) or flail_animation

        for i in range(repeats):
            try:
                self.nao.motion.request(NaoqiAnimationRequest(resolved_anim))
            except Exception as exc:  # pylint: disable=broad-except
                print(f"[WARN] Failed to play flail animation '{resolved_anim}' on repeat {i+1}: {exc}")
                break
            # Allow animation to play before forcing posture again.
            time.sleep(max(0.5, wait_after_flail))
            # Keep returning to LyingBelly to maintain the down posture between flails.
            try:
                self.nao.motion.request(NaoPostureRequest("LyingBelly", speed))
            except Exception as exc:  # pylint: disable=broad-except
                print(f"[WARN] Could not maintain LyingBelly during tantrum: {exc}")
                break
            time.sleep(0.25)

        # End in a lying posture.
        try:
            self.nao.motion.request(NaoPostureRequest("LyingBelly", speed))
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[WARN] Could not maintain LyingBelly posture after tantrum: {exc}")

def interactive_menu() -> None:
    """
    Run an interactive menu for direct testing of this script.
    """
    motion_standalone = NaoBasicMotionStandalone()
    nao_instance = motion_standalone.nao
    print(f"[INFO] Connected to Nao at {motion_standalone.nao_ip} for interactive testing.")

    while True:
        print("\n===== NAO Basic Motion Menu =====")
        print("1) Spin in place")
        print("2) Stand (StandInit/Stand)")
        print("3) Lie down relaxed (LyingBack)")
        print("4) Lie down with feet straight (StandZero -> LyingBack)")
        print("5) Change Position (sequence)")
        print("6) Sit down (SitRelax/Sit)")
        print("7) Death reach then slow fall")
        print("8) List built-in postures/animations")
        print("9) Go to a specific posture or play an animation (builtin list or suffix)")
        print("10) UpUp (Sit, legs straight, hands up)")
        print("11) Tantrum (LyingBelly, flail)")
        print("12) Crouch (builtin rest-like posture)")
        print("13) Walk in place (small steps forward/back)")
        print("q) Quit")
        choice = input("Enter option: ").strip().lower()

        if choice == "1":
            turns = float(input("How many turns? (default 1.0): ") or 1.0)
            direction = input("Direction: left or right? (default left): ").strip().lower() or "left"
            print(f"[INFO] NAO spinning in place...")
            spin_in_place(nao_instance, turns=turns, direction=direction)

        elif choice == "2":
            speed = float(input("Stand speed (0.0 - 1.0, default 0.4): ") or 0.4)
            init_input = input("Use StandInit? (y/N, default y): ").strip().lower()
            use_init = init_input != "n"
            print(f"[INFO] NAO going to {'StandInit' if use_init else 'Stand'} posture...")
            motion_standalone.stand_up(speed=speed, use_init=use_init)

        elif choice == "3":
            speed = float(input("Lie down speed (0.0 - 1.0, default 0.3): ") or 0.3)
            print(f"[INFO] NAO lying down...")
            motion_standalone.lie_down(speed=speed)

        elif choice == "4":
            speed = float(input("Lie down speed (0.0 - 1.0, default 0.25): ") or 0.25)
            print("[INFO] NAO lying down with feet straight (through StandZero)...")
            motion_standalone.lie_down_feet_straight(speed=speed)

        elif choice == "5":
            print("[INFO] NAO executing 'change_position' sequence...")
            change_position(nao_instance)

        elif choice == "6":
            speed = float(input("Sit posture speed (0.0 - 1.0, default 0.3): ") or 0.3)
            relaxed_input = input("Use relaxed sit? (y/N, default y): ").strip().lower()
            relaxed = relaxed_input != "n"
            print(f"[INFO] NAO going to sit posture ({'SitRelax' if relaxed else 'Sit'})...")
            motion_standalone.sit_down(speed=speed, relaxed=relaxed)

        elif choice == "7":
            speed = float(input("Return speed (0.0 - 1.0, default 0.2): ") or 0.2)
            anim = input("Reach animation (default animations/Stand/Gestures/You_1): ").strip() \
                   or "animations/Stand/Gestures/You_1"
            print(f"[INFO] NAO performing death reach then fall using {anim} ...")
            motion_standalone.death_reach_and_fall(reach_animation=anim, speed=speed)

        elif choice == "8":
            motion_standalone.list_builtin_actions()

        elif choice == "9":
            motion_standalone.list_builtin_actions()
            target = input("Enter posture (builtin) or animation name/suffix: ").strip()
            speed = float(input("Posture speed (0.0 - 1.0, default 0.3): ") or 0.3)
            print(f"[INFO] NAO executing {target} ...")
            motion_standalone.go_to_posture(target, speed=speed)

        elif choice == "10":
            speed = float(input("Sit speed (0.0 - 1.0, default 0.25): ") or 0.25)
            anim = input("Arms-up animation (default animations/Stand/Gestures/Enthusiastic_5): ").strip() \
                   or "animations/Stand/Gestures/Enthusiastic_5"
            print(f"[INFO] NAO performing UpUp (sit then raise hands) using {anim} ...")
            motion_standalone.upup(speed=speed, arms_animation=anim)

        elif choice == "11":
            speed = float(input("Tantrum posture speed (0.0 - 1.0, default 0.2): ") or 0.2)
            repeats = int(input("Flail repeats (default 2): ") or 2)
            anim = input("Flail animation (default animations/Stand/Gestures/Angry_1): ").strip() \
                   or "animations/Stand/Gestures/Angry_1"
            print(f"[INFO] NAO performing tantrum with {repeats} flails using {anim} ...")
            motion_standalone.tantrum(speed=speed, repeats=repeats, flail_animation=anim)

        elif choice == "12":
            speed = float(input("Crouch speed (0.0 - 1.0, default 0.3): ") or 0.3)
            print("[INFO] NAO going to Crouch posture ...")
            motion_standalone.crouch(speed=speed)

        elif choice == "13":
            step_dist = float(input("Step distance meters (0.01 - 0.1, default 0.05): ") or 0.05)
            reps = int(input("Number of step cycles (default 4): ") or 4)
            pause = float(input("Pause between steps (seconds, default 0.2): ") or 0.2)
            print(f"[INFO] NAO walking in place for {reps} cycles...")
            motion_standalone.walk_in_place(step_distance=step_dist, repeats=reps, pause=pause)

        elif choice == "q":
            print("[INFO] Exiting program.")
            break
        else:
            print("[WARN] Invalid option.")

if __name__ == "__main__":
    interactive_menu()
