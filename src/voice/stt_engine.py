import logging
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class STTEngine:
    """Speech-to-Text Engine supporting Google Web Speech API and local Whisper."""

    def __init__(
        self,
        provider: str = "google",
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str = "id",
        google_api_key: Optional[str] = None,
    ):
        self.provider = provider
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.google_api_key = google_api_key
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

    def _get_google_lang(self) -> str:
        lang = self.language.strip()
        if lang.lower() in ("id", "id-id"):
            return "id-ID"
        elif lang.lower() in ("en", "en-us"):
            return "en-US"
        return lang

    def _transcribe_google(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        try:
            import speech_recognition as sr
        except ImportError:
            logger.warning("speech_recognition module not found. Google STT unavailable.")
            return ""

        try:
            # Convert float32 [-1.0, 1.0] to 16-bit PCM bytes
            pcm_bytes = (np.clip(audio_data, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
            audio = sr.AudioData(pcm_bytes, sample_rate=sample_rate, sample_width=2)
            recognizer = sr.Recognizer()
            lang = self._get_google_lang()
            kwargs = {"language": lang}
            if self.google_api_key:
                kwargs["key"] = self.google_api_key
            text = recognizer.recognize_google(audio, **kwargs)
            return text.strip() if text else ""
        except getattr(sr, "UnknownValueError", Exception):
            logger.debug("Google STT: Tidak ada ucapan yang terdeteksi.")
            return ""
        except getattr(sr, "RequestError", Exception) as e:
            logger.error(f"Google STT request error: {e}")
            return ""
        except Exception as e:
            logger.error(f"Google STT transcription error: {e}")
            return ""

    def _transcribe_whisper(self, audio_data: np.ndarray) -> str:
        model = self._load_model()
        if model is None:
            return ""
        try:
            lang = "id" if self.language.lower().startswith("id") else self.language
            segments, _ = model.transcribe(audio_data, language=lang)
            text = " ".join([seg.text.strip() for seg in segments if hasattr(seg, "text") and seg.text]).strip()
            return text
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return ""

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        if audio_data is None or len(audio_data) == 0:
            return ""

        if not isinstance(audio_data, np.ndarray):
            audio_data = np.array(audio_data, dtype=np.float32)
        elif audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # If a mock/loaded model exists explicitly on the instance, prioritize it
        if self._model is not None:
            return self._transcribe_whisper(audio_data)

        if self.provider == "google":
            return self._transcribe_google(audio_data, sample_rate=sample_rate)

        if self.provider == "whisper":
            return self._transcribe_whisper(audio_data)

        # "auto" mode: try whisper first if installed, else fallback to google
        whisper_model = self._load_model()
        if whisper_model is not None:
            text = self._transcribe_whisper(audio_data)
            if text:
                return text

        # Fallback to Google Web Speech API
        return self._transcribe_google(audio_data, sample_rate=sample_rate)
