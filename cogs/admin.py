import os
import sys
import time
import discord
from discord.ext import commands, tasks
from config import config
from utils.logger import logger

# Import psutil safely for resource utilization stats
try:
    import psutil
except ImportError:
    psutil = None

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
                    name=f"Prefix: {config.prefix}status"
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

    @commands.command(name="uptime", aliases=["up"])
    @commands.cooldown(rate=1, per=3.0, type=commands.BucketType.user)
    async def uptime(self, ctx: commands.Context):
        """Shows the bot's current online uptime."""
        await ctx.send(f"⏱️ **Uptime**: {self.get_uptime_string()}")

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
            await ctx.send(f"✅ Successfully reloaded extension `{cog_name}`.")
        except Exception as e:
            logger.error(f"Failed to reload cog '{cog_name}': {e}", exc_info=True)
            await ctx.send(f"❌ Failed to reload `{cog_name}`:\n```py\n{e}\n```")

    @commands.command(name="shutdown", aliases=["stop"])
    @commands.is_owner()
    async def shutdown(self, ctx: commands.Context):
        """Shuts down the bot and terminates connection cleanly (owner only)."""
        await ctx.send("🌑 Powering down. Leaving voice channels and shutting down...")
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
        await ctx.send("🧹 Attempting to clean up and rotate log files...")
        
        from utils.logger import clear_log_files
        if clear_log_files():
            await ctx.send("✅ Successfully cleared all log files and reinitialized logging.")
        else:
            await ctx.send("❌ Failed to clear log files. Check console or logger for errors.")

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
