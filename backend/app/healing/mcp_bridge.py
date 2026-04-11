"""Bridge to Claude Code Agent MCP server for code-level fixes."""

import asyncio
import shlex
import shutil
import subprocess
import time
from collections import deque
from pathlib import Path
from typing import Any

import structlog

from app.core.config import settings
from app.healing.detector import AnomalyEvent

logger = structlog.get_logger("atlas_vox.healing.mcp")

# Default paths — overridden at runtime by engine._load_config_from_db()
DEFAULT_SERVER_PATH = Path("mcp-servers/claude-code-agent/server.py")
DEFAULT_PROJECT_ROOT = Path(".")


class MCPBridge:
    """Communicates with Claude Code Agent MCP server to request code fixes."""

    def __init__(
        self,
        server_path: Path = DEFAULT_SERVER_PATH,
        project_root: Path = DEFAULT_PROJECT_ROOT,
        max_fixes_per_hour: int = 3,
        timeout: int = 300,
    ):
        self.server_path = server_path
        self.project_root = project_root
        self.max_fixes_per_hour = max_fixes_per_hour
        self.timeout = timeout
        self._fix_history: deque[dict[str, Any]] = deque(maxlen=50)
        self._fix_timestamps: deque[float] = deque(maxlen=100)
        self.enabled = True

    def _fixes_this_hour(self) -> int:
        cutoff = time.time() - 3600
        return sum(1 for t in self._fix_timestamps if t > cutoff)

    async def test_connection(self) -> dict[str, Any]:
        """Test MCP bridge connectivity and readiness.

        Checks:
        1. Claude CLI exists in PATH
        2. MCP server script path is valid (if configured)
        3. Project root directory exists
        4. Claude CLI responds to --version

        Returns dict with test results.
        """
        results: dict[str, Any] = {
            "claude_cli_found": False,
            "claude_cli_version": None,
            "server_path_valid": False,
            "server_path": str(self.server_path),
            "project_root_valid": False,
            "project_root": str(self.project_root),
            "enabled": self.enabled,
            "ready": False,
        }

        # Check 1: Claude CLI in PATH
        claude_path = shutil.which("claude")
        results["claude_cli_found"] = claude_path is not None
        if claude_path:
            results["claude_cli_path"] = claude_path

        # Check 2: MCP server path
        results["server_path_valid"] = self.server_path.exists()

        # Check 3: Project root
        results["project_root_valid"] = self.project_root.exists()

        # Check 4: Claude CLI version
        if claude_path:
            try:
                version_result = await asyncio.to_thread(
                    subprocess.run,
                    ["claude", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if version_result.returncode == 0:
                    results["claude_cli_version"] = (
                        version_result.stdout.strip()[:100]
                    )
            except Exception as e:
                results["claude_cli_version"] = f"Error: {e}"

        # Overall readiness: CLI found + project root valid
        results["ready"] = (
            results["claude_cli_found"]
            and results["project_root_valid"]
            and self.enabled
        )

        logger.info("mcp_connection_test", **results)
        return results

    async def request_fix(self, event: AnomalyEvent) -> str:
        """Request a code fix from Claude Code Agent."""
        if not self.enabled:
            return "MCP bridge disabled"

        if not settings.healing_mcp_enabled:
            return "MCP bridge disabled via HEALING_MCP_ENABLED setting"

        if self._fixes_this_hour() >= self.max_fixes_per_hour:
            logger.warning(
                "mcp_rate_limit", fixes_this_hour=self._fixes_this_hour()
            )
            return (
                f"Rate limited: {self._fixes_this_hour()}"
                f"/{self.max_fixes_per_hour} fixes this hour"
            )

        # Build the task prompt from the anomaly event
        task = self._build_task_prompt(event)
        logger.info("mcp_fix_requested", rule=event.rule, task_length=len(task))

        try:
            # Use Claude Code CLI directly since it's more reliable
            # than MCP stdio for one-off tasks
            result = await asyncio.to_thread(
                self._run_claude_code,
                task,
            )
            self._fix_timestamps.append(time.time())
            self._fix_history.append(
                {
                    "timestamp": time.time(),
                    "event_rule": event.rule,
                    "event_title": event.title,
                    "task": task[:200],
                    "result": result[:500],
                    "success": "error" not in result.lower(),
                }
            )
            logger.info(
                "mcp_fix_completed", rule=event.rule, result_length=len(result)
            )
            return result
        except Exception as e:
            logger.error("mcp_fix_error", rule=event.rule, error=str(e))
            return f"MCP fix failed: {e}"

    def _sanitize(self, text: str) -> str:
        """Sanitize user-influenced data for safe inclusion in shell commands."""
        if not text:
            return ""
        # shlex.quote wraps the string in single-quotes, escaping any embedded
        # single-quotes — this is safer than a regex allowlist.
        return shlex.quote(text[:500])

    def _build_task_prompt(self, event: AnomalyEvent) -> str:
        """Build a task prompt for Claude Code from an anomaly event."""
        return f"""Atlas Vox Self-Healing: Investigate and fix the following issue.

ISSUE: {self._sanitize(event.title)}
SEVERITY: {event.severity}
CATEGORY: {event.category}
RULE: {event.rule}
DESCRIPTION: {self._sanitize(event.description)}
VALUE: {event.value} (threshold: {event.threshold})

INSTRUCTIONS:
1. Analyze the root cause in the Atlas Vox codebase at {self.project_root}
2. If a code fix is needed, make the minimal change to resolve the issue
3. Run the relevant tests: cd backend && python -m pytest tests/ --tb=short -q
4. If tests pass, the fix is good. If tests fail, revert your changes.
5. Do NOT make changes to unrelated code
6. Do NOT modify security settings, database schema, or API keys

Report what you found and what you did."""

    def _run_claude_code(self, task: str) -> str:
        """Execute a task via Claude Code CLI."""
        try:
            result = subprocess.run(
                [
                    "claude",
                    "--print",
                    "-p",
                    task,
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(self.project_root),
            )
            output = result.stdout.strip() if result.stdout else ""
            if result.returncode != 0 and result.stderr:
                output += f"\nSTDERR: {result.stderr[:500]}"
            return output or "No output from Claude Code"
        except subprocess.TimeoutExpired:
            return f"Claude Code timed out after {self.timeout}s"
        except FileNotFoundError:
            return "Claude Code CLI not found in PATH"
        except Exception as e:
            return f"Error running Claude Code: {e}"

    async def review_code(self, context: str) -> str:
        """Request a read-only code review (no modifications)."""
        prompt = f"""Review the Atlas Vox codebase for the following issue. \
Do NOT make any changes, only analyze and report.

CONTEXT: {context}

Report:
1. Root cause analysis
2. Affected files
3. Recommended fix (describe, don't implement)"""

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["claude", "--print", "-p", prompt],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.project_root),
            )
            return result.stdout.strip() if result.stdout else "No output"
        except Exception as e:
            return f"Review failed: {e}"

    @property
    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "server_path": str(self.server_path),
            "server_exists": self.server_path.exists(),
            "project_root": str(self.project_root),
            "project_root_exists": self.project_root.exists(),
            "fixes_this_hour": self._fixes_this_hour(),
            "max_fixes_per_hour": self.max_fixes_per_hour,
            "total_fixes": len(self._fix_history),
            "recent_fixes": list(self._fix_history)[-5:],
        }
