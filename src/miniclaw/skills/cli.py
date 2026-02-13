"""CLI commands for skill management.

Provides subcommands for listing, enabling, and disabling skills.
"""

import argparse
import sys

from .config import load_config, save_config
from .manager import SkillManager


def _get_manager() -> SkillManager:
    """Create a SkillManager with config loaded from disk."""
    config = load_config()
    manager = SkillManager(config)
    manager.discover()
    return manager


def _format_source(source: str) -> str:
    """Format source for display with color hints."""
    colors = {
        "bundled": "\033[34m",  # blue
        "user": "\033[32m",     # green
        "workspace": "\033[35m",  # magenta
    }
    reset = "\033[0m"
    color = colors.get(source.lower(), "")
    return f"{color}{source}{reset}"


def _format_status(enabled: bool, config_disabled: bool) -> str:
    """Format enabled status for display."""
    if not enabled:
        return "\033[31mdisabled (in SKILL.md)\033[0m"
    if config_disabled:
        return "\033[33mdisabled (in config)\033[0m"
    return "\033[32menabled\033[0m"


def cmd_list(args: argparse.Namespace) -> int:
    """List all available skills."""
    manager = _get_manager()
    skills = manager.list_skills(include_disabled=args.all)

    if not skills:
        print("No skills found.")
        return 0

    # Header
    print(f"\n{'Name':<20} {'Source':<12} {'Status':<28} Description")
    print("-" * 80)

    for meta in sorted(skills, key=lambda s: s.name):
        config_disabled = meta.name in manager.config.disabled_skills
        status = _format_status(meta.enabled, config_disabled)
        source = _format_source(meta.source.value)

        # Truncate long descriptions
        desc = meta.description
        if len(desc) > 35:
            desc = desc[:32] + "..."

        print(f"{meta.name:<20} {source:<21} {status:<37} {desc}")

    print(f"\nTotal: {len(skills)} skill(s)")
    return 0


def cmd_enable(args: argparse.Namespace) -> int:
    """Enable a disabled skill."""
    config = load_config()
    manager = SkillManager(config)
    manager.discover()

    skill = manager.get(args.name)
    if skill is None:
        print(f"Error: Skill '{args.name}' not found.")
        return 1

    if not skill.enabled:
        print(f"Error: Skill '{args.name}' is disabled in its SKILL.md (enabled: false).")
        print("Edit the SKILL.md to enable it.")
        return 1

    if args.name not in config.disabled_skills:
        print(f"Skill '{args.name}' is already enabled.")
        return 0

    config.disabled_skills.remove(args.name)
    save_config(config)
    print(f"Enabled skill: {args.name}")
    return 0


def cmd_disable(args: argparse.Namespace) -> int:
    """Disable a skill."""
    config = load_config()
    manager = SkillManager(config)
    manager.discover()

    skill = manager.get(args.name)
    if skill is None:
        print(f"Error: Skill '{args.name}' not found.")
        return 1

    if args.name in config.disabled_skills:
        print(f"Skill '{args.name}' is already disabled.")
        return 0

    config.disabled_skills.append(args.name)
    save_config(config)
    print(f"Disabled skill: {args.name}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Show detailed info about a skill."""
    manager = _get_manager()

    skill = manager.get(args.name)
    if skill is None:
        print(f"Error: Skill '{args.name}' not found.")
        return 1

    meta = skill.metadata
    config_disabled = meta.name in manager.config.disabled_skills

    print(f"\nSkill: {meta.name}")
    print("-" * 40)
    print(f"Description: {meta.description}")
    print(f"Version: {meta.version}")
    print(f"Source: {_format_source(meta.source.value)}")
    print(f"Status: {_format_status(meta.enabled, config_disabled)}")

    if meta.tags:
        print(f"Tags: {', '.join(meta.tags)}")

    if meta.tools_required:
        print(f"Required tools: {', '.join(meta.tools_required)}")

    if meta.path:
        print(f"Path: {meta.path}")

    mtime = manager.get_skill_mtime(meta.name)
    if mtime:
        from datetime import datetime
        dt = datetime.fromtimestamp(mtime)
        print(f"Last modified: {dt.strftime('%Y-%m-%d %H:%M:%S')}")

    return 0


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for skills CLI."""
    parser = argparse.ArgumentParser(
        prog="miniclaw skills",
        description="Manage MiniClaw skills",
    )

    subparsers = parser.add_subparsers(dest="command", help="Sub-command help")

    # list command
    list_parser = subparsers.add_parser("list", help="List available skills")
    list_parser.add_argument(
        "-a", "--all",
        action="store_true",
        help="Include disabled skills",
    )

    # enable command
    enable_parser = subparsers.add_parser("enable", help="Enable a skill")
    enable_parser.add_argument("name", help="Name of the skill to enable")

    # disable command
    disable_parser = subparsers.add_parser("disable", help="Disable a skill")
    disable_parser.add_argument("name", help="Name of the skill to disable")

    # info command
    info_parser = subparsers.add_parser("info", help="Show detailed skill info")
    info_parser.add_argument("name", help="Name of the skill")

    return parser


def run_skills_cli(argv: list[str] | None = None) -> int:
    """Run the skills CLI with given arguments.

    Args:
        argv: Command-line arguments. Uses sys.argv[1:] if None.

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "list": cmd_list,
        "enable": cmd_enable,
        "disable": cmd_disable,
        "info": cmd_info,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(run_skills_cli())
