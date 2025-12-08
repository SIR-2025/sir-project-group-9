import whisper
print(f"Whisper module loaded from: {whisper.__file__}")
import sounddevice as sd
import numpy as np
import keyboard

# --- Configuration ---
MODEL_TYPE = "base.en"  # Whisper model type (e.g., "tiny.en", "base.en", "small.en")
SAMPLE_RATE = 16000     # Sample rate for audio recording (Whisper requires 16k)
CHANNELS = 1            # Mono audio
BLOCK_DURATION_S = 1    # Duration in seconds for each audio block read from the stream

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
        print("Loading Whisper model...")
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
        print("\n--- Direct Whisper STT ---")
        print("Press and HOLD the 'r' key to start recording.")
        print("RELEASE the 'r' key to stop and transcribe.")
        print("Press 'q' when not recording to QUIT.")

        while True:
            print("\nWaiting for hotkey...")
            keyboard.wait('r')  # Wait until 'r' is pressed

            # Check for quit condition immediately after 'r' is detected
            # This is a bit of a race condition, but works for simple cases
            if keyboard.is_pressed('q'):
                print("Quit key detected. Exiting.")
                break

            print("Recording... (Release 'r' to stop)")
            audio_data = []
            
            try:
                # Record audio while 'r' is held down
                with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='float32') as stream:
                    while keyboard.is_pressed('r'):
                        data, overflowed = stream.read(int(SAMPLE_RATE * BLOCK_DURATION_S))
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
            # Concatenate audio chunks and ensure it's a 1D array (flatten)
            full_audio = np.concatenate(audio_data).flatten()

            try:
                # Transcribe the raw audio data directly from the NumPy array, bypassing ffmpeg
                result = self.model.transcribe(full_audio, fp16=False)
                transcript = result['text'].strip()

                if transcript:
                    print(f"Heard: {transcript}")
                else:
                    print("Could not understand audio or speech was empty.")
            except Exception as e:
                print(f"Transcription failed: {e}")

if __name__ == '__main__':
    print("This script uses Whisper for STT directly.")
    print("Please ensure you have the required libraries installed:")
    print("--> pip install openai-whisper sounddevice numpy scipy keyboard")
    
    try:
        stt = DirectWhisperSTT()
        stt.listen_and_transcribe()
    except Exception as e:
        print(f"\nAn error occurred during setup: {e}")
        print("Please check that all required libraries are installed correctly.")
