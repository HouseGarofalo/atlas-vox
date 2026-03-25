"""Webhook subscription endpoints — CRUD + test."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DbSession
from app.models.webhook import Webhook
from app.schemas.webhook import (
    WebhookCreate,
    WebhookListResponse,
    WebhookResponse,
    WebhookUpdate,
)
from app.services.webhook_dispatcher import dispatch_event

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

VALID_EVENTS = {"training.completed", "training.failed", "*"}


@router.get("", response_model=WebhookListResponse)
async def list_webhooks(db: DbSession, user: CurrentUser) -> WebhookListResponse:
    """List all webhook subscriptions."""
    result = await db.execute(select(Webhook).order_by(Webhook.created_at.desc()))
    webhooks = result.scalars().all()
    return WebhookListResponse(
        webhooks=[WebhookResponse.model_validate(w) for w in webhooks],
        count=len(webhooks),
    )


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    data: WebhookCreate, db: DbSession, user: CurrentUser
) -> WebhookResponse:
    """Create a webhook subscription."""
    invalid = set(data.events) - VALID_EVENTS
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid events: {', '.join(invalid)}. Valid: {', '.join(sorted(VALID_EVENTS))}",
        )

    webhook = Webhook(
        url=data.url,
        events=",".join(data.events),
        secret=data.secret,
        active=True,
    )
    db.add(webhook)
    await db.flush()
    return WebhookResponse.model_validate(webhook)


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str, data: WebhookUpdate, db: DbSession, user: CurrentUser
) -> WebhookResponse:
    """Update a webhook subscription."""
    result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
    webhook = result.scalar_one_or_none()
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    if data.url is not None:
        webhook.url = data.url
    if data.events is not None:
        webhook.events = ",".join(data.events)
    if data.secret is not None:
        webhook.secret = data.secret
    if data.active is not None:
        webhook.active = data.active
    await db.flush()
    return WebhookResponse.model_validate(webhook)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str, db: DbSession, user: CurrentUser
) -> None:
    """Delete a webhook subscription."""
    result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
    webhook = result.scalar_one_or_none()
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    await db.delete(webhook)


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str, db: DbSession, user: CurrentUser
) -> dict:
    """Send a test payload to a webhook."""
    result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
    webhook = result.scalar_one_or_none()
    if webhook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    deliveries = await dispatch_event(db, "test", {"message": "Test webhook from Atlas Vox"})
    return {"deliveries": deliveries}
