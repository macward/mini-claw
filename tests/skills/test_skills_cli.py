"""Tests for skills CLI commands."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from miniclaw.skills.cli import (
    cmd_list,
    cmd_enable,
    cmd_disable,
    cmd_info,
    run_skills_cli,
    create_parser,
)
from miniclaw.skills.config import SkillsConfig


def create_skill_dir(base: Path, name: str, description: str, **kwargs) -> Path:
    """Helper to create a skill directory with SKILL.md."""
    skill_dir = base / name
    skill_dir.mkdir(parents=True)

    tags = kwargs.get("tags", [])
    enabled = kwargs.get("enabled", True)
    version = kwargs.get("version", "0.1.0")

    tags_str = ", ".join(tags) if tags else ""
    content = f"""---
name: {name}
description: {description}
version: {version}
tags: [{tags_str}]
enabled: {str(enabled).lower()}
---

Instructions for {name}.
"""
    (skill_dir / "SKILL.md").write_text(content)
    return skill_dir


class TestSkillsListCommand:
    """Tests for 'miniclaw skills list' command."""

    def test_list_shows_skills(self, tmp_path: Path, capsys):
        """List command shows discovered skills."""
        bundled = tmp_path / "bundled"
        bundled.mkdir()
        create_skill_dir(bundled, "summarize", "Summarize documents")
        create_skill_dir(bundled, "explain", "Explain concepts")

        config = SkillsConfig(bundled_dir=bundled, user_dir=None)

        with patch("miniclaw.skills.cli.load_config", return_value=config):
            result = run_skills_cli(["list"])

        assert result == 0
        captured = capsys.readouterr()
        assert "summarize" in captured.out
        assert "explain" in captured.out
        assert "2 skill(s)" in captured.out

    def test_list_excludes_disabled_by_default(self, tmp_path: Path, capsys):
        """List command excludes disabled skills by default."""
        bundled = tmp_path / "bundled"
        bundled.mkdir()
        create_skill_dir(bundled, "enabled_skill", "Enabled")
        create_skill_dir(bundled, "disabled_skill", "Disabled", enabled=False)

        config = SkillsConfig(bundled_dir=bundled, user_dir=None)

        with patch("miniclaw.skills.cli.load_config", return_value=config):
            result = run_skills_cli(["list"])

        assert result == 0
        captured = capsys.readouterr()
        assert "enabled_skill" in captured.out
        assert "disabled_skill" not in captured.out

    def test_list_all_includes_disabled(self, tmp_path: Path, capsys):
        """List --all includes disabled skills."""
        bundled = tmp_path / "bundled"
        bundled.mkdir()
        create_skill_dir(bundled, "enabled_skill", "Enabled")
        create_skill_dir(bundled, "disabled_skill", "Disabled", enabled=False)

        config = SkillsConfig(bundled_dir=bundled, user_dir=None)

        with patch("miniclaw.skills.cli.load_config", return_value=config):
            result = run_skills_cli(["list", "--all"])

        assert result == 0
        captured = capsys.readouterr()
        assert "enabled_skill" in captured.out
        assert "disabled_skill" in captured.out

    def test_list_empty(self, tmp_path: Path, capsys):
        """List command with no skills."""
        config = SkillsConfig(bundled_dir=tmp_path / "empty", user_dir=None)

        with patch("miniclaw.skills.cli.load_config", return_value=config):
            result = run_skills_cli(["list"])

        assert result == 0
        captured = capsys.readouterr()
        assert "No skills found" in captured.out


class TestSkillsEnableCommand:
    """Tests for 'miniclaw skills enable' command."""

    def test_enable_skill(self, tmp_path: Path, capsys):
        """Enable command removes skill from disabled list."""
        bundled = tmp_path / "bundled"
        bundled.mkdir()
        create_skill_dir(bundled, "test_skill", "Test")

        config_path = tmp_path / "config.json"
        config = SkillsConfig(
            bundled_dir=bundled,
            user_dir=None,
            disabled_skills=["test_skill"],
        )

        saved_config = None

        def mock_save(cfg, path=None):
            nonlocal saved_config
            saved_config = cfg

        with (
            patch("miniclaw.skills.cli.load_config", return_value=config),
            patch("miniclaw.skills.cli.save_config", mock_save),
        ):
            result = run_skills_cli(["enable", "test_skill"])

        assert result == 0
        assert "test_skill" not in saved_config.disabled_skills
        captured = capsys.readouterr()
        assert "Enabled skill: test_skill" in captured.out

    def test_enable_already_enabled(self, tmp_path: Path, capsys):
        """Enable command on already enabled skill."""
        bundled = tmp_path / "bundled"
        bundled.mkdir()
        create_skill_dir(bundled, "test_skill", "Test")

        config = SkillsConfig(bundled_dir=bundled, user_dir=None)

        with patch("miniclaw.skills.cli.load_config", return_value=config):
            result = run_skills_cli(["enable", "test_skill"])

        assert result == 0
        captured = capsys.readouterr()
        assert "already enabled" in captured.out

    def test_enable_nonexistent_skill(self, tmp_path: Path, capsys):
        """Enable command on nonexistent skill."""
        config = SkillsConfig(bundled_dir=tmp_path / "empty", user_dir=None)

        with patch("miniclaw.skills.cli.load_config", return_value=config):
            result = run_skills_cli(["enable", "nonexistent"])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_enable_skill_disabled_in_skill_md(self, tmp_path: Path, capsys):
        """Enable command fails for skills disabled in SKILL.md."""
        bundled = tmp_path / "bundled"
        bundled.mkdir()
        create_skill_dir(bundled, "disabled_skill", "Test", enabled=False)

        config = SkillsConfig(bundled_dir=bundled, user_dir=None)

        with patch("miniclaw.skills.cli.load_config", return_value=config):
            result = run_skills_cli(["enable", "disabled_skill"])

        assert result == 1
        captured = capsys.readouterr()
        assert "disabled in its SKILL.md" in captured.out


class TestSkillsDisableCommand:
    """Tests for 'miniclaw skills disable' command."""

    def test_disable_skill(self, tmp_path: Path, capsys):
        """Disable command adds skill to disabled list."""
        bundled = tmp_path / "bundled"
        bundled.mkdir()
        create_skill_dir(bundled, "test_skill", "Test")

        config = SkillsConfig(bundled_dir=bundled, user_dir=None)
        saved_config = None

        def mock_save(cfg, path=None):
            nonlocal saved_config
            saved_config = cfg

        with (
            patch("miniclaw.skills.cli.load_config", return_value=config),
            patch("miniclaw.skills.cli.save_config", mock_save),
        ):
            result = run_skills_cli(["disable", "test_skill"])

        assert result == 0
        assert "test_skill" in saved_config.disabled_skills
        captured = capsys.readouterr()
        assert "Disabled skill: test_skill" in captured.out

    def test_disable_already_disabled(self, tmp_path: Path, capsys):
        """Disable command on already disabled skill."""
        bundled = tmp_path / "bundled"
        bundled.mkdir()
        create_skill_dir(bundled, "test_skill", "Test")

        config = SkillsConfig(
            bundled_dir=bundled,
            user_dir=None,
            disabled_skills=["test_skill"],
        )

        with patch("miniclaw.skills.cli.load_config", return_value=config):
            result = run_skills_cli(["disable", "test_skill"])

        assert result == 0
        captured = capsys.readouterr()
        assert "already disabled" in captured.out

    def test_disable_nonexistent_skill(self, tmp_path: Path, capsys):
        """Disable command on nonexistent skill."""
        config = SkillsConfig(bundled_dir=tmp_path / "empty", user_dir=None)

        with patch("miniclaw.skills.cli.load_config", return_value=config):
            result = run_skills_cli(["disable", "nonexistent"])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.out


class TestSkillsInfoCommand:
    """Tests for 'miniclaw skills info' command."""

    def test_info_shows_details(self, tmp_path: Path, capsys):
        """Info command shows skill details."""
        bundled = tmp_path / "bundled"
        bundled.mkdir()
        create_skill_dir(
            bundled,
            "test_skill",
            "A test skill",
            version="1.0.0",
            tags=["test", "example"],
        )

        config = SkillsConfig(bundled_dir=bundled, user_dir=None)

        with patch("miniclaw.skills.cli.load_config", return_value=config):
            result = run_skills_cli(["info", "test_skill"])

        assert result == 0
        captured = capsys.readouterr()
        assert "test_skill" in captured.out
        assert "A test skill" in captured.out
        assert "1.0.0" in captured.out
        assert "test" in captured.out
        assert "example" in captured.out

    def test_info_nonexistent_skill(self, tmp_path: Path, capsys):
        """Info command on nonexistent skill."""
        config = SkillsConfig(bundled_dir=tmp_path / "empty", user_dir=None)

        with patch("miniclaw.skills.cli.load_config", return_value=config):
            result = run_skills_cli(["info", "nonexistent"])

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.out


class TestSkillsCLIHelp:
    """Tests for CLI help and argument parsing."""

    def test_no_command_shows_help(self, capsys):
        """No command shows help."""
        with patch("miniclaw.skills.cli.load_config"):
            result = run_skills_cli([])

        assert result == 0
        captured = capsys.readouterr()
        assert "Manage MiniClaw skills" in captured.out

    def test_parser_structure(self):
        """Parser has expected subcommands."""
        parser = create_parser()

        # Check subparsers exist
        assert parser._subparsers is not None

        # Parse valid commands without error
        args = parser.parse_args(["list"])
        assert args.command == "list"

        args = parser.parse_args(["enable", "test"])
        assert args.command == "enable"
        assert args.name == "test"

        args = parser.parse_args(["disable", "test"])
        assert args.command == "disable"
        assert args.name == "test"

        args = parser.parse_args(["info", "test"])
        assert args.command == "info"
        assert args.name == "test"
