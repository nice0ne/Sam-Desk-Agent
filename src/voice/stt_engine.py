import logging
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class STTEngine:
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "id"
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model = None
        self._load_attempted = False

    def _load_model(self):
        if self._model is not None:
            return self._model
        if self._load_attempted:
            return None
        self._load_attempted = True
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            return self._model
        except Exception as e:
            logger.warning(
                f"faster-whisper WhisperModel could not be loaded ({e}). "
                "Using fallback mode."
            )
            return None

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        if audio_data is None or len(audio_data) == 0:
            return ""

        if not isinstance(audio_data, np.ndarray):
            audio_data = np.array(audio_data, dtype=np.float32)
        elif audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        model = self._load_model()
        if model is None:
            return ""

        try:
            segments, _ = model.transcribe(audio_data, language=self.language)
            text = " ".join([seg.text.strip() for seg in segments if hasattr(seg, "text") and seg.text]).strip()
            return text
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
