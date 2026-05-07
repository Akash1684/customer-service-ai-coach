"""Tests for `ProhibitedDetector`."""

from __future__ import annotations

from coach_agent.detectors import ProhibitedDetector


def test_exact_match_case_insensitive():
    d = ProhibitedDetector(["I don't know"])
    events = d.on_final("Well, I DON'T KNOW the answer.", t_ms=1)
    assert d.hits == 1
    assert d.last_match == "i don't know"
    assert events[0].detail == "i don't know"


def test_fuzzy_match_catches_missing_apostrophe():
    d = ProhibitedDetector(["I don't know"])
    events = d.on_final("Honestly, I dont know.", t_ms=1)
    assert d.hits == 1
    assert events[0].meta["match"] == "fuzzy"  # type: ignore[index]


def test_unrelated_text_does_not_match():
    d = ProhibitedDetector(["I don't know"])
    assert d.on_final("Let me look into that for you.", t_ms=1) == []
    assert d.hits == 0


def test_multiple_phrases_in_one_final_all_fire():
    d = ProhibitedDetector(["I don't know", "calm down"])
    events = d.on_final("Look, calm down, I don't know what happened.", t_ms=1)
    assert d.hits == 2
    matched = {e.detail for e in events}
    assert matched == {"calm down", "i don't know"}


def test_set_phrases_replaces_list_without_resetting_counter():
    d = ProhibitedDetector(["I don't know"])
    d.on_final("I don't know.", t_ms=1)
    assert d.hits == 1
    d.set_phrases(["that's not my problem"])
    d.on_final("That's not my problem.", t_ms=2)
    assert d.hits == 2


def test_reset_clears_counters_and_last_match():
    d = ProhibitedDetector(["calm down"])
    d.on_final("Please calm down.", t_ms=1)
    d.reset()
    assert d.hits == 0
    assert d.last_match is None


def test_empty_text_is_ignored():
    d = ProhibitedDetector(["calm down"])
    assert d.on_final("   ", t_ms=1) == []
    assert d.hits == 0
