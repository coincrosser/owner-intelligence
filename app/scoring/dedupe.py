from __future__ import annotations

import re


def normalize_name(name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9 ]", " ", name).upper()
    return " ".join(normalized.split())


def dedupe_score(name_a: str, name_b: str) -> float:
    norm_a = normalize_name(name_a)
    norm_b = normalize_name(name_b)
    if norm_a == norm_b:
        return 1.0
    tokens_a = set(norm_a.split())
    tokens_b = set(norm_b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = len(tokens_a & tokens_b) / max(len(tokens_a), len(tokens_b))
    return round(overlap, 2)
