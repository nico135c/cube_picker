from gtts import gTTS
from playsound import playsound
import tempfile
import re
import os

class BlockingTTS:
    def __init__(self, lang="en", tld="com", slow=False):
        """
        lang: language code ('en', 'en-au', 'en-gb', etc.)
        tld: google domain (e.g. 'com', 'co.uk', 'ca', 'in') affects accent
        slow: True for slower speech
        """
        self.lang = lang
        self.tld = tld
        self.slow = slow

    def _split_text(self, text, limit=200):
        """Split text into chunks that gTTS can handle safely."""
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
        """Speak text synchronously with natural voice."""
        print(f"[TTS SAYS] {text}")
        chunks = self._split_text(text)
        for i, chunk in enumerate(chunks):
            tts = gTTS(chunk, lang=self.lang, tld=self.tld, slow=self.slow)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                tts.save(fp.name)
                playsound(fp.name)
                os.unlink(fp.name)
