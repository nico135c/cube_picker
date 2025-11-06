import pyttsx3
import re
import threading
import time

class BlockingTTS:
    def __init__(self, driver=None, rate=None, voice=None):
        """Initialize the TTS engine."""
        self.engine = pyttsx3.init(driverName=driver)
        if rate is not None:
            self.engine.setProperty("rate", rate)
        if voice is not None:
            self.engine.setProperty("voice", voice)

    def _split_text(self, text, limit=180):
        """Split long text into safe chunks."""
        parts = [p.strip() for p in re.split(r'([.!?]+)\s+', text)]
        sentences = []
        for i in range(0, len(parts), 2):
            s = parts[i] + (parts[i + 1] if i + 1 < len(parts) else "")
            if s.strip():
                sentences.append(s.strip())

        chunks, buf = [], ""
        for s in sentences:
            if len(buf) + len(s) <= limit:
                buf = (buf + " " + s).strip()
            else:
                if buf:
                    chunks.append(buf)
                buf = s
        if buf:
            chunks.append(buf)
        return chunks

    def speak(self, text):
        """Speak text and block until done."""
        print(f"[TTS SAYS] {text}")
        chunks = self._split_text(text)
        done = threading.Event()

        def _on_finished(name, completed):
            if name == "last":
                done.set()

        self.engine.connect("finished-utterance", _on_finished)

        for i, chunk in enumerate(chunks):
            name = "last" if i == len(chunks) - 1 else f"utt-{i}"
            self.engine.say(chunk, name=name)

        # Run and block
        self.engine.runAndWait()

        # Ensure we truly wait until done
        if not done.is_set():
            for _ in range(5000):
                if done.is_set() or not self.engine.isBusy():
                    break
                time.sleep(0.01)

        self.engine.stop()

    def set_rate(self, rate):
        self.engine.setProperty("rate", rate)

    def set_voice(self, voice):
        self.engine.setProperty("voice", voice)

    def list_voices(self):
        return [v.name for v in self.engine.getProperty("voices")]