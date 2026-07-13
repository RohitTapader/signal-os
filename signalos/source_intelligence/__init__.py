"""Source Intelligence — first-class capability for trusted AI PM signal ingestion.

Interview framing (4 layers):
1. source_intelligence — what sources to trust, how to score & cluster signals
2. ingestion            — adapters that fetch from RSS, GitHub, arXiv
3. agents               — LLM skills (novelty, impact, feedback)
4. workflows            — daily pipeline, delivery (Telegram, API)
"""

from signalos.source_intelligence.briefing import build_intelligence_briefing
from signalos.source_intelligence.registry import SourceRegistry, get_registry
from signalos.source_intelligence.scoring import compute_signal_score, explain_signal_score

__all__ = [
    "SourceRegistry",
    "build_intelligence_briefing",
    "compute_signal_score",
    "explain_signal_score",
    "get_registry",
]
