"""Natural human-like text-to-speech service using edge-tts.

Edge-TTS uses Microsoft's neural network voices for lifelike, human-quality
speech synthesis without requiring an API key. Falls back gracefully to the
system TTS if edge-tts is unavailable.
"""

from __future__ import annotations

import asyncio
import platform
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Optional

from config.settings import TTS_VOICE, TTS_RATE, TTS_VOLUME
from src.core.logger import activity_logger


class TTSService:
    """Generate natural human-like speech from text."""

    def __init__(self, voice: str = TTS_VOICE, rate: str = TTS_RATE, volume: str = TTS_VOLUME) -> None:
        self._voice = voice
        self._rate = rate
        self._volume = volume
        self._edge_available = self._check_edge_tts()
        self._current_process: Optional[subprocess.Popen] = None
        self._play_lock = threading.Lock()

    def _check_edge_tts(self) -> bool:
        """Check if edge-tts is installed and usable."""
        try:
            import edge_tts
            return True
        except ImportError:
            activity_logger.log("edge-tts not installed; falling back to system TTS", category="VOICE", level="INFO")
            return False

    @property
    def is_available(self) -> bool:
        return self._edge_available

    @property
    def voice_name(self) -> str:
        return self._voice

    def _play_audio(self, audio_path: Path) -> bool:
        """Play an audio file using the best available player."""
        system = platform.system()
        try:
            if system == "Windows":
                proc = subprocess.Popen(
                    ["powershell", "-Command",
                     f"(New-Object Media.SoundPlayer '{audio_path}').PlaySync()"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                with self._play_lock:
                    self._current_process = proc
                proc.wait()
                return True
            elif system == "Darwin":
                proc = subprocess.Popen(["afplay", str(audio_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                with self._play_lock:
                    self._current_process = proc
                proc.wait()
                return True
            else:
                for player in ["aplay", "paplay", "ffplay", "mpv"]:
                    if self._has_shutil(player):
                        proc = subprocess.Popen([player, str(audio_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        with self._play_lock:
                            self._current_process = proc
                        proc.wait()
                        return True
            return False
        except Exception as exc:
            activity_logger.log(f"Audio playback error: {exc}", category="VOICE", level="WARNING")
            return False

    def stop(self) -> None:
        """Stop any in-progress TTS playback."""
        with self._play_lock:
            if self._current_process and self._current_process.poll() is None:
                try:
                    self._current_process.terminate()
                except Exception:
                    pass
            self._current_process = None

    def _has_shutil(self, binary: str) -> bool:
        import shutil
        return shutil.which(binary) is not None

    def speak_edge(self, text: str) -> bool:
        """Synthesize speech using edge-tts neural voices."""
        if not self._edge_available:
            return False
        try:
            import edge_tts
            temp_dir = Path(tempfile.gettempdir())
            audio_path = temp_dir / f"voicebot_{abs(hash(text)) % 100000}.mp3"

            asyncio.run(
                edge_tts.Communicate(
                    text=text,
                    voice=self._voice,
                    rate=self._rate,
                    volume=self._volume,
                ).save(str(audio_path))
            )
            played = self._play_audio(audio_path)
            try:
                audio_path.unlink(missing_ok=True)
            except Exception:
                pass
            return played
        except Exception as exc:
            activity_logger.log(f"edge-tts synthesis error: {exc}", category="VOICE", level="WARNING")
            return False

    def speak(self, text: str) -> bool:
        """Speak text using the best available TTS backend."""
        if not text:
            return False
        if self.speak_edge(text):
            return True
        return self._speak_system(text)

    def generate_audio(self, text: str) -> Optional[Path]:
        """Generate speech audio via edge-tts and return the file path.

        Returns the path to a temporary MP3 file, or None on failure.
        The caller is responsible for cleaning up the file.
        """
        if not text or not self._edge_available:
            return None
        try:
            import edge_tts
            temp_dir = Path(tempfile.gettempdir())
            audio_path = temp_dir / f"voicebot_tts_{abs(hash(text)) % 100000}.mp3"

            asyncio.run(
                edge_tts.Communicate(
                    text=text,
                    voice=self._voice,
                    rate=self._rate,
                    volume=self._volume,
                ).save(str(audio_path))
            )
            return audio_path if audio_path.exists() else None
        except Exception as exc:
            activity_logger.log(f"edge-tts generation error: {exc}", category="VOICE", level="WARNING")
            return None

    def _speak_system(self, text: str) -> bool:
        """Fallback to system TTS via command-line utilities."""
        system = platform.system()
        try:
            if system == "Windows":
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty("rate", 170)
                engine.setProperty("volume", 1.0)
                engine.say(text)
                engine.runAndWait()
                return True
            elif system == "Darwin":
                subprocess.Popen(["say", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            else:
                for tts in ["espeak-ng", "espeak"]:
                    if self._has_shutil(tts):
                        subprocess.Popen([tts, "-v", "en", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        return True
            return False
        except Exception as exc:
            activity_logger.log(f"System TTS error: {exc}", category="VOICE", level="WARNING")
            return False


# Global singleton
tts_service = TTSService()
