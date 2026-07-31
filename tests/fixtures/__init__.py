"""Regression corpus for the Mahakundli engine.

Two kinds of fixture, for two different jobs:

- ``synthetic`` — charts hand-built from explicit longitudes. They exist to exercise the
  awkward cases the spec's Part 9 asks for (a Gandanta Moon, a planet at 0.02° of a sign, a
  cancelled debilitation, a true Kaal Sarp axis, an active Sade Sati, a pre-1970 birth).
  Constructing them from real births would be guesswork; constructing them from longitudes
  makes each one exactly the case it claims to be.

- ``live_*.json`` — real ``fetch_all()`` captures, committed so the adapter is tested against
  shapes AstrologyAPI actually returns rather than shapes we invented. Loaded by
  ``load_live()``; tests that need them skip when they are absent, so the suite stays
  runnable on a clone that has not captured any.
"""
from __future__ import annotations

import json
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent


def live_paths() -> list[Path]:
    return sorted(FIXTURE_DIR.glob("live_*.json"))


def load_live(path: Path):
    """Rehydrate a captured response into a ``KundliData``.

    Imported lazily so ``tests.fixtures`` stays importable without pydantic models loaded.
    """
    from models import KundliData

    return KundliData.model_validate(json.loads(path.read_text(encoding="utf-8")))
