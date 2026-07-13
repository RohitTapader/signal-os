
# Offline Evaluation Plan

## Why offline evaluation is required
The system uses LLMs for:
- novelty detection
- executive intelligence analysis
- RCA
- repair proposals

Offline evaluation is needed before rollout to verify quality, trustworthiness, ranking quality, and cost.

## Benchmark datasets
1. Historical golden set of source items
2. Edge-case set of duplicates and updates
3. Adversarial set of malformed or misleading inputs

## Metrics
### Novelty detection
- precision
- recall
- F1
- duplicate suppression rate
- false novelty rate

### Executive intelligence analysis
- groundedness
- citation accuracy
- unsupported claim rate
- usefulness
- actionability
- recommendation accuracy (Read Now / Read This Week / Skim / Ignore)

### Feedback classification
- accuracy
- confusion matrix
- false repair rate

### Signal scoring
- ranking quality against human judgment
- top-3 usefulness
- correlation with source authority / novelty / impact labels

### End-to-end
- digest usefulness
- delivery success
- latency
- cost per digest

## Launch gates
Do not launch unless:
- novelty precision is high
- groundedness is high
- signal score ordering is sensible
- delivery is stable
- repair flow is approval-gated
- cost remains under cap

## Shadow mode
Run the system in shadow mode for 1–2 weeks before exposing users.
