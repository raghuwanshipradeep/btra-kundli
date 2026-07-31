"""Pure astrology layer.

Every module here is a pure function of its inputs: no network, no filesystem, no clock
reads (``generated_at`` is injected once, from the caller). That is what makes the golden-file
snapshot tests in ``tests/test_facts_golden.py`` meaningful — same input, same output, forever.

Data flows in from ``models.KundliData`` (the raw AstrologyAPI DTO) and out as
``facts.KundliFacts`` (frozen). Nothing downstream of ``facts`` may recompute an
astrological value; it reads the facts object or it does without.
"""
