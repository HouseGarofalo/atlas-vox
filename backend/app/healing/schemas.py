"""Pydantic schemas for the self-healing API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HealingStatus(BaseModel):
    enabled: bool
    running: bool
    uptime_seconds: float
    incidents_handled: int
    health: dict
    telemetry: dict
    logs: dict


class IncidentResponse(BaseModel):
    id: str
    severity: str
    category: str
    title: str
    description: str | None
    detection_rule: str | None
    action_taken: str | None
    action_detail: str | None
    outcome: str
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentListResponse(BaseModel):
    incidents: list[IncidentResponse]
    count: int
