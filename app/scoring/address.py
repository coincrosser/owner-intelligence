from __future__ import annotations

from app.models.schemas import Address


def address_score(address: Address) -> float:
    score = address.confidence
    if address.is_deliverable:
        score += 0.1
    return min(score, 1.0)
