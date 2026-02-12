"""CLI interface for MiniClaw."""

import asyncio
import os
import uuid

from .agent import AgentConfig, AgentLoop, StopReason
from .logging import configure_logger, get_logger
from .tools import ToolRegistry


BANNER = """
╔══════════════════════════════════════════╗
║           🦀 MiniClaw v0.1.0             ║
║    Educational Sandbox Assistant         ║
╚══════════════════════════════════════════╝

Commands:
  /exit, /quit  - Exit the CLI
  /reset        - Reset session (new chat_id)
  /help         - Show this help

Type your message and press Enter.
"""


class CLI:
    """Interactive command-line interface for MiniClaw."""

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        config: AgentConfig | None = None,
    ) -> None:
        self.registry = registry or ToolRegistry()
        self.config = config or AgentConfig()
        self.chat_id = self._new_chat_id()
        self.agent: AgentLoop | None = None
        self.logger = get_logger()

    def _new_chat_id(self) -> str:
        """Generate a new chat ID."""
        return f"cli-{uuid.uuid4().hex[:8]}"

    def _init_agent(self) -> None:
        """Initialize or reinitialize the agent."""
        self.agent = AgentLoop(self.registry, self.config)
        self.logger.set_chat_id(self.chat_id)
        self.logger.log("session_start", chat_id=self.chat_id)

    def _reset(self) -> None:
        """Reset the session."""
        old_chat_id = self.chat_id
        self.chat_id = self._new_chat_id()
        self._init_agent()
        self.logger.log("session_reset", old_chat_id=old_chat_id, chat_id=self.chat_id)
        print(f"\n✓ Session reset. New chat_id: {self.chat_id}")

    def _format_response(self, response: str, stop_reason: StopReason, turns: int) -> str:
        """Format the agent's response for display."""
        output = ["\n" + "─" * 40]
        output.append(response)
        output.append("─" * 40)

        if stop_reason != StopReason.COMPLETE:
            output.append(f"⚠ Stopped: {stop_reason.value} (turns: {turns})")

        return "\n".join(output)

    async def _process_message(self, message: str) -> None:
        """Process a user message through the agent."""
        if self.agent is None:
            self._init_agent()

        assert self.agent is not None

        try:
            result = await self.agent.run(message, chat_id=self.chat_id)

            print(self._format_response(result.response, result.stop_reason, result.turns))

            self.logger.log_agent_stop(
                result.stop_reason.value,
                chat_id=self.chat_id,
                turns=result.turns,
            )

        except Exception as e:
            error_msg = f"Error: {e}"
            print(f"\n❌ {error_msg}")
            self.logger.log("error", chat_id=self.chat_id, error=str(e))

    def _handle_command(self, command: str) -> bool:
        """Handle a special command. Returns True if should continue, False to exit."""
        cmd = command.lower().strip()

        if cmd in ("/exit", "/quit", "exit", "quit"):
            print("\n👋 Goodbye!")
            self.logger.log("session_end", chat_id=self.chat_id)
            return False

        if cmd == "/reset":
            self._reset()
            return True

        if cmd == "/help":
            print(BANNER)
            return True

        return True  # Unknown command, continue

    async def run(self) -> None:
        """Run the interactive CLI."""
        print(BANNER)
        print(f"Session: {self.chat_id}\n")

        self._init_agent()

        while True:
            try:
                user_input = input("you> ").strip()

                if not user_input:
                    continue

                # Handle special commands
                if user_input.startswith("/") or user_input.lower() in ("exit", "quit"):
                    if not self._handle_command(user_input):
                        break
                    continue

                # Process through agent
                await self._process_message(user_input)

            except KeyboardInterrupt:
                print("\n\n⚡ Interrupted")
                try:
                    confirm = input("Exit? (y/n): ").strip().lower()
                    if confirm in ("y", "yes"):
                        print("👋 Goodbye!")
                        self.logger.log("session_interrupt", chat_id=self.chat_id)
                        break
                except (KeyboardInterrupt, EOFError):
                    print("\n👋 Goodbye!")
                    break

            except EOFError:
                print("\n👋 Goodbye!")
                break


async def run_cli() -> None:
    """Run the CLI with default configuration."""
    # Configure logging
    configure_logger()

    # Check for API key
    if not os.getenv("GROQ_API_KEY"):
        print("❌ Error: GROQ_API_KEY environment variable not set")
        print("Please set it in your .env file or environment")
        return

    cli = CLI()
    await cli.run()
