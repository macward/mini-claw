"""MiniClaw entry point."""

import asyncio
import sys

from dotenv import find_dotenv, load_dotenv

from .cli import run_cli


def main() -> None:
    """Main entry point."""
    load_dotenv(find_dotenv(usecwd=True))

    if len(sys.argv) > 1 and sys.argv[1] == "bot":
        from .telegram import TelegramBot

        bot = TelegramBot()
        bot.run()
        return

    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
