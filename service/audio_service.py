import numpy as np
from io import BytesIO
from pydub import AudioSegment
import sounddevice as sd

class AudioPlayer:
    """负责播放 MP3 音频"""

    def __init__(self, mp3_bytes: bytes, format="mp3"):
        self.mp3_bytes = mp3_bytes
        self.format = format
        self.is_converted = False
        self.samples = np.empty(shape=(1,))
        self.frame_rate = 0

    def _convert_to_array(self, audio):
        samples = np.array(audio.get_array_of_samples())
        if audio.channels == 2:
            samples = samples.reshape((-1, 2))
        return samples / 2**15

    def convert_audio(self):
        if not self.is_converted and self.mp3_bytes:
            audio = AudioSegment.from_file(BytesIO(self.mp3_bytes), format=self.format)
            self.samples = self._convert_to_array(audio)
            self.frame_rate = audio.frame_rate
            self.is_converted = True

    def play(self, wait=False):
        self.convert_audio()
        sd.play(self.samples, samplerate=self.frame_rate)
        if wait:
            sd.wait()
