import os
import wave
import tempfile
import numpy as np
import sounddevice as sd
from piper.voice import PiperVoice

class TTS:
    def __init__(self, model = "voices/cori/en_GB-cori-high.onnx"):
        self.voice = PiperVoice.load(model)

    def speak(self, text):
        # Create a temp path
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name

        # Open a Wave_write and pass THAT to synthesize_wav
        with wave.open(wav_path, "wb") as wf:
            self.voice.synthesize_wav(text, wf)
        
        print(f"[TTS SAYS] {text}")
        # Playback
        with wave.open(wav_path, "rb") as wf:
            samplerate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16)

        sd.play(audio, samplerate)
        sd.wait()

        # Clean up
        os.remove(wav_path)