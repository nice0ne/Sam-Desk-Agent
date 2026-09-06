import os
import tempfile
import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


class TTSEngine:
    def __init__(self, default_voice: str = "id-ID-ArdiNeural", rate: str = "+0%"):
        self.default_voice = default_voice
        self.rate = rate

    async def generate_audio_file(self, text: str, output_path: str, voice: Optional[str] = None) -> str:
        target_voice = voice or self.default_voice
        import edge_tts
        communicate = edge_tts.Communicate(text, target_voice, rate=self.rate)
        await communicate.save(output_path)
        return output_path

    async def speak(self, text: str, voice: Optional[str] = None) -> None:
        target_voice = voice or self.default_voice
        import edge_tts

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_path = fp.name

        try:
            communicate = edge_tts.Communicate(text, target_voice, rate=self.rate)
            await communicate.save(temp_path)

            # Play audio file via Windows PowerShell / Media Player
            uri = "file:///" + temp_path.replace("\\", "/")
            try:
                cmd = (
                    "Add-Type -AssemblyName presentationCore; "
                    "$p = New-Object System.Windows.Media.MediaPlayer; "
                    f"$p.Open([System.Uri]'{uri}'); "
                    "$p.Play(); "
                    "$t = 0; "
                    "while ((-not $p.NaturalDuration.HasTimeSpan) -and ($t -lt 50)) { "
                    "  Start-Sleep -Milliseconds 100; "
                    "  $t++; "
                    "}; "
                    "if ($p.NaturalDuration.HasTimeSpan) { "
                    "  $ms = [int]($p.NaturalDuration.TimeSpan.TotalMilliseconds); "
                    "  Start-Sleep -Milliseconds ($ms + 300); "
                    "} else { "
                    "  Start-Sleep -Seconds 3; "
                    "}; "
                    "$p.Close();"
                )
                subprocess.run(
                    ["powershell", "-NoProfile", "-c", cmd],
                    capture_output=True,
                    timeout=30,
                )
            except Exception as play_err:
                logger.warning(f"Audio playback error: {play_err}")
        except Exception as e:
            logger.error(f"TTS speak failed: {e}")
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
