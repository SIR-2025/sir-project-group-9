# motion_controller.py
# -*- coding: utf-8 -*-

import os
import re
from typing import Optional, Set

import emo_list  # contains MotionAnimationsApp and ALL_ANIMATIONS
import nao_basic_motion # Import the refactored basic motion functions

# Import NAO TTS request type (same as in demo_nao_talk.py)
from sic_framework.devices.common_naoqi.naoqi_text_to_speech import (
    NaoqiTextToSpeechRequest,
)
from sic_framework.devices.common_naoqi.naoqi_motion import NaoPostureRequest


class EmotionMotionController:
    """
    High-level wrapper around emo_list.MotionAnimationsApp.

    Responsibilities:
    - Initialize NAO connection via SIC.
    - Map motion tags (e.g. "angry", "sad", "gesture_hey") to NAO animations.
    - Provide real TTS for speech, with fallback simulation mode.
    """

    def __init__(
        self,
        nao_ip: Optional[str] = "10.0.0.137",
        auto_stand: bool = True,
        enable_simulation: bool = True,
    ) -> None:
        """
        :param nao_ip: NAO robot IP. If None, use NAO_IP environment variable.
        :param auto_stand: If True, go to Stand posture on startup.
        :param enable_simulation: If True, print simulated actions when NAO is not available.
        """
        self.nao_ip: Optional[str] = nao_ip or os.getenv("NAO_IP")
        self.auto_stand = auto_stand
        self.enable_simulation = enable_simulation

        self.app: Optional[emo_list.MotionAnimationsApp] = None

        if self.nao_ip:
            self._init_real_robot()
        else:
            print("[MOTION] No NAO IP provided. Running in simulation mode only.")

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _init_real_robot(self) -> None:
        """
        Try to initialize MotionAnimationsApp from emo_list.
        """
        try:
            print(f"[MOTION] Initializing MotionAnimationsApp with IP {self.nao_ip} ...")
            self.app = emo_list.MotionAnimationsApp(
                nao_ip=self.nao_ip,
                auto_stand=self.auto_stand,
            )
            self.app.setup()
            if self.auto_stand:
                self.app.go_to_stand()
            print("[MOTION] MotionAnimationsApp initialized successfully.")
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[MOTION] Failed to initialize MotionAnimationsApp: {exc}")
            self.app = None

    def is_real_robot_available(self) -> bool:
        """
        Return True if NAO is successfully initialized.
        """
        return self.app is not None and getattr(self.app, "nao", None) is not None

    # ------------------------------------------------------------------
    # Tag normalization and animation mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_animation_name(name: str) -> Optional[str]:
        """
        Resolve a provided animation identifier to a known full path using emo_list lists.
        Accepts full paths or suffixes like 'Angry_1'. Returns the best match or None.
        """
        if not name:
            return None

        animations = getattr(emo_list, "ALL_ANIMATIONS", [])
        lowered = name.strip().lower()
        if not lowered:
            return None

        # Exact full-path match (case-sensitive or insensitive)
        if name.startswith("animations/"):
            for anim in animations:
                if name == anim:
                    return anim
            for anim in animations:
                if anim.lower() == lowered:
                    return anim

        # Suffix match, case-insensitive
        matches = [a for a in animations if a.lower().endswith("/" + lowered)]
        if not matches:
            return None
        if len(matches) == 1:
            return matches[0]
        # Prefer gesture path if duplicates
        gesture_matches = [m for m in matches if "/gestures/" in m.lower()]
        if gesture_matches:
            return gesture_matches[0]
        return matches[0]

    @staticmethod
    def _normalize_tag(tag: str) -> str:
        """
        Convert something like 'gesture_hey' or 'very_angry' to a compact
        semantic keyword that can be matched against animation names.
        Example:
            'gesture_hey' -> 'hey'
            'very_angry'  -> 'veryangry'
        """
        raw = tag.strip().lower()

        # Explicit prefix for gesture tags, we only keep the semantic part.
        if raw.startswith("gesture_"):
            raw = raw[len("gesture_") :]

        # Remove underscores for easier substring matching.
        return raw.replace("_", "")

    def _find_animation_for_tag(self, tag: str) -> Optional[str]:
        """
        Given a motion tag string like 'angry', 'sad', 'gesture_hey', etc.,
        try to find a suitable animation name from emo_list.ALL_ANIMATIONS.

        Strategy:
        1. Normalize tag to a compact semantic token, e.g. 'gesture_hey' -> 'hey'.
        2. For each animation name in ALL_ANIMATIONS:
           - Take base name (after the last '/'), e.g. 'Angry_1'.
           - Lowercase it and remove non-letters, e.g. 'angry1' -> 'angry'.
           - Check if normalized tag is contained in this compact base.
        3. Return the first match found.
        """
        if not tag:
            return None

        normalized = self._normalize_tag(tag)
        if not normalized:
            return None

        for name in emo_list.ALL_ANIMATIONS:
            base = name.split("/")[-1]  # e.g. "Angry_1"
            base_low = base.lower()
            base_compact = re.sub(r"[^a-z]", "", base_low)  # "angry1" -> "angry"

            if normalized in base_compact:
                return name

        return None

    # ------------------------------------------------------------------
    # TTS (real or simulated)
    # ------------------------------------------------------------------

    def speak_text(self, text: str, emotion_tag: Optional[str] = None, block: bool = False) -> None:
        """
        Use NAO's built-in TTS to say the given text.
        If NAO is unavailable, fall back to printing a simulated TTS line.

        :param text: The text that NAO should say.
        :param emotion_tag: Optional motion/emotion tag (e.g. "angry", "sad").
                            If provided, we may enable animated TTS.
        :param block: If True, wait for the speech to complete before returning.
        """
        if not text:
            return

        # Choose whether to use animated TTS based on whether we have an emotion.
        animated = emotion_tag is not None and not emotion_tag.startswith("gesture_")

        # Slightly louder voice than before (70%).
        modified_text = f"\\vct=100\\{text}"

        # Real robot available
        if self.is_real_robot_available():
            try:
                print(
                    f"[TTS] NAO speaking (animated={animated}, tag={emotion_tag!r}): {modified_text}"
                )
                # Same pattern as in demo_nao_talk.py:
                # self.nao.tts.request(NaoqiTextToSpeechRequest("Hello ...", animated=True))
                request = NaoqiTextToSpeechRequest(modified_text, animated=animated)
                self.app.nao.tts.request(request, block=block)

            except Exception as exc:  # pylint: disable=broad-except
                print(f"[TTS] Error while sending TTS request: {exc}")
            return

        # No robot available, simulation mode
        if self.enable_simulation:
            if emotion_tag:
                print(f"[TTS][SIM] ({emotion_tag}) {modified_text}")
            else:
                print(f"[TTS][SIM] {modified_text}")
        else:
            print("[TTS] Robot is not available and simulation is disabled.")

    # ------------------------------------------------------------------
    # Motion playback for a set of tags
    # ------------------------------------------------------------------

    def play_for_emotions(self, emotions: Set[str]) -> None:
        """
        For each emotion/motion tag in the set, find a matching NAO animation and play it.
        If NAO is not available but simulation is enabled, print what would be played.

        Tags can be:
        - Pure emotions  like 'angry', 'sad', 'bored', 'surprise', etc.
        - Gesture tags   like 'gesture_hey', 'gesture_yes', 'gesture_bow', etc.
        - A special tag 'neutral' meaning "no animation".
        """
        if not emotions:
            print("[MOTION] No motion tags to play.")
            return

        # Do not play anything for neutral tags.
        filtered = {e for e in emotions if e != "neutral"}
        if not filtered:
            print("[MOTION] Only 'neutral' tag found. No animation will be played.")
            return

        for tag in filtered:
            animation = self._find_animation_for_tag(tag)
            resolved = self._resolve_animation_name(animation) or animation
            if not animation:
                print(f"[MOTION] No animation mapped for tag '{tag}'.")
                continue

            # Real robot available
            if self.is_real_robot_available():
                try:
                    print(
                        f"[MOTION] Playing animation '{resolved}' for tag '{tag}'."
                    )
                    self.app.play_animation(resolved)
                except Exception as exc:  # pylint: disable=broad-except
                    print(f"[MOTION] Error while playing animation '{resolved}': {exc}")
                continue

            # No real robot, but simulation allowed
            if self.enable_simulation:
                print(
                    f"[MOTION][SIM] Would play animation '{resolved}' for tag '{tag}'."
                )
            else:
                print("[MOTION] Robot is not available and simulation is disabled.")

    # ------------------------------------------------------------------
    # Special high-level actions
    # ------------------------------------------------------------------

    def go_to_crouch(self, speed: float = 0.3) -> None:
        """
        Move to the built-in Crouch posture. Used to keep low posture in baby stage.
        """
        if self.is_real_robot_available():
            try:
                self.app.nao.motion.request(NaoPostureRequest("Crouch", speed))
                print("[MOTION] Switched to Crouch posture.")
            except Exception as exc:  # pylint: disable=broad-except
                print(f"[MOTION] Failed to switch to Crouch: {exc}")
        elif self.enable_simulation:
            print("[MOTION][SIM] Would switch to Crouch posture.")

    def perform_wrap_up_action(self, use_spin: bool = False) -> None:
        """
        Performs the wrap-up action.
        If use_spin is True and a real robot is available, perform a spin.
        Otherwise perform the default change_position sequence.
        """
        action_label = "spin_in_place" if use_spin else "change_position"

        if self.is_real_robot_available():
            print(f"[MOTION] Performing wrap-up action '{action_label}'.")
            try:
                if use_spin:
                    nao_basic_motion.spin_in_place(self.app.nao)
                else:
                    nao_basic_motion.change_position(self.app.nao)
            except Exception as e:
                print(f"[MOTION] Error during wrap-up action: {e}")
        else:
            # If no real robot, simulate the action
            if use_spin:
                print("[MOTION][SIM] Would perform 'spin_in_place' as wrap-up action.")
            else:
                print("[MOTION][SIM] Would perform 'change_position' sequence as wrap-up action.")

    # ------------------------------------------------------------------
    # Posture helpers
    # ------------------------------------------------------------------

    def go_to_posture(self, posture: str, speed: float = 0.3) -> None:
        """
        Generic helper to move to a NAO built-in posture.
        """
        posture = posture.strip()
        if not posture:
            return
        speed = max(0.05, min(speed, 1.0))

        if self.is_real_robot_available():
            try:
                self.app.nao.motion.request(NaoPostureRequest(posture, speed))
                print(f"[MOTION] Switched to posture '{posture}'.")
            except Exception as exc:  # pylint: disable=broad-except
                print(f"[MOTION] Failed to switch to posture '{posture}': {exc}")
        elif self.enable_simulation:
            print(f"[MOTION][SIM] Would switch to posture '{posture}'.")

    def go_to_lying_back(self, speed: float = 0.3) -> None:
        self.go_to_posture("LyingBack", speed)

    def go_to_sit_relax(self, speed: float = 0.3) -> None:
        self.go_to_posture("SitRelax", speed)

    def go_to_stand(self, speed: float = 0.4) -> None:
        self.go_to_posture("StandInit", speed)

    def go_to_lying_belly(self, speed: float = 0.3) -> None:
        self.go_to_posture("LyingBelly", speed)

    def perform_elderly_shutdown(self) -> None:
        """
        Elderly wrap-up: Stand, then change position, then lie on belly.
        """
        print("[MOTION] Performing elderly shutdown sequence: Stand -> change_position -> LyingBelly.")
        try:
            self.go_to_stand()
            if self.is_real_robot_available():
                nao_basic_motion.change_position(self.app.nao)
            elif self.enable_simulation:
                print("[MOTION][SIM] Would perform 'change_position' sequence.")
            self.go_to_lying_belly()
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[MOTION] Elderly shutdown sequence failed: {exc}")
