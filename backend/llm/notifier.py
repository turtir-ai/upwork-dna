"""
HOT Jobs Notifier – Sends alerts when high-priority jobs are detected.

Supports:
- Console logging (always on)
- Webhook (Discord/Telegram/Slack) via configurable URL
- In-memory notification queue for dashboard polling
"""
from __future__ import annotations

import json
import logging
import os
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger("upwork-dna.llm.notifier")

# Max notifications to keep in memory for dashboard polling
MAX_NOTIFICATION_QUEUE = 100

# Webhook URL from environment
WEBHOOK_URL = os.getenv("UPWORK_DNA_WEBHOOK_URL", "")
WEBHOOK_ENABLED = bool(WEBHOOK_URL)


@dataclass
class Notification:
    """A single notification about a job opportunity."""
    job_key: str
    title: str
    priority: str  # HOT | WARM
    composite_score: float
    summary: str
    reason: str
    timestamp: str = ""
    sent_webhook: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class HotJobsNotifier:
    """
    Manages notifications for high-priority job opportunities.

    Usage:
        notifier = HotJobsNotifier()
        await notifier.notify_hot_job(decision)
        recent = notifier.get_recent()
    """

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or WEBHOOK_URL
        self._queue: deque[Notification] = deque(maxlen=MAX_NOTIFICATION_QUEUE)

    async def notify_hot_job(
        self,
        job_key: str,
        title: str,
        priority: str,
        composite_score: float,
        summary: str,
        reason: str,
    ) -> Notification:
        """Send a notification for a HOT/WARM job."""
        notification = Notification(
            job_key=job_key,
            title=title,
            priority=priority,
            composite_score=composite_score,
            summary=summary,
            reason=reason,
            timestamp=datetime.utcnow().isoformat(),
        )

        # Always add to in-memory queue
        self._queue.appendleft(notification)

        # Console log
        emoji = "🔥" if priority == "HOT" else "☀️"
        logger.info(
            f"{emoji} {priority} JOB: {title} | Score: {composite_score:.0%} | {reason}"
        )

        # Webhook if configured
        if self.webhook_url:
            try:
                await self._send_webhook(notification)
                notification.sent_webhook = True
            except Exception as e:
                logger.warning(f"Webhook failed: {e}")

        return notification

    async def notify_batch(self, decisions: list[dict]):
        """Notify for all HOT and WARM jobs in a decision batch."""
        for d in decisions:
            if d.get("priority_label") in ("HOT", "WARM"):
                analysis = d.get("analysis", {})
                await self.notify_hot_job(
                    job_key=d.get("job_key", ""),
                    title=d.get("title", ""),
                    priority=d.get("priority_label", "WARM"),
                    composite_score=d.get("composite_score", 0),
                    summary=analysis.get("summary_1line", ""),
                    reason=d.get("reason", ""),
                )

    def get_recent(self, limit: int = 20) -> list[dict]:
        """Get recent notifications for dashboard polling."""
        return [n.to_dict() for n in list(self._queue)[:limit]]

    def clear(self):
        """Clear notification queue."""
        self._queue.clear()

    async def _send_webhook(self, notification: Notification):
        """Send notification to configured webhook URL."""
        emoji = "🔥" if notification.priority == "HOT" else "☀️"

        # Try to detect webhook type from URL
        if "discord" in self.webhook_url:
            payload = self._format_discord(notification, emoji)
        elif "telegram" in self.webhook_url:
            payload = self._format_telegram(notification, emoji)
        else:
            # Generic webhook (Slack-compatible)
            payload = self._format_generic(notification, emoji)

        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(self.webhook_url, json=payload)
            r.raise_for_status()
            logger.info(f"Webhook sent for: {notification.job_key}")

    @staticmethod
    def _format_discord(n: Notification, emoji: str) -> dict:
        return {
            "content": None,
            "embeds": [{
                "title": f"{emoji} {n.priority} Job Alert",
                "description": n.title,
                "color": 0xFF4500 if n.priority == "HOT" else 0xFFA500,
                "fields": [
                    {"name": "Score", "value": f"{n.composite_score:.0%}", "inline": True},
                    {"name": "Summary", "value": n.summary[:200], "inline": False},
                    {"name": "Reason", "value": n.reason[:200], "inline": False},
                ],
                "footer": {"text": f"Job: {n.job_key}"},
                "timestamp": n.timestamp,
            }],
        }

    @staticmethod
    def _format_telegram(n: Notification, emoji: str) -> dict:
        text = (
            f"{emoji} *{n.priority} Job Alert*\n\n"
            f"*{n.title}*\n"
            f"Score: {n.composite_score:.0%}\n"
            f"Summary: {n.summary[:200]}\n"
            f"Reason: {n.reason[:200]}\n"
            f"Key: `{n.job_key}`"
        )
        return {"text": text, "parse_mode": "Markdown"}

    @staticmethod
    def _format_generic(n: Notification, emoji: str) -> dict:
        return {
            "text": f"{emoji} {n.priority}: {n.title} ({n.composite_score:.0%}) — {n.reason[:200]}",
            "blocks": [{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{emoji} *{n.priority} Job Alert*\n"
                        f"*{n.title}*\n"
                        f"Score: {n.composite_score:.0%} | {n.summary[:200]}"
                    ),
                },
            }],
        }


# Singleton instance
_notifier: Optional[HotJobsNotifier] = None


def get_notifier() -> HotJobsNotifier:
    global _notifier
    if _notifier is None:
        _notifier = HotJobsNotifier()
    return _notifier
