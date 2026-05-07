"""Tests for `FillerDetector`."""

from __future__ import annotations

from coach_agent.config import DEFAULT_FILLER_WORDS
from coach_agent.detectors import FillerDetector


def test_counts_single_word_fillers():
    d = FillerDetector(DEFAULT_FILLER_WORDS)
    events = d.on_final("Well um like I was thinking, uh, yeah.", t_ms=1000)
    kinds = [e.detail for e in events]
    assert kinds == ["well", "um", "like", "uh"]
    assert d.total == 4
    assert d.last_word == "uh"


def test_counts_bigram_fillers_without_double_counting_you():
    d = FillerDetector(["you know", "you"])  # "you" as unigram would double
    events = d.on_final("You know, this is hard.", t_ms=500)
    # Bigram `you know` should be consumed as a single hit; the standalone
    # `you` unigram must not also fire on the same `you`.
    assert [e.detail for e in events] == ["you know"]
    assert d.total == 1


def test_case_and_punctuation_insensitive():
    d = FillerDetector(["um"])
    events = d.on_final("UM, um. uM! Um", t_ms=1)
    assert d.total == 4
    assert [e.detail for e in events] == ["um", "um", "um", "um"]


def test_ignores_empty_and_whitespace_text():
    d = FillerDetector(["um"])
    assert d.on_final("", t_ms=1) == []
    assert d.on_final("   ", t_ms=1) == []
    assert d.total == 0


def test_same_filler_repeated_three_times_counts_three():
    d = FillerDetector(["um"])
    events = d.on_final("um um um", t_ms=1)
    assert d.total == 3
    assert len(events) == 3


def test_reset_clears_counters():
    d = FillerDetector(["um"])
    d.on_final("um um", t_ms=1)
    assert d.total == 2
    d.reset()
    assert d.total == 0
    assert d.last_word is None


def test_unknown_tokens_are_ignored():
    d = FillerDetector(["um"])
    assert d.on_final("Thank you for calling customer service.", t_ms=1) == []
    assert d.total == 0
