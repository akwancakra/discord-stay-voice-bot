import discord
from discord.ext import commands
from config import config
from utils.logger import logger

class StayVoiceBot(commands.Bot):
    def __init__(self):
        # Configure Discord Intents
        intents = discord.Intents.default()
        intents.voice_states = True
        intents.message_content = True
        
        super().__init__(
            command_prefix=config.prefix,
            intents=intents,
            help_command=commands.DefaultHelpCommand()
        )
        self.first_ready = True

    async def setup_hook(self):
        """Called automatically by discord.py before login to load cogs."""
        extensions = ["cogs.voice", "cogs.admin"]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                logger.info(f"Loaded extension: {ext}")
            except Exception as e:
                logger.critical(f"Failed to load extension {ext}: {e}", exc_info=True)

    async def on_ready(self):
        """Fires when the bot successfully connects to Discord."""
        if self.first_ready:
            logger.info(f"==================================================")
            logger.info(f"🌑 Stay Voice Bot '{self.user}' is online!")
            logger.info(f"Prefix: '{config.prefix}'")
            logger.info(f"Guild ID Config: {config.guild_id}")
            logger.info(f"Channel ID Config: {config.voice_channel_id}")
            logger.info(f"Silence Loop Enabled: {config.play_silence}")
            logger.info(f"==================================================")
            self.first_ready = False
        else:
            logger.info(f"Reconnected to Discord as {self.user}.")

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Gracefully handle and log command execution errors."""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors to avoid log noise
        
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ This command is on cooldown. Please try again in **{error.retry_after:.1f}s**.")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument provided. Please check command usage.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param.name}`.")
        else:
            logger.error(f"Error in command '{ctx.command}': {error}", exc_info=True)
            await ctx.send(f"❌ An error occurred while executing the command.")
