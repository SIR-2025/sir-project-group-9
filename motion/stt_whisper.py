# -*- coding: utf-8 -*-

"""
This script provides a standalone speech-to-text (STT) capability using Whisper.

It is based on the demo_desktop_microphone_whisper.py example and is configured
to be easy to run.

IMPORTANT - Prerequisites:
1. Install dependencies:
   pip install --upgrade "social-interaction-cloud[whisper-speech-to-text]"

2. Run the Whisper service in a SEPARATE terminal before starting this script:
   run-whisper
"""

import time
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging
from sic_framework.devices.desktop import Desktop
from sic_framework.services.openai_whisper_stt.whisper_stt import \
    (GetTranscript,
    SICWhisper,
    WhisperConf)

class StandaloneWhisperSTT(SICApplication):
    """
    A standalone application for transcribing speech from the microphone using Whisper.
    """

    def __init__(self):
        super(StandaloneWhisperSTT, self).__init__()
        self.desktop = None
        self.whisper = None
        self.set_log_level(sic_logging.INFO)
        self.setup_stt()

    def setup_stt(self):
        """Initializes the desktop microphone and the Whisper STT service."""
        self.logger.info("Setting up Whisper STT...")

        # Initialize the desktop to access the microphone
        self.desktop = Desktop()

        # Configure Whisper to use the local model.
        # This does not require an OpenAI API key.
        # For higher accuracy, you can switch to the API version by providing a key.
        # See commented out code below.
        self.logger.info("Using local Whisper model.")
        self.whisper = SICWhisper(input_source=self.desktop.mic)

        # --- To use the OpenAI API version (requires API key) ---
        # from os import environ
        # from os.path import abspath, join
        # from dotenv import load_dotenv
        # 
        # # Make sure you have a .env file with OPENAI_API_KEY="your-key"
        # # or that the key is in your system environment variables.
        # env_path = abspath(join("..", "..", "conf", ".env")) # Adjust path if needed
        # load_dotenv(env_path)
        # if "OPENAI_API_KEY" not in environ:
        #     raise RuntimeError("OpenAI API key not found. Please check your .env file or environment variables.")
        # 
        # self.logger.info("Using OpenAI Whisper API.")
        # whisper_conf = WhisperConf(openai_key=environ["OPENAI_API_KEY"])
        # self.whisper = SICWhisper(input_source=self.desktop.mic, conf=whisper_conf)
        # ---------------------------------------------------------

        # Give the service a moment to initialize
        time.sleep(2)
        self.logger.info("Whisper STT is ready.")

    def run(self):
        """Main application loop to continuously listen and transcribe."""
        self.logger.info("Starting Standalone Whisper STT Application.")
        print("\n--- Whisper STT is running ---")
        print("Speak into your microphone. Say 'quit' to exit.")

        try:
            while not self.shutdown_event.is_set():
                print("\nListening...")
                # Request a transcript. This will block until speech is detected.
                # timeout: max duration to wait for speech
                # phrase_time_limit: max duration of the speech itself
                response = self.whisper.request(GetTranscript(timeout=20, phrase_time_limit=30))

                if response and response.transcript:
                    transcript = response.transcript.strip()
                    print(f"Heard: {transcript}")

                    if transcript.lower() == "quit":
                        self.logger.info("'quit' received. Shutting down.")
                        break
                else:
                    self.logger.warning("No transcript received or speech not recognized.")

        except Exception as e:
            self.logger.error(f"An error occurred: {e}", exc_info=True)
        finally:
            self.stop_app()

if __name__ == "__main__":
    # Create and run the STT application
    app = StandaloneWhisperSTT()
    app.run()
