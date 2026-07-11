import os
import sys
import time
import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
from config import config
from utils.logger import logger

# Import psutil safely for resource utilization stats
try:
    import psutil
except ImportError:
    psutil = None

class HelpView(View):
    def __init__(self):
        super().__init__(timeout=None)  # Permanent buttons

    @discord.ui.button(label="🔊 Voice Commands", style=discord.ButtonStyle.primary, custom_id="help_voice")
    async def voice_button(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="🔊 Voice Commands Help",
            description=(
                f"Commands for managing stay-in-voice functions. All commands require a user to have the configured roles/permissions.\n\n"
                f"• **`st join`** `[channel]` (or **`st j`**): Connects the bot to a channel (defaults to your current voice channel) and locks it.\n"
                f"• **`st leave`** (or **`st l`**, **`st dc`**): Safely disconnects the bot from the voice channel and stops auto-reconnect.\n"
                f"• **`st setchannel`** `<channel>` (or **`st sc`**): Updates the target voice channel to lock onto.\n"
                f"• **`st togglesilence`** (or **`st ts`**): Enables/disables streaming silent audio (disabling saves CPU & upload bandwidth)."
            ),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🛡️ Admin Commands", style=discord.ButtonStyle.secondary, custom_id="help_admin")
    async def admin_button(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="🛡️ Administrative Commands Help",
            description=(
                f"Commands for bot administration and resource metrics. Administrative commands require bot owner privileges.\n\n"
                f"• **`st status`** (or **`st stats`**, **`st info`**): Displays real-time CPU/RAM usage of the bot process, API ping, and voice connection status.\n"
                f"• **`st uptime`** (or **`st up`**): Displays how long the bot has been online.\n"
                f"• **`st clearlogs`** (or **`st cl`**): Safely wipes all log files inside `logs/` directory. (Owner Only)\n"
                f"• **`st reload`** `<cog>`: Hot-reloads a feature cog (e.g. `voice` or `admin`). (Owner Only)\n"
                f"• **`st shutdown`** (or **`st stop`**): Disconnects all channels and stops the bot process. (Owner Only)"
            ),
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="⚡ System Info", style=discord.ButtonStyle.success, custom_id="help_system")
    async def system_button(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="⚡ System Information",
            description=(
                f"Technical details on bot optimizations:\n\n"
                f"• **Auto-Deafen**: Enabled by default to block incoming sound packets, reducing download bandwidth on Mini PCs to exactly 0 KB/s.\n"
                f"• **Zero-Copy Stream**: Silence is pre-allocated in memory, keeping CPU utilization under 0.1% and RAM between 60-90 MB.\n"
                f"• **Log Rotation**: Logs are automatically rotated at 5 MB (max 3 backups) to protect disk storage (20 MB cap)."
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class AdminCog(commands.Cog, name="Admin"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = time.time()
        self.presence_index = 0
        self.presence_rotate_loop.start()

    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        self.presence_rotate_loop.cancel()

    @tasks.loop(seconds=30.0)
    async def presence_rotate_loop(self):
        """Periodically updates the bot's rich presence activity."""
        await self.bot.wait_until_ready()
        
        try:
            activities = []
            
            # 1. Listening to silence
            activities.append(discord.Activity(
                type=discord.ActivityType.listening,
                name="Silence 🤫"
            ))
            
            # 2. Watching uptime
            activities.append(discord.Activity(
                type=discord.ActivityType.watching,
                name=f"Uptime: {self.get_uptime_string()}"
            ))
            
            # 3. Playing/Locked to channel status
            target_guild = self.bot.get_guild(config.guild_id) if config.guild_id else None
            target_channel = target_guild.get_channel(config.voice_channel_id) if target_guild and config.voice_channel_id else None
            
            if target_channel:
                activities.append(discord.Activity(
                    type=discord.ActivityType.playing,
                    name=f"Locked to {target_channel.name}"
                ))
            else:
                activities.append(discord.Activity(
                    type=discord.ActivityType.playing,
                    name=f"Prefix: {config.prefix} help"
                ))

            # Select current presence
            activity = activities[self.presence_index % len(activities)]
            await self.bot.change_presence(activity=activity)
            self.presence_index += 1
            
        except Exception as e:
            logger.error(f"Error in presence rotation loop: {e}")

    def get_uptime_string(self) -> str:
        """Helper to get a human-readable uptime duration string."""
        uptime_seconds = int(time.time() - self.start_time)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        return " ".join(parts)

    # ==================== COMMANDS ====================

    @commands.command(name="help")
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def help(self, ctx: commands.Context):
        """Displays the interactive help menu with buttons."""
        embed = discord.Embed(
            title="🌑 Stay-in-Voice Bot Commands Help",
            description="Select a category below to view detailed commands and instructions.",
            color=discord.Color.dark_gray()
        )
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            
        view = HelpView()
        await ctx.send(embed=embed, view=view)

    @commands.command(name="uptime", aliases=["up"])
    @commands.cooldown(rate=1, per=3.0, type=commands.BucketType.user)
    async def uptime(self, ctx: commands.Context):
        """Shows the bot's current online uptime."""
        embed = discord.Embed(
            description=f"⏱️ **Uptime**: {self.get_uptime_string()}",
            color=discord.Color.dark_gray()
        )
        await ctx.send(embed=embed)

    @commands.command(name="status", aliases=["stats", "info"])
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def status(self, ctx: commands.Context):
        """Displays system resource usage, bot settings, and connection stats."""
        # Guild & Voice Connection Status
        guild_count = len(self.bot.guilds)
        voice_client_count = len(self.bot.voice_clients)
        latency_ms = round(self.bot.latency * 1000, 1)
        
        # Target voice channel details
        target_guild = self.bot.get_guild(config.guild_id) if config.guild_id else None
        target_channel = target_guild.get_channel(config.voice_channel_id) if target_guild and config.voice_channel_id else None
        
        channel_status = "None"
        if target_channel:
            channel_status = f"**{target_channel.name}** (ID: `{target_channel.id}`)"
            
        # Resource utilization
        cpu_usage = "N/A"
        ram_usage = "N/A"
        if psutil:
            try:
                process = psutil.Process(os.getpid())
                cpu_usage = f"{psutil.cpu_percent(interval=None)}%"
                # RSS memory in MB
                ram_mb = process.memory_info().rss / 1024 / 1024
                ram_usage = f"{round(ram_mb, 1)} MB"
            except Exception as e:
                logger.warning(f"Error fetching system resources: {e}")

        # Build Status Embed
        embed = discord.Embed(
            title="🌑 Stay-in-Voice Bot Status",
            color=discord.Color.dark_gray(),
            timestamp=ctx.message.created_at
        )
        
        embed.add_field(name="⏱️ Bot Uptime", value=self.get_uptime_string(), inline=True)
        embed.add_field(name="📶 API Latency", value=f"{latency_ms} ms", inline=True)
        embed.add_field(name="🌍 Servers (Guilds)", value=f"{guild_count}", inline=True)
        
        embed.add_field(name="🔊 Voice Connections", value=f"{voice_client_count} active", inline=True)
        embed.add_field(name="🎯 Locked Channel", value=channel_status, inline=True)
        embed.add_field(name="🔇 Silence Player", value="ENABLED" if config.play_silence else "DISABLED", inline=True)
        
        embed.add_field(name="💻 Process CPU", value=cpu_usage, inline=True)
        embed.add_field(name="🧠 Process RAM", value=ram_usage, inline=True)
        embed.add_field(name="⚙️ Config Prefix", value=f"`{config.prefix}`", inline=True)
        
        embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, cog_name: str):
        """Reloads a specific cog (owner only). Prefix it with 'cogs.' (e.g. cogs.voice)."""
        # Ensure it has the correct prefix
        if not cog_name.startswith("cogs."):
            cog_name = f"cogs.{cog_name}"
            
        try:
            await self.bot.reload_extension(cog_name)
            logger.info(f"Cog '{cog_name}' was reloaded via owner command.")
            embed = discord.Embed(
                description=f"✅ Successfully reloaded extension **`{cog_name}`**.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to reload cog '{cog_name}': {e}", exc_info=True)
            embed = discord.Embed(
                description=f"❌ Failed to reload **`{cog_name}`**:\n```py\n{e}\n```",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

    @commands.command(name="shutdown", aliases=["stop"])
    @commands.is_owner()
    async def shutdown(self, ctx: commands.Context):
        """Shuts down the bot and terminates connection cleanly (owner only)."""
        embed = discord.Embed(
            description="🌑 Powering down. Leaving voice channels and shutting down...",
            color=discord.Color.dark_gray()
        )
        await ctx.send(embed=embed)
        logger.info("Bot shutdown initiated via owner command.")
        
        # Disconnect all voice connections
        for vc in self.bot.voice_clients:
            try:
                await vc.disconnect(force=True)
            except Exception as e:
                logger.error(f"Error disconnecting voice client during shutdown: {e}")
                
        await self.bot.close()
        sys.exit(0)

    @commands.command(name="clearlogs", aliases=["cl"])
    @commands.is_owner()
    async def clearlogs(self, ctx: commands.Context):
        """Clears all system log files in logs/ directory (owner only)."""
        embed = discord.Embed(
            description="🧹 Attempting to clean up and rotate log files...",
            color=discord.Color.blue()
        )
        message = await ctx.send(embed=embed)
        
        from utils.logger import clear_log_files
        if clear_log_files():
            success_embed = discord.Embed(
                description="✅ Successfully cleared all log files and reinitialized logging.",
                color=discord.Color.green()
            )
            await message.edit(embed=success_embed)
        else:
            failed_embed = discord.Embed(
                description="❌ Failed to clear log files. Check console or logger for errors.",
                color=discord.Color.red()
            )
            await message.edit(embed=failed_embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
