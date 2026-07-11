# 🌑 Discord Stay-in-Voice Bot

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![discord.py](https://img.shields.io/badge/discord.py-v2.4+-red.svg)](https://discordpy.readthedocs.io/)

A highly resilient, resource-optimized Discord bot that stays in a voice channel 24/7. It automatically reconnects if kicked, moved, or disconnected due to network issues.

It plays a pre-allocated silent PCM stream to prevent Discord from marking it as idle and disconnecting it. Because it streams silence directly as PCM in pure Python, it **does not require FFmpeg** to be installed on your system!

---

## ✨ Features

- **24/7 Resilience**: Reconnects instantly if kicked or moved, and runs a 15-second background health-check loop to catch edge cases.
- **Resource Optimized**:
  - Streams silence using a single pre-allocated memory chunk, reducing CPU usage to under 0.05%.
  - Supports a resource-saving mode (`!togglesilence`) that stops the audio stream completely in servers where Discord doesn't kick idle bots.
- **FFmpeg-Free**: Generates audio frames directly in code, eliminating the need to install or maintain FFmpeg binaries.
- **Dynamic Config**: Stores voice channel and guild configurations in `data/config.json` automatically, meaning the bot remembers where to stay even after restarts.
- **Structured Logging**: Beautiful colored console logging and persistent log files in `logs/bot.log`.
- **Hot Reloading**: Developers can reload bot features (cogs) on the fly without stopping the bot.

---

## ⚡ Low Resource Mode (Mini PC Optimized)

This bot is specifically tailored to run 24/7 on low-power hardware like a Raspberry Pi, Orange Pi, or mini PC:

- **Idle RAM**: **~60-90 MB** (extremely lightweight).
- **CPU Usage**: **< 0.1%** even when the silent audio stream is active.
- **FFmpeg-Free**: No extra decoder processes spawned, saving memory and CPU cycles.

### Tips for Mini PC Deployment

- **Process Priority**: Run the bot with low priority on Linux to ensure it doesn't impact other services:
  ```bash
  nice -n 19 python main.py
  ```
- **Persistent Sessions**: Use `screen` or `tmux` to keep the bot running after you disconnect from your SSH session:
  ```bash
  tmux new -s discord-bot
  # Run the bot, then press Ctrl+B followed by D to detach
  ```
- **Resource Monitoring**: Track resources in real time using `htop` or the built-in `!status` bot command.

---

## 🛠️ Installation

### 1. Prerequisites

- **Python 3.8+**
- A Discord Bot account (created via the [Discord Developer Portal](https://discord.com/developers/applications)).

> [!IMPORTANT]
> **Required Gateway Intents**: In the Discord Developer Portal, navigate to your application -> **Bot**, and make sure the following toggles are enabled:
> - **Message Content Intent** (Required to process prefix commands)
> - **Voice State Intent** (Required to track and join voice channels)

### 2. Setup & Installation

You can set up and run this bot using **`uv`** (highly recommended for lightning-fast package resolution) or standard **`pip`**.

#### Option A: Using `uv` (Recommended)

1. Initialize a virtual environment and install dependencies:

   ```bash
   uv venv

   # Activate venv (Windows):
   .venv\Scripts\activate
   # Activate venv (Linux/macOS):
   source .venv/bin/activate

   uv pip install -r requirements.txt
   ```

2. Open the `.env` file in the root folder and add your Discord bot token:

   ```env
   DISCORD_TOKEN=your_actual_token_here
   ```

3. Run the bot:

   ```bash
   uv run main.py
   ```

#### Option B: Using standard `pip`

1. Create and activate a virtual environment:

   ```bash
   python -m venv venv

   # Activate venv (Windows):
   venv\Scripts\activate
   # Activate venv (Linux/macOS):
   source venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Open the `.env` file in the root folder and add your Discord bot token:

   ```env
   DISCORD_TOKEN=your_actual_token_here
   ```

4. Run the bot:

   ```bash
   python main.py
   ```

### 3. Production Deployment (Linux Systemd)

To ensure the bot starts automatically after system reboots and stays running in the background, you can set it up as a systemd service:

1. Create a systemd service file:

   ```bash
   sudo nano /etc/systemd/system/stay-voice-bot.service
   ```

2. Paste the following configuration (replace `yourusername` and `/path/to/bot` with your actual Linux user and project directory):

   ```ini
   [Unit]
   Description=Discord Stay Voice Bot
   After=network.target

   [Service]
   Type=simple
   User=yourusername
   WorkingDirectory=/path/to/bot
   ExecStart=/path/to/bot/.venv/bin/python /path/to/bot/main.py
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable stay-voice-bot.service
   sudo systemctl start stay-voice-bot.service
   ```

4. View real-time service logs:

   ```bash
   journalctl -u stay-voice-bot.service -f
   ```

---

## 🎮 Commands

All commands are prefixed with `!` by default.

### Voice Commands

- **`!join` / `!j` `[channel_id/name]`**: Joins a voice channel and locks it for stay-in-voice. Defaults to the channel you are in.
- **`!leave` / `!l` / `!dc`**: Leaves the voice channel and stops the stay-in-voice manager.
- **`!setchannel` / `!sc` `<channel_id/name>`**: Changes the target voice channel.
- **`!togglesilence` / `!ts`**: Toggles the silent audio stream. Disabling silence saves network bandwidth and CPU.

### Admin Commands

- **`!status` / `!stats`**: Displays process metrics (CPU/RAM), latency, connection uptime, target channel, and audio status.
- **`!uptime` / `!up`**: Shows the bot's current online uptime duration.
- **`!reload <cog_name>`**: Hot-reloads a cog (e.g., `voice` or `admin`) without shutting down the bot. (Owner only)
- **`!shutdown`**: Gracefully leaves voice channels and terminates the bot process. (Owner only)

---

## 🛡️ Security & Anti-Abuse

To prevent unauthorized users from hijacking the voice connection or abusing bot resources:

- **Owner-Only Restrictions**: Dangerous administrative commands (`!reload`, `!shutdown`) are hardcoded to check for the Discord Application Owner ID. Only the bot creator can run them.
- **Built-in Rate Limiting**: Commands are protected by a user-based cooldown (1 request per 3–5 seconds depending on the command) to prevent chat spam and API rate limit locks.
- **Guild Lock / Single Server**: The bot is designed to stay in a designated server channel configured by you. It ignores cross-guild messages for voice control.

---

## ⚙️ Configuration File (`data/config.json`)

On the first boot, the bot will auto-generate `data/config.json`. You can modify settings dynamically via bot commands, or edit this file directly:

```json
{
    "prefix": "!",
    "guild_id": 123456789012345678,
    "voice_channel_id": 123456789012345678,
    "play_silence": true,
    "auto_reconnect": true
}
```

---

## 🔍 Troubleshooting

- **Bot connects but immediately disconnects?**
  - Check the bot logs in `logs/bot.log` or your console.
  - Make sure the bot has **Connect** and **Speak** permissions in the voice channel's settings.
  - Make sure the **Voice State Intent** is enabled in the Discord Developer Portal.
- **Failed to install PyNaCl / pip error?**
  - PyNaCl (voice encryption wrapper) requires a compiler on some systems. Under Windows/Linux, running `pip install --upgrade pip` will download pre-built wheels and solve this.

---

## ⚠️ Disclaimer

This bot is intended for educational purposes and personal/private Discord server usage. Please respect Discord's Developer Terms of Service and make sure your server members are comfortable with the bot staying in the voice channel.
