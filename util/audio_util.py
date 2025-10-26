
from io import BytesIO

import numpy as np
import time

# Optional: TTS and audio playback helpers
try:
    from gtts import gTTS, gTTSError
except Exception:
    gTTS = None

try:
    from pydub import AudioSegment
    import sounddevice as sd
except Exception:
    raise "pydub lib is found"


def token2voice(text, retries=3, base_sleep=1) -> bytes:
    """Return mp3 bytes for the given text using gTTS if available.
    If gTTS isn't available or fails, return None.
    """
    if gTTS is None:
        return b""
    mp3_io = BytesIO()
    for attempt in range(1, retries + 1):
        try:
            tts = gTTS(text=text.strip(), lang='en', tld='co.uk')
            for decoded in tts.stream():
                mp3_io.write(decoded)
            mp3_io.flush()
            return mp3_io.getvalue()
        except gTTSError as e:
            if attempt < retries:
                time.sleep(base_sleep * (2 ** (attempt - 1)))
            else:
                print(f"token2voice error: {e}")
    
    return b""

def play_voice(mp3_bytes:bytes, format="mp3", is_wait=False):
    """Play mp3 bytes. Use pydub if available, otherwise write to temp file and
    try to open with default system player as a fallback.
    """
    if not mp3_bytes:
        return
    
    audio = AudioSegment.from_file(BytesIO(mp3_bytes), format=format)
    samples = _voice2np(audio)
    sd.play(samples, samplerate=audio.frame_rate)
    if is_wait:
        sd.wait()

def _voice2np(audio:AudioSegment):
    if not audio:
        return
    
    samples = np.frombuffer(audio.get_array_of_samples(), dtype=np.float32)
    if audio.channels == 2:
        samples = samples.reshape((-1,2))
    return samples / 2**15