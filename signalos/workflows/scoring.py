"""Backward-compatible shim — use signalos.source_intelligence.scoring instead."""

from signalos.source_intelligence.scoring import (
    compute_signal_score,
    explain_signal_score,
    recommendation_for_score,
)

__all__ = ["compute_signal_score", "explain_signal_score", "recommendation_for_score"]
