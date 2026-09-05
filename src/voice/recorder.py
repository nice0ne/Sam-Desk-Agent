import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)


class AudioRecorder:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.is_recording = False

    def start(self) -> None:
        self.is_recording = True

    def stop(self) -> None:
        self.is_recording = False

    def record_chunk(self, duration_sec: float = 3.0) -> np.ndarray:
        frames = int(duration_sec * self.sample_rate)
        try:
            import sounddevice as sd
            recording = sd.rec(
                frames,
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32"
            )
            sd.wait()
            if recording is not None:
                return recording.flatten().astype(np.float32)
            return np.zeros(frames, dtype=np.float32)
        except Exception as e:
            logger.warning(
                f"Audio recording failed or sounddevice unavailable: {e}. "
                "Falling back to mock silent array."
            )
            return np.zeros(frames, dtype=np.float32)
