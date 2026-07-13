# ADR 0004 — No auto-deploy for code fixes

## Status
Accepted

## Context
The product must handle failures safely.

## Decision
Auto-apply only bounded config/data adjustments.  
Code changes become repair proposals and require human approval before merge/deploy.

## Consequences
Positive:
- prevents unsafe autonomous deploys
- creates an auditable approval trail
- keeps production risk low

Tradeoffs:
- slower code repair loop
- more manual review for code-level issues
