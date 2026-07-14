# ADR 0006 — Signal is PM decision support, not a research/news digest

## Status
Accepted

## Context
Early iterations of the executive-intelligence output read like a well-written research
summary: a headline, a summary, some bullets, and a numeric "Signal Score" that meant nothing
to a reader without the underlying weighting formula. Every item also carried a
`roadmap_relevance` line regardless of whether the source actually supported one, because the
skill was instructed to always fill it in — which produced generic, stretched "roadmap"
language on items that were simply research-interesting with no real product angle. The
recommendation label set (Read Now / Read This Week / Skim / Ignore) was also a plain
urgency scale, not tied to whether a real PM decision was actually at stake.

## Decision
Reframe Signal explicitly as a decision-support system for AI Product Managers, not a news
summarizer or research digest, and change the product surface to match:

- Every item must answer, in order: **what changed → why it matters to an AI PM → who should
  care → what decision it informs → how confident and well-evidenced is this.** These are now
  distinct schema fields (`roadmap_relevance`, `business_metric_impact`, `who_should_care`,
  `decision_supported`) rather than folded into prose.
- `roadmap_relevance`, `business_metric_impact`, `who_should_care`, and `decision_supported`
  are all genuinely optional — the skill is instructed to leave them empty when the source
  doesn't support one, rather than manufacture a plausible-sounding answer. An item that is
  only research-interesting should read as low-priority, not be dressed up as roadmap-relevant.
- The recommendation label set is now grounded PM action language: **Read, Skim, File Away,
  Ignore** — replacing the old urgency-only scale. `decision_supported` sharpens the *reason*
  text within the top band (why it's "Read") without changing the label itself — the label
  set is deliberately small so the storage/delivery rule below stays simple to reason about.
- The numeric signal-score breakdown is no longer shown to the reader as the primary framing;
  the label plus a one-line plain-English reason (`should_you_read.reason`) is the entire
  reader-facing signal, per the existing scoring-transparency requirement, but the label
  itself must be self-explanatory.
- Ranking now reflects seven explicit, PM-relevant factors — novelty, product impact,
  business impact, strategic relevance, source authority, trend momentum (cross-source
  corroboration), and evidence strength — rather than one blended "impact" number, so an
  item's PM-relevance can be reasoned about component by component.
- RCA and repair proposals remain internal reliability tooling only (ADR 0004); this ADR does
  not change that, but explicitly rules out ever marketing them as a customer-facing feature.
- **Storage and delivery are filtered by label, not just ranking.** Only Read and Skim items
  are ever pushed to Telegram (`signalos/workflows/pipeline.py::TELEGRAM_SHOWN_RECOMMENDATIONS`).
  File Away items are still persisted (impact_json stored, reachable via the dashboard/API) so
  they exist as an archive, but never reach the user's feed. Ignore items are not persisted at
  all — the underlying `ContentItem` row from ingestion still exists (required for novelty
  dedup against future days), but no impact analysis is stored or shown for it. This keeps the
  daily Telegram feed to only what's actually worth a PM's attention, while the backend still
  retains a broader record for reference and future evaluation.

## Consequences
Positive:
- the product reads as "what should I do about this" rather than "here's what happened"
- manufactured roadmap/decision claims become a measurable groundedness failure instead of
  invisible stylistic noise (see docs/EVALUATION.md)
- ranking is explainable component-by-component instead of one opaque "impact" number
- the label set is small and unambiguous — every item is exactly one of Read / Skim / File
  Away / Ignore, and each maps to one storage/delivery outcome
- the Telegram feed only ever contains Read/Skim items, so a noisy day doesn't degrade daily
  reading — it just means fewer messages, not lower-quality ones

Tradeoffs:
- most items will legitimately have empty `roadmap_relevance` / `decision_supported` — this is
  intentional (see EVALUATION.md), not a regression, but it means fewer fields render per
  message than before
- the skill prompt is longer and more constrained, which costs a small amount of extra output
  discipline from the model (mitigated by explicit few-field examples in the skill file)
- on a day where the top-ranked candidates (selected before scoring, by authority/preference
  bias) all land below Skim, the Telegram feed can go out with zero items even though lower-
  ranked candidates further down the list were never analyzed — the pipeline does not currently
  backfill additional candidates when top picks get filtered out post-scoring
