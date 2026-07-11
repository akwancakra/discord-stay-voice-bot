import asyncio
import discord
from discord.ext import commands, tasks
from config import config
from utils.logger import logger
from utils.audio import SilentAudioSource

class VoiceCog(commands.Cog, name="Voice"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Async lock to prevent concurrent/race condition connection attempts
        self.connection_lock = asyncio.Lock()
        
        # Determine if we should maintain connection based on configuration
        self.should_stay = config.voice_channel_id is not None
        
        # Start the background health check loop
        self.voice_stay_loop.start()

    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        self.voice_stay_loop.cancel()

    async def do_reconnect(self):
        """
        Thread-safe coroutine to connect, move, or restart playback.
        Uses a lock to ensure only one connection state modification runs at a time.
        """
        async with self.connection_lock:
            guild_id = config.guild_id
            channel_id = config.voice_channel_id
            
            if not guild_id or not channel_id:
                return

            guild = self.bot.get_guild(guild_id)
            if not guild:
                logger.warning(f"Guild with ID {guild_id} not found. Ensure the bot is in that guild.")
                return

            channel = guild.get_channel(channel_id)
            if not isinstance(channel, discord.VoiceChannel):
                logger.warning(f"Channel with ID {channel_id} not found or is not a voice channel.")
                return

            # Check bot permissions in target channel
            permissions = channel.permissions_for(guild.me)
            if not permissions.connect or not permissions.speak:
                logger.error(f"Bot lacks 'Connect' or 'Speak' permissions in voice channel '{channel.name}' (Guild: '{guild.name}').")
                return

            vc = guild.voice_client

            try:
                # Case 1: Voice client doesn't exist or is completely disconnected
                if vc is None or not vc.is_connected():
                    logger.info(f"Connecting to voice channel '{channel.name}' (ID: {channel.id}) in guild '{guild.name}'...")
                    if vc is not None:
                        # Clean up previous state safely
                        await vc.disconnect(force=True)
                    await channel.connect(reconnect=True, timeout=20.0)
                    logger.info(f"Connected to '{channel.name}'.")
                
                # Case 2: Voice client is active but in the WRONG channel
                elif vc.channel.id != channel_id:
                    logger.info(f"Bot is in channel '{vc.channel.name}' (ID: {vc.channel.id}), moving to configured channel '{channel.name}' (ID: {channel_id})...")
                    await vc.move_to(channel)
                    logger.info(f"Moved to '{channel.name}'.")
                
                # Update vc reference after connection/movement
                vc = guild.voice_client

                # Manage audio stream based on config
                if vc and vc.is_connected():
                    if config.play_silence:
                        if not vc.is_playing():
                            logger.info(f"Starting silent audio stream in '{channel.name}'.")
                            vc.play(SilentAudioSource())
                    else:
                        if vc.is_playing() and isinstance(vc.source, SilentAudioSource):
                            logger.info("Stopping silent audio stream (silence playback disabled).")
                            vc.stop()

            except discord.Forbidden:
                logger.error(f"Permission denied during voice action in '{channel.name}'.")
            except discord.ClientException as ce:
                logger.warning(f"Discord Client Exception in voice loop: {ce}")
            except Exception as e:
                logger.error(f"Unexpected error during connection lifecycle: {e}", exc_info=True)

    @tasks.loop(seconds=15.0)
    async def voice_stay_loop(self):
        """Periodic connection health check."""
        if self.should_stay:
            await self.do_reconnect()

    @voice_stay_loop.before_loop
    async def before_voice_stay_loop(self):
        """Wait for the bot to be fully ready before starting the loop."""
        await self.bot.wait_until_ready()
        logger.info("Voice connection manager loop has started.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Reactive listener to trigger instant reconnects if kicked or moved."""
        if member.id != self.bot.user.id:
            return

        # Case 1: Bot was disconnected
        if after.channel is None:
            if self.should_stay:
                logger.warning("Bot was disconnected from voice channel! Triggering instant reconnection...")
                self.bot.loop.create_task(self.do_reconnect())
            else:
                logger.info("Bot disconnected from voice channel intentionally.")

        # Case 2: Bot was moved to another channel
        elif before.channel != after.channel:
            if self.should_stay and after.channel.id != config.voice_channel_id:
                logger.warning(f"Bot was moved to channel '{after.channel.name}'. Returning to configured channel...")
                self.bot.loop.create_task(self.do_reconnect())

    # ==================== COMMANDS ====================

    @commands.command(name="join", aliases=["j"])
    @commands.guild_only()
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def join(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        """Joins a voice channel and locks it for stay-in-voice. Defaults to author's current channel."""
        # Find target channel
        if channel is None:
            if ctx.author.voice and ctx.author.voice.channel:
                channel = ctx.author.voice.channel
            else:
                await ctx.send("❌ You must be in a voice channel or specify a channel name/ID (e.g. `!join General`).")
                return

        # Update configurations
        config.guild_id = ctx.guild.id
        config.voice_channel_id = channel.id
        self.should_stay = True

        await ctx.send(f"🔄 Attempting to connect to **{channel.name}** and lock connection...")
        await self.do_reconnect()
        await ctx.send(f"✅ Successfully joined and locked in voice channel: **{channel.name}**.")

    @commands.command(name="leave", aliases=["l", "dc"])
    @commands.guild_only()
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def leave(self, ctx: commands.Context):
        """Gracefully disconnects the bot from the voice channel and stops auto-reconnect."""
        self.should_stay = False
        vc = ctx.guild.voice_client
        
        if vc and vc.is_connected():
            await vc.disconnect()
            await ctx.send("👋 Disconnected and paused the stay-in-voice system.")
        else:
            await ctx.send("ℹ️ The bot is not connected to any voice channel in this server.")

    @commands.command(name="setchannel", aliases=["sc"])
    @commands.guild_only()
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def setchannel(self, ctx: commands.Context, channel: discord.VoiceChannel):
        """Changes the target stay-in-voice channel and updates the configuration."""
        config.guild_id = ctx.guild.id
        config.voice_channel_id = channel.id
        self.should_stay = True
        
        await ctx.send(f"🔄 Updating target channel to **{channel.name}**...")
        await self.do_reconnect()
        await ctx.send(f"✅ Target channel updated to **{channel.name}**.")

    @commands.command(name="togglesilence", aliases=["ts"])
    @commands.cooldown(rate=1, per=5.0, type=commands.BucketType.user)
    async def togglesilence(self, ctx: commands.Context):
        """Toggles the silent audio stream to optimize network/CPU resources."""
        new_state = not config.play_silence
        config.play_silence = new_state
        
        state_str = "ENABLED" if new_state else "DISABLED (Resource-Saving Mode)"
        await ctx.send(f"⚙️ Silent audio stream has been **{state_str}**.")
        
        # Trigger reconnection logic to start/stop the silent player
        if self.should_stay:
            await self.do_reconnect()

async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceCog(bot))
