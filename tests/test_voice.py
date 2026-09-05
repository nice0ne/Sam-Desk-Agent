import os
import pytest
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch
from pynput import keyboard

from src.voice import (
    AudioRecorder,
    STTEngine,
    TTSEngine,
    GlobalHotkeyListener,
)
from src.core.safety import SafetySupervisor


# ============================================================================
# AudioRecorder Tests
# ============================================================================

def test_audio_recorder_defaults():
    recorder = AudioRecorder()
    assert recorder.sample_rate == 16000
    assert recorder.is_recording is False

    custom_recorder = AudioRecorder(sample_rate=44100)
    assert custom_recorder.sample_rate == 44100


def test_audio_recorder_start_stop():
    recorder = AudioRecorder()
    recorder.start()
    assert recorder.is_recording is True
    recorder.stop()
    assert recorder.is_recording is False


def test_audio_recorder_mock_capture_fallback():
    recorder = AudioRecorder(sample_rate=16000)
    # Simulate sounddevice raising an error (e.g., no hardware device in CI/test)
    with patch("sounddevice.rec", side_effect=Exception("No default input device")):
        chunk = recorder.record_chunk(duration_sec=0.5)
        assert isinstance(chunk, np.ndarray)
        assert chunk.shape == (8000,)
        assert chunk.dtype == np.float32
        assert np.all(chunk == 0.0)


def test_audio_recorder_with_mocked_sounddevice():
    recorder = AudioRecorder(sample_rate=16000)
    dummy_data = np.ones((1600, 1), dtype=np.float32) * 0.42

    with patch("sounddevice.rec", return_value=dummy_data) as mock_rec, \
         patch("sounddevice.wait") as mock_wait:
        chunk = recorder.record_chunk(duration_sec=0.1)
        mock_rec.assert_called_once_with(1600, samplerate=16000, channels=1, dtype="float32")
        mock_wait.assert_called_once()
        assert chunk.shape == (1600,)
        assert chunk[0] == pytest.approx(0.42)


# ============================================================================
# STTEngine Tests
# ============================================================================

def test_stt_engine_defaults():
    stt = STTEngine()
    assert stt.model_size == "base"
    assert stt.device == "cpu"
    assert stt.compute_type == "int8"
    assert stt.language == "id"


def test_stt_engine_custom_config():
    stt = STTEngine(model_size="small", device="cuda", compute_type="float16", language="en")
    assert stt.model_size == "small"
    assert stt.device == "cuda"
    assert stt.compute_type == "float16"
    assert stt.language == "en"


def test_stt_engine_empty_audio():
    stt = STTEngine()
    assert stt.transcribe(np.array([])) == ""
    assert stt.transcribe(None) == ""


def test_stt_engine_fallback_when_unavailable():
    stt = STTEngine()
    audio = np.zeros(1600, dtype=np.float32)
    # faster-whisper is not installed or raises ImportError
    with patch.dict("sys.modules", {"faster_whisper": None}):
        result = stt.transcribe(audio)
        assert result == ""


def test_stt_engine_with_mock_model():
    stt = STTEngine()
    audio = np.zeros(1600, dtype=np.float32)

    class MockSegment:
        def __init__(self, text):
            self.text = text

    mock_model = MagicMock()
    mock_model.transcribe.return_value = (
        [MockSegment("halo"), MockSegment("sam"), MockSegment("")],
        {"language": "id"}
    )
    stt._model = mock_model

    result = stt.transcribe(audio)
    assert result == "halo sam"
    mock_model.transcribe.assert_called_once()


def test_stt_engine_converts_dtype_and_handles_exception():
    stt = STTEngine()
    audio_int = np.zeros(100, dtype=np.int16)

    mock_model = MagicMock()
    mock_model.transcribe.side_effect = RuntimeError("GPU memory error")
    stt._model = mock_model

    result = stt.transcribe(audio_int)
    assert result == ""


# ============================================================================
# TTSEngine Tests
# ============================================================================

def test_tts_engine_defaults():
    tts = TTSEngine()
    assert tts.default_voice == "id-ID-ArdiNeural"
    assert tts.rate == "+0%"

    custom_tts = TTSEngine(default_voice="id-ID-GadisNeural", rate="+10%")
    assert custom_tts.default_voice == "id-ID-GadisNeural"
    assert custom_tts.rate == "+10%"


@pytest.mark.asyncio
async def test_tts_generate_audio_file(tmp_path):
    tts = TTSEngine()
    output_file = str(tmp_path / "output.mp3")

    mock_communicate = MagicMock()
    mock_communicate.save = AsyncMock(return_value=None)

    with patch("edge_tts.Communicate", return_value=mock_communicate) as mock_comm_cls:
        res = await tts.generate_audio_file("Halo dunia", output_file)
        assert res == output_file
        mock_comm_cls.assert_called_once_with("Halo dunia", "id-ID-ArdiNeural", rate="+0%")
        mock_communicate.save.assert_awaited_once_with(output_file)


@pytest.mark.asyncio
async def test_tts_speak_flow_and_cleanup():
    tts = TTSEngine()
    created_temp_files = []

    async def fake_save(path):
        created_temp_files.append(path)
        with open(path, "wb") as f:
            f.write(b"fake_mp3_data")

    mock_communicate = MagicMock()
    mock_communicate.save = AsyncMock(side_effect=fake_save)

    with patch("edge_tts.Communicate", return_value=mock_communicate), \
         patch("subprocess.run") as mock_subproc:
        await tts.speak("Tes suara", voice="id-ID-GadisNeural")
        assert len(created_temp_files) == 1
        temp_file = created_temp_files[0]
        # Verify subprocess was called to play sound
        mock_subproc.assert_called_once()
        # Verify temporary mp3 file was cleaned up
        assert not os.path.exists(temp_file)


@pytest.mark.asyncio
async def test_tts_speak_handles_playback_exception():
    tts = TTSEngine()
    mock_communicate = MagicMock()
    mock_communicate.save = AsyncMock(return_value=None)

    with patch("edge_tts.Communicate", return_value=mock_communicate), \
         patch("subprocess.run", side_effect=Exception("Playback device busy")):
        # Should not raise exception
        await tts.speak("Tes exception")


# ============================================================================
# GlobalHotkeyListener Tests
# ============================================================================

def test_hotkey_listener_initialization():
    callback = MagicMock()
    safety = SafetySupervisor()
    listener = GlobalHotkeyListener(
        on_trigger=callback,
        safety_supervisor=safety,
        hotkey_str="<ctrl>+<shift>+s"
    )
    assert listener.on_trigger == callback
    assert listener.safety == safety
    assert listener.hotkey_str == "<ctrl>+<shift>+s"
    assert listener.is_running is False


def test_hotkey_listener_esc_panic_trigger():
    callback = MagicMock()
    safety = SafetySupervisor(window_seconds=1.0, required_presses=3)
    listener = GlobalHotkeyListener(on_trigger=callback, safety_supervisor=safety)

    # Press 1
    listener._on_esc_press(keyboard.Key.esc)
    assert safety.is_cancelled() is False

    # Press 2
    listener._on_esc_press(keyboard.Key.esc)
    assert safety.is_cancelled() is False

    # Press 3 -> triggers panic
    listener._on_esc_press(keyboard.Key.esc)
    assert safety.is_cancelled() is True


def test_hotkey_listener_ignores_other_keys():
    callback = MagicMock()
    safety = SafetySupervisor()
    listener = GlobalHotkeyListener(on_trigger=callback, safety_supervisor=safety)

    listener._on_esc_press(keyboard.Key.space)
    listener._on_esc_press(keyboard.KeyCode(char="a"))
    assert len(safety._esc_timestamps) == 0
    assert safety.is_cancelled() is False


def test_hotkey_listener_esc_press_without_safety():
    callback = MagicMock()
    listener = GlobalHotkeyListener(on_trigger=callback, safety_supervisor=None)
    # Should not raise exception when safety is None
    listener._on_esc_press(keyboard.Key.esc)


def test_hotkey_listener_start_and_stop():
    callback = MagicMock()
    safety = SafetySupervisor()
    listener = GlobalHotkeyListener(on_trigger=callback, safety_supervisor=safety)

    mock_hotkeys = MagicMock()
    mock_esc_listener = MagicMock()

    with patch("pynput.keyboard.GlobalHotKeys", return_value=mock_hotkeys) as mock_ghk_cls, \
         patch("pynput.keyboard.Listener", return_value=mock_esc_listener) as mock_l_cls:
        listener.start()
        assert listener.is_running is True
        mock_ghk_cls.assert_called_once_with({listener.hotkey_str: callback})
        mock_hotkeys.start.assert_called_once()
        mock_l_cls.assert_called_once()
        mock_esc_listener.start.assert_called_once()

        # Duplicate start does nothing
        listener.start()
        assert mock_hotkeys.start.call_count == 1

        # Stop
        listener.stop()
        assert listener.is_running is False
        mock_hotkeys.stop.assert_called_once()
        mock_esc_listener.stop.assert_called_once()


def test_hotkey_listener_trigger_callback():
    triggered = []

    def on_hit():
        triggered.append(True)

    listener = GlobalHotkeyListener(on_trigger=on_hit)
    listener.on_trigger()
    assert triggered == [True]
