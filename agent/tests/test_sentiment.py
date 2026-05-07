"""Tests for `SentimentDetector`."""

from __future__ import annotations

from coach_agent.detectors import SentimentDetector


def test_positive_text_produces_positive_tag():
    s = SentimentDetector()
    s.on_final("I'm really happy to help you today, that's wonderful news.", t_ms=1)
    assert s.tag() == "Positive"
    assert s.compound() > 0.3


def test_negative_text_produces_negative_tag():
    s = SentimentDetector()
    s.on_final("This is terrible. I hate it. You are useless.", t_ms=1)
    assert s.tag() == "Negative"
    assert s.compound() < -0.05


def test_flat_text_produces_flat_or_neutral_tag():
    s = SentimentDetector()
    s.on_final("The account number is 1234567890.", t_ms=1)
    # Flat or Neutral — either is acceptable for factual text.
    assert s.tag() in {"Flat", "Neutral"}


def test_dip_event_fires_only_on_downgrade():
    s = SentimentDetector()
    s.on_final("Wonderful, amazing, so happy.", t_ms=1_000)
    assert s.tag() == "Positive"

    # First downgrade — should emit a dip.
    events = s.on_final("Terrible, awful, I hate this.", t_ms=2_000)
    assert any(e.kind == "sentiment_dip" for e in events)

    # Further downgrade into Negative — another dip is legitimate.
    events2 = s.on_final("Still bad. Still awful.", t_ms=3_000)
    assert any(e.kind == "sentiment_dip" for e in events2)

    # Upgrade back to Positive — no dip on improvements.
    events3 = s.on_final("Actually things are great now, I love it.", t_ms=4_000)
    assert not any(e.kind == "sentiment_dip" for e in events3)


def test_no_dip_when_tag_is_unchanged():
    # Same-tone sequential finals shouldn't emit dips because the tag
    # doesn't change.
    s = SentimentDetector()
    s.on_final("The weather is mild today.", t_ms=1_000)
    first_tag = s.tag()
    events = s.on_final("The report is on page four.", t_ms=2_000)
    # If the tag did not change, no dip should be emitted; if it did
    # happen to change (VADER noise), the first transition can legitimately
    # fire, so we only assert the invariant conditionally.
    if s.tag() == first_tag:
        assert not any(e.kind == "sentiment_dip" for e in events)


def test_window_ages_out_old_text():
    s = SentimentDetector(window_s=5.0)
    s.on_final("Wonderful wonderful wonderful.", t_ms=0)
    # 30 s later, the original text has aged out.
    s.on_final("Bad bad bad.", t_ms=30_000)
    # After eviction, only "Bad bad bad." contributes to the score.
    assert s.tag() == "Negative"


def test_reset_returns_to_flat():
    s = SentimentDetector()
    s.on_final("Wonderful!", t_ms=1)
    s.reset()
    assert s.tag() == "Flat"
    assert s.compound() == 0.0
