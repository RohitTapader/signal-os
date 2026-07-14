
# Offline Evaluation Plan

## Why offline evaluation is required
The system uses LLMs for:
- novelty detection
- executive intelligence analysis (PM decision synthesis)
- RCA (internal reliability only)
- repair proposals (internal reliability only)

Offline evaluation is needed before rollout to verify quality, trustworthiness, ranking
quality, and cost — but "quality" here means **usefulness to an AI PM's decision-making**,
not summarization quality in the abstract. A fluent, well-cited summary of a paper with no
product/business/strategic angle is not a success case for Signal; it should score low and
carry a low-urgency label (Skim / File Away / Ignore), not get inflated into "Read." Note that
only Read and Skim items are delivered to Telegram — File Away is stored but not sent, and
Ignore is not persisted at all — so a mis-scored item doesn't just rank wrong, it either
reaches the user's feed when it shouldn't, or is silently dropped when it shouldn't be.

## Benchmark datasets
1. Historical golden set of source items
2. Edge-case set of duplicates and updates
3. Adversarial set of malformed or misleading inputs
4. A labeled "PM-relevance" set: items hand-tagged by whether they would plausibly change an
   AI PM's roadmap, vendor choice, pricing model, or competitive read — vs. items that are
   only research-interesting

## Metrics
### Novelty detection
- precision
- recall
- F1
- duplicate suppression rate
- false novelty rate

### Executive intelligence analysis (PM decision synthesis)
- **PM relevance** — does the output actually answer "why does this matter to an AI PM,"
  not just "what happened"
- **actionability** — is `recommended_action` a concrete next step, not generic advice
- **groundedness** — citation accuracy, unsupported claim rate
- **evidence quality** — are supporting_evidence claims traceable to real source text
- **usefulness of the recommendation label** — would a PM reading only the label and one-line
  reason correctly infer how urgently to act, without needing the score breakdown
- **trust / confidence clarity** — do product_impact_confidence / business_impact_confidence /
  strategic_relevance_confidence actually vary independently and track the source content
  (a paper with zero product angle should show near-zero product_impact_confidence, not a
  copy of the other two)
- **roadmap/decision groundedness** — rate of `roadmap_relevance` / `decision_supported`
  being populated for items that don't actually support one (should be near zero; these
  fields must stay empty rather than be manufactured)

### Feedback classification
- accuracy
- confusion matrix
- false repair rate

### Signal scoring and recommendation
- ranking quality against human PM judgment (not just novelty/authority correlation)
- top-3 usefulness: would a PM agree the top 3 items were the ones worth their time today
- **decision impact vs. informational value** — for human review, the key question per item
  is: *would this change a PM's decision, or does it merely inform them?* Items that only
  inform should not outrank items that change a decision, even if the informational item is
  more novel or better-written.
- label distribution sanity — "Read" should be reserved for genuinely top-tier items, not the
  default outcome for every high-novelty item
- **storage/delivery correctness** — Read/Skim items are delivered to Telegram, File Away
  items are stored but not delivered, Ignore items are not persisted; verify no label crosses
  a boundary it shouldn't (e.g. a File Away item accidentally reaching Telegram)

### End-to-end
- digest usefulness (PM-judged, not summarization-judged)
- delivery success
- latency
- cost per digest

## Human review guidance
When reviewing a digest item, the reviewer should ask two questions in order:
1. **Would this change what an AI PM does this week** (roadmap, vendor choice, pricing,
   competitive response)? If yes, the label should be "Read."
2. If it would only inform them (interesting, no decision attached), the label should be
   "Skim" or "File Away" — and `decision_supported` should be empty. A reviewer who finds a
   populated `roadmap_relevance` or `decision_supported` on an item that doesn't actually
   support one should flag it as a groundedness failure, not a stylistic nitpick.

## Launch gates
Do not launch unless:
- novelty precision is high
- groundedness is high, including near-zero manufactured roadmap/decision claims
- signal score ordering reflects genuine PM relevance, verified against the PM-relevance
  labeled set, not just novelty/authority
- recommendation labels are meaningfully differentiated and "Read" isn't the default outcome
- delivery is stable
- repair flow is approval-gated
- cost remains under cap

## Shadow mode
Run the system in shadow mode for 1–2 weeks before exposing users.
