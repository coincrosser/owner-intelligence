from __future__ import annotations

from dataclasses import dataclass

from app.models.schemas import IntentLabel


@dataclass
class SchedulingLink:
    url: str


class IntentClassifier:
    def classify(self, message: str) -> IntentLabel:
        normalized = message.lower()
        if "stop" in normalized or "unsubscribe" in normalized:
            return IntentLabel.stop
        if "not now" in normalized or "later" in normalized:
            return IntentLabel.not_now
        if "never" in normalized or "do not contact" in normalized:
            return IntentLabel.never
        if "interested" in normalized or "yes" in normalized or "call me" in normalized:
            return IntentLabel.interested
        return IntentLabel.curious


class ResponseGenerator:
    def __init__(self, scheduling_link: SchedulingLink) -> None:
        self.scheduling_link = scheduling_link

    def draft(self, intent: IntentLabel) -> str:
        if intent in {IntentLabel.stop, IntentLabel.never}:
            return "Understood. We will not contact you again."
        if intent == IntentLabel.not_now:
            return (
                "Thanks for letting us know. If timing changes, we can schedule here: "
                f"{self.scheduling_link.url}"
            )
        if intent == IntentLabel.interested:
            return (
                "Great! I can set up a quick call to discuss. "
                f"Pick a time here: {self.scheduling_link.url}"
            )
        return (
            "Happy to answer questions and set up a call if helpful. "
            f"Schedule anytime: {self.scheduling_link.url}"
        )
