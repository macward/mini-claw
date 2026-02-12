"""MiniClaw entry point."""

import asyncio
import sys

from dotenv import load_dotenv


async def run_cli() -> None:
    """Run the CLI interface."""
    print("MiniClaw CLI - Type 'exit' to quit")
    print("-" * 40)

    while True:
        try:
            user_input = input("\n> ").strip()
            if user_input.lower() in ("exit", "quit", "/exit"):
                print("Goodbye!")
                break
            if not user_input:
                continue

            # TODO: Integrate with AgentLoop
            print(f"[placeholder] Received: {user_input}")

        except KeyboardInterrupt:
            print("\nInterrupted. Goodbye!")
            break
        except EOFError:
            break


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
