import discord
from utils.logger import logger

class SilentAudioSource(discord.AudioSource):
    """
    An optimized AudioSource that streams silent PCM audio to Discord.
    Provides 20ms chunks (3840 bytes) of stereo 16-bit 48kHz PCM silence.
    By returning a pre-allocated reference, it eliminates CPU overhead and garbage collection thrashing.
    """
    def __init__(self):
        super().__init__()
        # Pre-allocate 20ms of stereo PCM silence: 48000Hz * 2 channels * 2 bytes/sample * 0.02s = 3840 bytes
        self._silence_frame = b'\x00' * 3840
        self._check_opus()

    def _check_opus(self):
        """Verifies if the system's Opus library is loaded (required by discord.py voice)."""
        try:
            if not discord.opus.is_loaded():
                logger.warning("Opus library is not loaded. Voice transmission might fail unless libopus is available on your system.")
            else:
                logger.debug("Opus library loaded successfully.")
        except Exception as e:
            logger.error(f"Error checking Opus library state: {e}")

    def read(self) -> bytes:
        """Returns 20ms of silence."""
        return self._silence_frame

    def is_opus(self) -> bool:
        """Returns False because we output raw PCM, not Opus-encoded data."""
        return False

    def cleanup(self):
        """No resources to release, clean cleanup."""
        pass
