# nao_basic_motion.py
# -*- coding: utf-8 -*-
"""
This script provides simple wrappers for basic NAO motions:
- Spin in place (spin_in_place)
- Lie down (lie_down)
- A combined movement sequence (change_position)

It also provides a command-line interactive menu.
- Run `python nao_basic_motion.py` and select an action from the prompts.

Dependencies:
    pip install "social-interaction-cloud"
And SIC must be installed and running on the NAO robot.
"""

import math
import os
from typing import Optional

from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_motion import (
    NaoqiMoveToRequest,
    NaoPostureRequest,
)


class NaoBasicMotion:
    """
    Provides simple high-level actions:
      - spin_in_place: Spin on the spot.
      - lie_down: Lie down on its back (LyingBack posture).
      - change_position: A sequence of turning and walking.
    """

    def __init__(self, nao_ip: Optional[str] = None):
        # Use NAO_IP from environment variables if available
        if nao_ip is None:
            nao_ip = os.getenv("NAO_IP", "10.0.0.127")

        self.nao_ip = nao_ip
        self.nao = Nao(ip=self.nao_ip)

    # ------------------------------------------------------------------
    # Spin in place
    # ------------------------------------------------------------------
    def spin_in_place(self, turns: float = 1.0, direction: str = "left") -> None:
        """
        Makes the NAO robot spin on the spot (rotation only, no translation).

        :param turns: How many full rotations to make.
                      1.0 = 360°
                      0.5 = 180°
                      0.25 = 90°, etc.
        :param direction: "left" or "right"
                           "left"  = counter-clockwise
                           "right" = clockwise
        """
        if turns == 0:
            return

        total_angle = 2.0 * math.pi * abs(turns)

        # Direction: left = positive angle, right = negative angle
        if direction.lower() == "right":
            total_angle = -total_angle

        # The theta for NaoqiMoveToRequest must be in [-pi, pi], so we execute in steps.
        max_step = math.pi  # Max rotation per step: 180°
        remaining = total_angle

        while abs(remaining) > 1e-3:
            # The angle for this step, clamped to [-max_step, max_step]
            if remaining > 0:
                step = min(remaining, max_step)
            else:
                step = max(remaining, -max_step)

            req = NaoqiMoveToRequest(x=0.0, y=0.0, theta=step)
            self.nao.motion.request(req)

            remaining -= step

    # ------------------------------------------------------------------
    # Lie down
    # ------------------------------------------------------------------
    def lie_down(self, speed: float = 0.3) -> None:
        """
        Makes the NAO robot lie down (using the LyingBack predefined posture).

        :param speed: The speed of the posture change (0.0 - 1.0). Recommended: 0.2-0.5.
        """
        req = NaoPostureRequest("LyingBack", speed)
        self.nao.motion.request(req)

    # ------------------------------------------------------------------
    # Change position (New combined action)
    # ------------------------------------------------------------------
    def change_position(self) -> None:
        """
        A combination of moves:
        1. Turn 90 degrees to the right.
        2. Move forward 1.5 meters.
        3. Turn 90 degrees to the left.
        """
        print("[INFO] Starting 'change_position' sequence...")

        # 1. Turn left 90 degrees
        print("[INFO] Step 1: Turning right 90 degrees.")
        self.spin_in_place(turns=0.25, direction="right")

        # 2. Move forward 1.5 meters
        print("[INFO] Step 2: Moving forward 1.5 meters.")
        # NaoqiMoveToRequest uses meters for x and y
        move_req = NaoqiMoveToRequest(x=1, y=0.0, theta=0.0)
        self.nao.motion.request(move_req)

        # 3. Turn right 90 degrees
        print("[INFO] Step 3: Turning left 90 degrees.")
        self.spin_in_place(turns=0.25, direction="left")

        print("[INFO] 'change_position' sequence finished.")


# ----------------------------------------------------------------------
# Interactive command-line menu
# ----------------------------------------------------------------------
def interactive_menu() -> None:
    """
    Run an interactive menu when this file is executed:
        1 -> Spin in place
        2 -> Lie down
        3 -> Change position (sequence)
        q -> Quit
    """
    motion = NaoBasicMotion()
    print(f"[INFO] Connected to Nao at {motion.nao_ip}")
    print("[INFO] Interactive mode: select an action for NAO to perform.")

    while True:
        print("\n===== NAO Basic Motion Menu =====")
        print("1) Spin in place")
        print("2) Lie down (LyingBack)")
        print("3) Change Position (sequence)")
        print("q) Quit")
        choice = input("Enter option (1/2/3/q): ").strip().lower()

        if choice == "1":
            # Let user choose turns and direction, with defaults
            turns_input = input("How many turns? (default 1.0): ").strip()
            dir_input = input("Direction: left or right? (default left): ").strip().lower()

            if not turns_input:
                turns = 1.0
            else:
                try:
                    turns = float(turns_input)
                except ValueError:
                    print("[WARN] Turns must be a number, using default 1.0.")
                    turns = 1.0

            if dir_input not in {"left", "right"}:
                dir_input = "left"

            print(f"[INFO] NAO spinning in place: {turns} turns, direction: {dir_input}")
            motion.spin_in_place(turns=turns, direction=dir_input)

        elif choice == "2":
            speed_input = input("Lie down speed (0.0 - 1.0, default 0.3): ").strip()
            if not speed_input:
                speed = 0.3
            else:
                try:
                    speed = float(speed_input)
                except ValueError:
                    print("[WARN] Speed must be a number, using default 0.3.")
                    speed = 0.3

            print(f"[INFO] NAO lying down (LyingBack) with speed={speed}...")
            motion.lie_down(speed=speed)

        elif choice == "3":
            print("[INFO] NAO executing 'change_position' sequence...")
            motion.change_position()

        elif choice == "q":
            print("[INFO] Exiting program.")
            break

        else:
            print("[WARN] Invalid option, please enter 1, 2, 3, or q.")


if __name__ == "__main__":
    interactive_menu()
