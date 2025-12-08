import whisper
import numpy as np
from sic_framework.core.message_python2 import AudioMessage, SICMessage
from sic_framework.core.service_python2 import Service
from sic_framework.core.connector import SICConnector

class WhisperRequest(SICMessage):
    """
    Message to request a transcription. Contains the audio data.
    """
    def __init__(self, audio_data):
        super(WhisperRequest, self).__init__()
        # Audio data should be a numpy array
        self.audio_data = audio_data

class WhisperService(Service):
    """
    A SIC service that uses OpenAI's Whisper to transcribe audio.
    """
    def __init__(self, *args, **kwargs):
        super(WhisperService, self).__init__(*args, **kwargs)
        self.model = None

    def on_message(self, message):
        """
        Handles incoming WhisperRequest messages.
        """
        if isinstance(message, WhisperRequest):
            print("WhisperService: Received audio, transcribing...")
            # Whisper expects a 1D numpy array (float32)
            audio_np = message.audio_data.flatten().astype(np.float32)

            result = self.model.transcribe(audio_np, fp16=False)
            transcript = result['text'].strip()
            print(f"WhisperService: Transcription result: '{transcript}'")
            self.send_message(transcript) # Send the text back to the requester

    def on_start(self):
        print("WhisperService: Loading model...")
        self.model = whisper.load_model("base.en")
        print("WhisperService: Model loaded.")