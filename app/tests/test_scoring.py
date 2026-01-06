from __future__ import annotations

from datetime import datetime, timedelta

from app.compliance.rules import is_suppressed, should_allow_outreach
from app.models.schemas import Address, IntentLabel
from app.scoring.address import address_score
from app.scoring.dedupe import dedupe_score
from app.scoring.hot_lead import is_hot_lead


def test_dedupe_score_matches():
    assert dedupe_score("Janet Miller", "Janet Miller") == 1.0
    assert dedupe_score("Janet Miller", "Janet A. Miller") >= 0.5


def test_address_score_caps():
    address = Address(
        id="addr-1",
        owner_id="own-1",
        line1="123 Elm",
        city="Canton",
        state="OH",
        postal_code="44702",
        confidence=0.95,
        is_deliverable=True,
    )
    assert address_score(address) == 1.0


def test_suppression_logic():
    suppression = {"own-1": "stop"}
    assert is_suppressed(suppression, "own-1") is True
    assert is_suppressed(suppression, "own-2") is False


def test_frequency_cap():
    attempts = [datetime.utcnow() - timedelta(days=1)]
    assert should_allow_outreach(attempts, max_attempts=2, window_days=7) is True
    attempts.append(datetime.utcnow())
    assert should_allow_outreach(attempts, max_attempts=2, window_days=7) is False


def test_hot_lead_routing():
    assert is_hot_lead(IntentLabel.interested, meaningful_messages=1) is True
    assert is_hot_lead(IntentLabel.curious, meaningful_messages=2) is True
    assert is_hot_lead(IntentLabel.curious, meaningful_messages=1) is False
