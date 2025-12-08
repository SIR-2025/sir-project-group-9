# stt_input.py
# -*- coding: utf-8 -*-

import json
import os
from os.path import abspath, join
from typing import Optional

from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging
from sic_framework.devices.desktop import Desktop
from sic_framework.services.google_stt.google_stt import (
    GoogleSpeechToText,
    GoogleSpeechToTextConf,
    GetStatementRequest,
)


class GoogleSTTInput(SICApplication):
    """
    A simplified wrapper for Google Speech-to-Text, designed for a single,
    blocking "speak -> get text" call within main.py.
    """

    def __init__(self, google_keyfile_path: Optional[str] = None):
        """
        Initializes the Speech-to-Text input component.
        
        :param google_keyfile_path: Path to the Google Cloud credentials JSON file.
                                    If not provided, it will try a default relative path.
        """
        # Initialize SICApplication (as in the official demos)
        super().__init__()

        # Set logging level
        self.set_log_level(sic_logging.INFO)

        # Initialize desktop microphone
        self.desktop = Desktop()
        self.desktop_mic = self.desktop.mic

        # Use the official demo's key path structure as a default
        if google_keyfile_path is None:
            google_keyfile_path = abspath(
                join(os.path.dirname(__file__), "..", "..", "conf", "google", "google-key.json")
            )

        try:
            keyfile_json = json.load(open(google_keyfile_path))
        except FileNotFoundError:
            self.logger.error(f"Google Cloud credentials file not found at: {google_keyfile_path}")
            self.logger.error("Please ensure the key file exists or provide the correct path.")
            # Since this is critical, we might want to exit or handle this more gracefully.
            # For now, we'll let the subsequent call fail.
            keyfile_json = {}


        # Configure STT
        stt_conf = GoogleSpeechToTextConf(
            keyfile_json=keyfile_json,
            sample_rate_hertz=44100,
            language="en-US",
            interim_results=False,  # We only need the final result
        )

        # Create the STT service with the desktop microphone as the input source
        self.stt = GoogleSpeechToText(conf=stt_conf, input_source=self.desktop_mic)
        self.logger.info("Google STT Input initialized.")


    def listen_once(self) -> str:
        """
        Listens for a single utterance in a blocking manner and returns the transcribed text.
        
        :return: The transcribed text as a string, or an empty string if no speech was detected.
        """
        self.logger.info("Listening for speech...")
        result = self.stt.request(GetStatementRequest())
        if (
            not result
            or not hasattr(result.response, "alternatives")
            or not result.response.alternatives
        ):
            self.logger.info("No transcript received.")
            return ""
        
        transcript = result.response.alternatives[0].transcript or ""
        self.logger.info(f"Heard: '{transcript}'")
        return transcript

    def close(self) -> None:
        """
        Shuts down the application and cleans up resources.
        """
        self.logger.info("Shutting down STT service.")
        self.shutdown()


if __name__ == '__main__':
    # This block makes the script runnable for standalone testing.
    print("--- Standalone Google STT Test ---")
    print("Speak into your microphone. Say 'quit' or 'exit' to stop.")
    
    try:
        stt_input = GoogleSTTInput()
        
        while True:
            # Listen for one utterance
            text = stt_input.listen_once()
            
            if text:
                print(f"You said: {text}")
            
            # Check for exit command
            if text.lower() in ["quit", "exit"]:
                break
                
    except Exception as e:
        # This will catch errors, e.g., if the key file was not found.
        sic_logging.error(f"An error occurred during STT setup or execution: {e}")
        sic_logging.error("Please check your Google Cloud credentials and microphone setup.")

    finally:
        if 'stt_input' in locals() and stt_input:
            stt_input.close()
        print("--- STT Test Finished ---")
