# ADR 0005 — Telegram feedback loop guardrails

## Status
Accepted

## Context
The daily digest ships three Telegram buttons (Good digest / Did not like / Regenerate).
"Did not like" and "Regenerate" both need follow-up questions and must be able to change
future digest behavior. Free text from a Telegram chat is untrusted input; without explicit
bounds this is a route for prompt injection into agent prompts or unbounded config drift.

## Decision
Enforcement lives in `signalos/core/feedback_guardrails.py` (allowed categories, bounds,
per-category deltas, daily cap, unsafe-text patterns) plus `signalos/core/input_safety.py`
(sanitizer) and `signalos/core/preferences.py` (bounded read/write layer). Nothing else in
the feedback loop hardcodes these values.

- **Allowed feedback categories** — exactly the 8 in `FEEDBACK_CATEGORY_LABELS`, selected via
  Telegram inline buttons only. The category is never inferred from free text, so it can never
  be a prompt-injection vector.
- **Allowed preference changes** — `PREFERENCE_BOUNDS` hard-clamps every field
  (`technical_depth`, `summary_length`, `recommendation_strictness`, `source_trust_bias`,
  `category_bias` per-key). `CATEGORY_PREFERENCE_STEP` maps each category to exactly one
  fixed-step delta on exactly one field. `too_repetitive` / `not_enough_new_information` reuse
  the pre-existing bounded `SystemSetting` novelty-threshold tuning instead of the preference
  profile — one governed mechanism, not two.
- **Maximum change magnitude per day** — `MAX_PREFERENCE_EVENTS_PER_DAY` (5) is a *shared*
  budget across all bounded adjustments for a chat (preference fields and novelty-threshold
  tuning). Each event is one small fixed step, so bounding the count also bounds total daily
  magnitude per field.
- **Blocked actions** — `BLOCKED_ACTIONS` lists what feedback handling can never do: modify
  code, auto-deploy, execute shell/system commands, change the DB schema, write an arbitrary
  config key, or apply an unbounded preference change. These are not runtime checks — the code
  simply never implements them. Repair proposals drafted from feedback still go through the
  existing human-approval path (ADR 0004); the feedback loop never auto-applies them.
- **Fallback behavior when feedback is ambiguous or unsafe** — `sanitize_user_text()` rejects
  free text matching `UNSAFE_TEXT_PATTERNS` (prompt-injection phrasing, script/SQL/shell
  fragments) before it reaches storage or a prompt. Unsafe or ambiguous input never changes a
  preference; the bot asks a clarifying question instead and logs a `guardrail_violation`
  `SystemEvent` for evaluation (`signalos/evaluation/feedback_metrics.py::guardrail_violation_rate`).
- **Regenerate-angle text** goes through the same sanitizer, and is injected into the impact-agent
  prompt only inside an explicitly labeled "READER-REQUESTED ANGLE" block. The `product-impact`
  skill is instructed to treat that block as data, never as new instructions.

## Consequences
Positive:
- feedback can only ever nudge a small, enumerated set of numeric fields by small fixed steps
- prompt injection via free text is filtered before it reaches storage or any prompt
- all preference and threshold changes are logged and rate-limited per chat per day
- code and deploys stay untouched by construction, not by convention

Tradeoffs:
- the unsafe-text filter is a cheap heuristic, not a full jailbreak classifier
- a chat that legitimately wants faster adaptation is still capped at the shared daily budget
