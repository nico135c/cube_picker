import argparse
import queue
import sys
import sounddevice as sd
from vosk import Model, KaldiRecognizer

class VoskSTT:
    def __init__(self):
        self.q = queue.Queue()
        self.device = 6
        devinfo = sd.query_devices(self.device, 'input')
        self.samplerate = int(devinfo['default_samplerate'])
        self.blocksize = 100
        # for windows
        # self.samplerate = int(sd.query_devices(None, "input")["default_samplerate"])
        # self.device = None
        self.model = Model(lang="en-us")

    def int_or_str(self, text):
        """Helper function for argument parsing."""
        try:
            return int(text)
        except ValueError:
            return text

    def callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def speech_to_text_vosk(self):
        print(f"[VOSK STT] Speech-to-text listening!")
        with sd.RawInputStream(samplerate=self.samplerate, blocksize=self.blocksize, device=self.device,
                               dtype="int16", channels=1, callback=self.callback):
            rec = KaldiRecognizer(self.model, self.samplerate)

            stt_results = ""
            while True:
                data = self.q.get()
                if rec.AcceptWaveform(data):
                    stt_results = rec.Result().split('"')[1::2][1]
                    if (stt_results != "") and (stt_results != 'huh'):
                        break
            
            print(f"[VOSK STT] Speech-to-text done listening!")
            return stt_results

