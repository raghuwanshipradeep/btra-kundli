# Cost Optimization — A/B Results

## Lever 1: Haiku 4.5 for translation

Routed Hindi translation calls from Sonnet 4 ($3/$15 per MTok) to Haiku 4.5 ($1/$5 per MTok) — 67% cost reduction on translation.

Kill-switch: `USE_HAIKU_FOR_TRANSLATION=false` in `.env` reverts to Sonnet without code change.

**Status:** SHIP — pending A/B comparison on live Hindi PDFs. Compare ascendant, nakshatra, and house report sections for fluency and term accuracy.

| Section | Sonnet output | Haiku output | Verdict |
|---|---|---|---|
| Ascendant report | _pending_ | _pending_ | _pending_ |
| Nakshatra report | _pending_ | _pending_ | _pending_ |
| House 1 report | _pending_ | _pending_ | _pending_ |

## Lever 5a: Remedy batch cohesion

- Per-item word count target: 120-180 → 90-120
- Per-item tokens (hi): 1100 → 500, (en): 700 → 350
- Cohesion clause added: yes (remedies cross-reference each other as unified plan)
- Cache version: v2 (forces regeneration of remedy narratives)

**Status:** SHIP — pending verification on live Kundli. Check remedy sections for cross-referencing and no truncation.
