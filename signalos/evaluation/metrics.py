from __future__ import annotations

def groundedness_score(has_citation: bool, unsupported_claims: int, total_claims: int) -> float:
    if total_claims == 0:
        return 0.0
    return max(0.0, min(1.0, (1 if has_citation else 0) * (1 - unsupported_claims / total_claims)))

def digest_quality_score(novelty_precision: float, groundedness: float, delivery_success: float) -> float:
    return round((0.4 * novelty_precision) + (0.4 * groundedness) + (0.2 * delivery_success), 4)
