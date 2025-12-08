import whisper
import sounddevice as sd
import numpy as np
import keyboard
import os

# 禁用 sounddevice 的调试信息
os.environ['PYTHON_SOUNDDEVICE_PLATFORM'] = 'dummy'

# --- Configuration ---
MODEL_TYPE = "base.en"  # Whisper model type (e.g., "tiny.en", "base.en", "small.en")
SAMPLE_RATE = 16000     # Sample rate for audio recording (Whisper requires 16k)

class DirectWhisperSTT:
    """
    A standalone Speech-To-Text class using OpenAI's Whisper directly.
    It listens for a hotkey press to record audio from the microphone and
    transcribes it upon release.
    """

    def __init__(self):
        """
        Initializes the STT class, loading the Whisper model.
        """
        print("Loading local Whisper model for testing...")
        try:
            self.model = whisper.load_model(MODEL_TYPE)
            print(f"Whisper '{MODEL_TYPE}' model loaded.")
        except Exception as e:
            print(f"Error loading Whisper model: {e}")
            print("Please ensure you have run: pip install openai-whisper")
            raise

    def listen_and_transcribe(self):
        """
        Main loop to listen for the record hotkey and transcribe audio.
        """
        print("\n--- Local Whisper STT Test ---")
        print("Press and HOLD the 'r' key to start recording.")
        print("RELEASE the 'r' key to stop and transcribe.")
        print("Press 'q' when not recording to QUIT.")

        while True:
            print("\nWaiting for hotkey...")
            keyboard.wait('r')  # Wait until 'r' is pressed

            if keyboard.is_pressed('q'):
                print("Quit key detected. Exiting.")
                break

            print("Recording... (Release 'r' to stop)")
            audio_data = []

            try:
                with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32') as stream:
                    while keyboard.is_pressed('r'):
                        data, overflowed = stream.read(SAMPLE_RATE) # Read 1 second of audio
                        if overflowed:
                            print("Warning: Audio buffer overflowed!")
                        audio_data.append(data)
            except Exception as e:
                print(f"Error during recording: {e}")
                continue

            if not audio_data:
                print("No audio recorded.")
                continue

            print("Recording stopped. Processing audio...")
            full_audio = np.concatenate(audio_data).flatten()

            try:
                # Transcribe the raw audio data
                result = self.model.transcribe(full_audio, fp16=False)
                transcript = result['text'].strip()

                if transcript:
                    print(f"Heard: {transcript}")
                else:
                    print("Could not understand audio or speech was empty.")
            except Exception as e:
                print(f"Transcription failed: {e}")

if __name__ == '__main__':
    print("This script is a LOCAL test for Whisper STT using your computer's microphone.")
    print("Please ensure you have the required libraries installed:")
    print("--> pip install openai-whisper sounddevice numpy keyboard")

    try:
        stt = DirectWhisperSTT()
        stt.listen_and_transcribe()
    except Exception as e:
        print(f"\nAn error occurred during setup: {e}")
        print("Please check that all required libraries are installed correctly.")
