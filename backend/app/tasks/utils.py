"""Shared utilities for Celery tasks."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """Run an async coroutine from a sync Celery task context."""
    return asyncio.run(coro)
