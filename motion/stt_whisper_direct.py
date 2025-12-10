import sounddevice as sd
import numpy as np
import collections
import time
import openai
import os
import io
import soundfile as sf

# --- Configuration ---
SAMPLE_RATE = 16000         # Whisper requires 16k Hz
CHANNELS = 1                # Mono audio
BLOCK_SIZE = 2048           # Number of frames per buffer

# --- VAD (Voice Activity Detection) Configuration ---
VAD_THRESHOLD = 0.01        # RMS volume threshold to start recording. Adjust based on your mic sensitivity.
VAD_PRE_BUFFER_S = 1        # Seconds of audio to keep before speech starts (to catch the beginning of words)
VAD_POST_BUFFER_S = 0.7     # Seconds of silence to wait for before stopping recording

class VADWhisperSTT:
    """
    A Speech-To-Text class using OpenAI's Whisper API, with Voice Activity Detection (VAD).

    It automatically detects when a user starts speaking, records their speech,
    and transcribes it after they stop talking using the OpenAI API.
    """
    def __init__(self, client: openai.Client):
        """
        Initializes the STT class.
        """
        if not client:
            raise ValueError("An OpenAI client must be provided.")
        self.client = client
        print("[STT] VADWhisperSTT initialized with OpenAI client.")

        # VAD state variables
        self.is_recording = False
        self.recorded_audio = []
        
        # Calculate buffer sizes in terms of audio blocks
        self.post_silence_blocks = int((VAD_POST_BUFFER_S * SAMPLE_RATE) / BLOCK_SIZE)
        self.pre_buffer_blocks = int((VAD_PRE_BUFFER_S * SAMPLE_RATE) / BLOCK_SIZE)
        
        # Ring buffer to hold audio before speech is detected
        self.pre_buffer = collections.deque(maxlen=self.pre_buffer_blocks)
        self.silence_counter = 0

    def _is_speech(self, block: np.ndarray) -> bool:
        """Calculate RMS of the audio block and check against threshold."""
        rms = np.sqrt(np.mean(block**2))
        return rms > VAD_THRESHOLD

    def _process_audio_stream(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """
        This callback is executed for each new audio block from the microphone.
        It implements a simple state machine for VAD.
        """
        if status:
            print(f"[STT] Warning: {status}")

        is_speech_now = self._is_speech(indata)

        if self.is_recording:
            # --- We are currently recording ---
            self.recorded_audio.append(indata.copy())
            
            if not is_speech_now:
                self.silence_counter += 1
                if self.silence_counter >= self.post_silence_blocks:
                    # End of speech detected, stop the stream
                    self.is_recording = False # Signal to stop
                    raise sd.CallbackStop
            else:
                # Reset silence counter if speech is detected again
                self.silence_counter = 0

        else:
            # --- We are waiting for speech to start ---
            if is_speech_now:
                print("[STT] Speech detected, starting recording...")
                self.is_recording = True
                self.silence_counter = 0
                # Add pre-buffer audio to the recording
                self.recorded_audio.extend(self.pre_buffer)
                self.recorded_audio.append(indata.copy())
            else:
                # Keep filling the pre-buffer
                self.pre_buffer.append(indata.copy())

    def listen_and_transcribe(self) -> str:
        """
        Listens for speech using VAD and returns the transcribed text.
        This is a blocking function.
        """
        self.recorded_audio = []
        self.pre_buffer.clear()
        self.is_recording = False
        self.silence_counter = 0

        print("\n[STT] Listening for speech... (speak when ready)")

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype='float32',
                blocksize=BLOCK_SIZE,
                callback=self._process_audio_stream
            ):
                while self.is_recording or len(self.recorded_audio) == 0:
                    time.sleep(0.1)
        except sd.CallbackStop:
            print("[STT] End of speech detected.")
        except Exception as e:
            print(f"[STT] Error during audio stream: {e}")
            return ""

        if not self.recorded_audio:
            print("[STT] No audio was recorded.")
            return ""

        print("[STT] Processing audio...")
        full_audio = np.concatenate(self.recorded_audio).flatten()
        
        # Save audio to an in-memory buffer as a FLAC file
        try:
            print("[STT] Compressing audio to FLAC in memory...")
            audio_buffer = io.BytesIO()
            sf.write(audio_buffer, full_audio, SAMPLE_RATE, format='FLAC')
            audio_buffer.seek(0) # Rewind the buffer to the beginning
            print("[STT] Audio compressed.")
        except Exception as e:
            print(f"[STT] Error creating in-memory audio buffer: {e}")
            return ""

        try:
            print("[STT] Sending audio to OpenAI API for transcription...")
            # The API client needs a file-like object with a name
            transcript_response = self.client.audio.transcriptions.create(
              model="whisper-1", 
              file=("audio.flac", audio_buffer)
            )
            print("[STT] Transcription received.")
            transcript = transcript_response.text.strip()

            if transcript:
                print(f"[STT] Heard: {transcript}")
                return transcript
            else:
                print("[STT] Could not understand audio or speech was empty.")
                return ""
        except Exception as e:
            print(f"[STT] Transcription failed: {e}")
            return ""

# --- Main execution for testing purposes ---
if __name__ == '__main__':
    print("This script demonstrates OpenAI Whisper STT with Voice Activity Detection (VAD).")
    print("It will automatically record when you speak and transcribe when you stop.")
    
    try:
        # NOTE: You need to have your OPENAI_API_KEY in your environment variables
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not found.")
            
        client = openai.OpenAI(api_key=api_key)
        stt = VADWhisperSTT(client=client)

        while True:
            print("\n--- Press Enter to start listening, or 'q' then Enter to quit ---")
            if input().lower() == 'q':
                break
            
            # This call will block until transcription is complete
            transcribed_text = stt.listen_and_transcribe()
            
            if transcribed_text:
                print(f"--> FINAL TRANSCRIPT: {transcribed_text}")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please check microphone permissions and library installations.")
        print("Required: pip install openai sounddevice numpy soundfile")