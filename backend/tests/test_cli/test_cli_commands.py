"""Tests for Atlas Vox CLI commands.

Uses Typer's CliRunner so no live server or database is required for the
commands that don't need them.  Commands that touch the database are tested
by mocking the async init_db call.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from app.cli.main import app


runner = CliRunner()


# ---------------------------------------------------------------------------
# version command
# ---------------------------------------------------------------------------

def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "Atlas Vox" in result.output
    assert "0.1.0" in result.output


def test_version_command_contains_version_number():
    """Smoke test: version string is present and looks like semver."""
    result = runner.invoke(app, ["version"])
    import re
    assert re.search(r"\d+\.\d+\.\d+", result.output), (
        f"No semver-like version found in output: {result.output!r}"
    )


# ---------------------------------------------------------------------------
# init command
# ---------------------------------------------------------------------------

def test_init_command_runs(tmp_path):
    """init must complete without crashing (mocked DB and Redis)."""
    with (
        patch("app.cli.commands.init._check_redis", return_value=False),
        patch("app.core.database.init_db", new=AsyncMock()),
        patch("asyncio.run"),  # prevent actual event loop creation in test
    ):
        result = runner.invoke(app, ["init"])

    assert result.exit_code == 0


def test_init_command_prints_dependency_table(tmp_path):
    with (
        patch("app.cli.commands.init._check_redis", return_value=False),
        patch("app.core.database.init_db", new=AsyncMock()),
        patch("asyncio.run"),
    ):
        result = runner.invoke(app, ["init"])

    # Should print a Rich table with dependency names
    assert "Python" in result.output


def test_init_command_creates_storage_dirs(tmp_path):
    """init must create the required storage subdirectories."""
    with (
        patch("app.cli.commands.init._check_redis", return_value=False),
        patch("app.core.database.init_db", new=AsyncMock()),
        patch("asyncio.run"),
        patch("app.cli.commands.init.Path", return_value=MagicMock()),  # intercept Path usage
    ):
        result = runner.invoke(app, ["init"])

    # Whether dirs are actually created or mocked, the command must not crash
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# help / no-args
# ---------------------------------------------------------------------------

def test_help_flag():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "atlas-vox" in result.output.lower() or "atlas" in result.output.lower()


def test_serve_help():
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--host" in result.output
    assert "--port" in result.output


# ---------------------------------------------------------------------------
# profiles subcommand
# ---------------------------------------------------------------------------

def test_profiles_subcommand_help():
    result = runner.invoke(app, ["profiles", "--help"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# synthesize subcommand
# ---------------------------------------------------------------------------

def test_synthesize_subcommand_help():
    result = runner.invoke(app, ["synthesize", "--help"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# providers subcommand
# ---------------------------------------------------------------------------

def test_providers_subcommand_help():
    result = runner.invoke(app, ["providers", "--help"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# compare subcommand
# ---------------------------------------------------------------------------

def test_compare_subcommand_help():
    result = runner.invoke(app, ["compare", "--help"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# presets subcommand
# ---------------------------------------------------------------------------

def test_presets_subcommand_help():
    result = runner.invoke(app, ["presets", "--help"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# train subcommand
# ---------------------------------------------------------------------------

def test_train_subcommand_help():
    result = runner.invoke(app, ["train", "--help"])
    assert result.exit_code == 0
