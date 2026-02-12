"""Prompt builder for the agent."""

from typing import Any

SYSTEM_PROMPT = """You are MiniClaw, a helpful assistant that can execute commands safely in a sandboxed environment.

You have access to the following tools:
{tools_description}

When you need to use a tool, respond with a tool call. Always explain what you're doing before executing commands.

Important:
- Commands run in an isolated Docker container
- No network access from the container
- Files persist in /workspace during the session
- Be careful with destructive operations

If you cannot complete a task with the available tools, explain why."""


def build_system_prompt(tools_schema: list[dict[str, Any]]) -> str:
    """Build the system prompt with available tools."""
    if not tools_schema:
        tools_desc = "No tools available."
    else:
        tools_desc = "\n".join(
            f"- {t['function']['name']}: {t['function']['description']}"
            for t in tools_schema
        )
    return SYSTEM_PROMPT.format(tools_description=tools_desc)


def format_tool_result(tool_name: str, success: bool, output: str, error: str | None) -> str:
    """Format a tool result for the conversation."""
    if success:
        return f"[{tool_name}] Success:\n{output}"
    else:
        return f"[{tool_name}] Error: {error}"
