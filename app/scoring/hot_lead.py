from __future__ import annotations

from app.models.schemas import IntentLabel


def is_hot_lead(intent: IntentLabel, meaningful_messages: int) -> bool:
    return intent == IntentLabel.interested or meaningful_messages >= 2
