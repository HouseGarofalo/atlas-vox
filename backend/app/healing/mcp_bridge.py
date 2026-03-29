"""Bridge to Claude Code Agent MCP server for code-level fixes."""

import asyncio
import subprocess
import time
from collections import deque
from pathlib import Path
from typing import Any

import structlog

from app.healing.detector import AnomalyEvent

logger = structlog.get_logger("atlas_vox.healing.mcp")

# Path to the Claude Code Agent MCP server
MCP_SERVER_PATH = Path(
    "E:/Repos/HouseGarofalo/claude-tools/mcp-servers/claude-code-agent/server.py"
)
PROJECT_ROOT = Path("E:/Repos/HouseGarofalo/atlas-vox")


class MCPBridge:
    """Communicates with Claude Code Agent MCP server to request code fixes."""

    def __init__(
        self,
        server_path: Path = MCP_SERVER_PATH,
        project_root: Path = PROJECT_ROOT,
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

    async def request_fix(self, event: AnomalyEvent) -> str:
        """Request a code fix from Claude Code Agent."""
        if not self.enabled:
            return "MCP bridge disabled"

        if self._fixes_this_hour() >= self.max_fixes_per_hour:
            logger.warning(
                "mcp_rate_limit", fixes_this_hour=self._fixes_this_hour()
            )
            return (
                f"Rate limited: {self._fixes_this_hour()}"
                f"/{self.max_fixes_per_hour} fixes this hour"
            )

        if not self.server_path.exists():
            logger.error("mcp_server_not_found", path=str(self.server_path))
            return f"MCP server not found at {self.server_path}"

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
        """Remove shell metacharacters and limit length."""
        if not text:
            return ""
        # Remove potential command injection characters
        sanitized = text.replace("`", "").replace("$", "").replace("$(", "").replace(";", "")
        return sanitized[:500]

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
            "fixes_this_hour": self._fixes_this_hour(),
            "max_fixes_per_hour": self.max_fixes_per_hour,
            "total_fixes": len(self._fix_history),
            "recent_fixes": list(self._fix_history)[-5:],
        }
