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
    def __init__(self, nao_ip: Optional[str] = None):
        if nao_ip is None:
            nao_ip = os.getenv("NAO_IP", "10.0.0.137")
        self.nao_ip = nao_ip
        self.nao = Nao(ip=self.nao_ip)

    def lie_down(self, speed: float = 0.3) -> None:
        req = NaoPostureRequest("LyingBack", speed)
        self.nao.motion.request(req)

    def sit_on_chair(self, speed: float = 0.3) -> None:
        req = NaoPostureRequest("SitOnChair", speed)
        self.nao.motion.request(req)

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
        print("2) Lie down (LyingBack)")
        print("3) Change Position (sequence)")
        print("4) Sit on chair (SitOnChair)")
        print("q) Quit")
        choice = input("Enter option: ").strip().lower()

        if choice == "1":
            turns = float(input("How many turns? (default 1.0): ") or 1.0)
            direction = input("Direction: left or right? (default left): ").strip().lower() or "left"
            print(f"[INFO] NAO spinning in place...")
            spin_in_place(nao_instance, turns=turns, direction=direction)
        
        elif choice == "2":
            speed = float(input("Lie down speed (0.0 - 1.0, default 0.3): ") or 0.3)
            print(f"[INFO] NAO lying down...")
            motion_standalone.lie_down(speed=speed)

        elif choice == "3":
            print("[INFO] NAO executing 'change_position' sequence...")
            change_position(nao_instance)

        elif choice == "4":
            speed = float(input("SitOnChair speed (0.0 - 1.0, default 0.3): ") or 0.3)
            print(f"[INFO] NAO going to 'SitOnChair' posture...")
            motion_standalone.sit_on_chair(speed=speed)

        elif choice == "q":
            print("[INFO] Exiting program.")
            break
        else:
            print("[WARN] Invalid option.")

if __name__ == "__main__":
    interactive_menu()
