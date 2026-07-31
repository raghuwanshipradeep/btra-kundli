"""Mahakundli report engine.

Layered so the astrology layer stays pure and testable:

    app.astro       — derives every fact from raw AstrologyAPI responses. No I/O, no LLM, no DB.
    app.narrative   — turns facts into prose. Never computes.
    app.validation  — fail-closed gate over the assembled HTML + facts.

See ``app/astro/facts.py`` for the single public entry point (``assemble_facts``).
"""
