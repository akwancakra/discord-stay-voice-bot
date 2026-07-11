import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Project Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = DATA_DIR / "config.json"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Default configuration settings
DEFAULT_CONFIG = {
    "prefix": "st",
    "guild_id": None,
    "voice_channel_id": None,
    "play_silence": True,
    "auto_reconnect": True
}

class BotConfig:
    def __init__(self):
        self.token = os.getenv("DISCORD_TOKEN")
        self.config_data = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        """Loads configuration from data/config.json if it exists."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                    # Merge loaded data with defaults to ensure all keys exist
                    for key, val in DEFAULT_CONFIG.items():
                        self.config_data[key] = loaded_data.get(key, val)
            except Exception as e:
                print(f"[Config Error] Failed to read config.json: {e}. Using defaults.")
        else:
            self.save()

    def save(self):
        """Saves current configuration to data/config.json."""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=4)
        except Exception as e:
            print(f"[Config Error] Failed to save config.json: {e}")

    # Helper getters/setters for configuration values
    @property
    def prefix(self) -> str:
        return self.config_data.get("prefix", "!")

    @prefix.setter
    def prefix(self, val: str):
        self.config_data["prefix"] = val
        self.save()

    @property
    def guild_id(self) -> int:
        val = self.config_data.get("guild_id")
        return int(val) if val is not None else None

    @guild_id.setter
    def guild_id(self, val: int):
        self.config_data["guild_id"] = val
        self.save()

    @property
    def voice_channel_id(self) -> int:
        val = self.config_data.get("voice_channel_id")
        return int(val) if val is not None else None

    @voice_channel_id.setter
    def voice_channel_id(self, val: int):
        self.config_data["voice_channel_id"] = val
        self.save()

    @property
    def play_silence(self) -> bool:
        return bool(self.config_data.get("play_silence", True))

    @play_silence.setter
    def play_silence(self, val: bool):
        self.config_data["play_silence"] = val
        self.save()

    @property
    def auto_reconnect(self) -> bool:
        return bool(self.config_data.get("auto_reconnect", True))

    @auto_reconnect.setter
    def auto_reconnect(self, val: bool):
        self.config_data["auto_reconnect"] = val
        self.save()

# Instantiate global config
config = BotConfig()
