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

## Lever: Haiku 4.5 for planets + numerology narratives

Routed the two most formulaic narrative batches from Sonnet 4 to Haiku 4.5 — `planets`
(placement descriptions, the single biggest batch) and `numerology` (near-deterministic
from birth number). All other batches (`md_journey`, `thematic`, `yoga`, `remedy`, `misc`)
stay on Sonnet.

Kill-switch: `USE_HAIKU_FOR_SIMPLE_NARRATIVES=false` in `.env` reverts ALL narratives to
Sonnet without a code change (`config.use_haiku_for_simple_narratives`, default `True`).

**Implementation (shipped in code):**
- `config.py` — `use_haiku_for_simple_narratives: bool = True` kill-switch.
- `narrative_engine.py` — `SIMPLE_NARRATIVE_MODEL = "claude-haiku-4-5-20251001"`; `_batch_narrate`
  gained a `model` param (defaults to `NARRATIVE_MODEL`); the API call and cost log now use
  `active_model`; dispatch routes only `planets` + `numerology` to `simple_model`.
- Cached `section_type` strings: `planet_placement` (planets), `numerology_personality` (numerology).

**Projected cost (per Hindi Kundli, from prod cost log):**

| Batch | Sonnet | Haiku | Saving |
|---|---|---|---|
| planets | $0.079 | ~$0.026 | $0.053 |
| numerology | $0.027 | ~$0.009 | $0.018 |
| **Total** | | | **~$0.07/Kundli** |

**A/B quality (completed 2026-06-10):** ran `generate_narratives()` on demo data (lang=hi)
twice — `use_haiku_for_simple_narratives=false` (Sonnet baseline) vs `true` (Haiku) — with
isolated caches, comparing all 12 planet + 4 numerology sections.

Measured cost on the test chart (full Hindi Kundli): **$0.3948 → $0.2966 (−$0.098/Kundli)**.

| Batch | Sonnet | Haiku | Routing confirmed |
|---|---|---|---|
| planets | $0.0932 | $0.0252 (−73%) | `claude-haiku-4-5-20251001` ✓ |
| numerology | $0.0263 | $0.0082 (−69%) | `claude-haiku-4-5-20251001` ✓ |
| all other 5 batches | unchanged | unchanged | `claude-sonnet-4-20250514` ✓ |

| Section | Observation | Verdict |
|---|---|---|
| Planet placements | Fluent Hindi; correct sign/house/lord/nakshatra; warm tone; no English bleed. ~15–30% shorter — drops Sonnet's extended opening metaphors but keeps full astrological substance. | OK |
| Numerology | Fluent, factually correct (moolank/bhagyank/success/connection); ~7–13% shorter; equivalent content. | OK |

**Decision: SHIP.** Haiku voice approved by user — content quality holds; the only diff is
less ornamentation, acceptable for the cost saving. Kill-switch
(`USE_HAIKU_FOR_SIMPLE_NARRATIVES=false`) reverts instantly if the metaphor framing is
wanted back later.

**Status:** SHIPPED (kill-switch on by default) — A/B verified, decision SHIP.

**Next candidates (don't implement until this A/B passes, one at a time):**
1. `remedy` ($0.029 → ~$0.010) — formulaic, likely safe
2. `misc` / outer planets ($0.043 → ~$0.014) — descriptive, likely safe
3. `yoga` ($0.050 → ~$0.017) — more interpretive, test carefully

Keep `md_journey` and `thematic` on Sonnet — flagship narratives customers read most closely.

## Lever 5a: Remedy batch cohesion

- Per-item word count target: 120-180 → 90-120
- Per-item tokens (hi): 1100 → 500, (en): 700 → 350
- Cohesion clause added: yes (remedies cross-reference each other as unified plan)
- Cache version: v2 (forces regeneration of remedy narratives)

**Status:** SHIP — pending verification on live Kundli. Check remedy sections for cross-referencing and no truncation.
