"""MiniClaw entry point."""

import asyncio
import sys

from dotenv import load_dotenv

from .cli import run_cli


def main() -> None:
    """Main entry point."""
    load_dotenv()

    if len(sys.argv) > 1 and sys.argv[1] == "bot":
        # TODO: Start Telegram bot
        print("Telegram bot mode not yet implemented")
        sys.exit(1)

    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
