import sys
from config import config
from bot import StayVoiceBot
from utils.logger import logger

def main():
    # Verify that the token is set and not a placeholder
    token = config.token
    if not token or token == "YOUR_BOT_TOKEN_HERE" or token.strip() == "":
        logger.critical(
            "\n"
            "==============================================================\n"
            "❌ DISCORD BOT TOKEN IS MISSING OR NOT CONFIGURED!\n"
            "Please open the '.env' file in the root directory and update:\n"
            "DISCORD_TOKEN=your_actual_discord_bot_token_here\n"
            "=============================================================="
        )
        sys.exit(1)

    logger.info("Initializing stay-in-voice bot system...")
    bot = StayVoiceBot()

    try:
        bot.run(token, log_handler=None)  # Use our own custom logging system
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down gracefully...")
    except Exception as e:
        logger.critical(f"An unexpected error occurred during execution: {e}", exc_info=True)
    finally:
        logger.info("Bot execution terminated.")

if __name__ == "__main__":
    main()
