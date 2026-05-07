"""Tests for `_looks_hallucinated` — the Whisper silence-hallucination guard.

Key invariants:
- Legitimate filler words ("um", "uh", "ah", "oh") MUST pass through so the
  FillerDetector can count them. They are *real speech*, not hallucinations.
- Repeated known silence-phrases ("Okay.", "bye bye") MUST be dropped
  because Whisper emits them on near-silent audio (YouTube caption
  artifacts in its training data).
"""

from coach_agent.stt.local_whisper import _looks_hallucinated


def test_flags_common_exact_phrases():
    for t in ["Okay", "okay.", "You", "you.", "Thank you.", "Thanks for watching!", "."]:
        assert _looks_hallucinated(t), f"expected hallucination: {t!r}"


def test_flags_short_silence_phrase_bursts():
    """2–3 repetitions of a known silence-phrase are hallucinations."""
    assert _looks_hallucinated("Okay. Okay.")
    assert _looks_hallucinated("Okay. Okay. Okay.")
    assert _looks_hallucinated("okay okay")
    assert _looks_hallucinated("bye bye")


def test_flags_long_repeated_bursts():
    assert _looks_hallucinated(" ".join(["Okay."] * 29))
    assert _looks_hallucinated("okay okay okay okay")
    assert _looks_hallucinated(". . . . . . . . .")


def test_does_not_flag_legitimate_filler_words():
    """Fillers are real speech — FillerDetector must see them."""
    for t in ["Um.", "um", "uh", "Ah.", "oh", "huh"]:
        assert not _looks_hallucinated(t), f"filler falsely flagged: {t!r}"


def test_does_not_flag_stuttered_fillers():
    """Short stutters like 'um um um' are plausible real speech."""
    assert not _looks_hallucinated("um um um")
    assert not _looks_hallucinated("uh uh")


def test_passes_real_speech():
    for t in [
        "Hello, my name is Akash.",
        "This is a test of the customer service coach system.",
        "Can you tell me about the billing issue?",
        "Okay, let me take a look at your account.",
        "I understand your concern and I'd be happy to help.",
        "Thank you for calling customer service.",
        "You can reach us at that number.",
        "So um yeah let me check that.",
        "um like basically I was trying to help.",
    ]:
        assert not _looks_hallucinated(t), f"false positive: {t!r}"


def test_empty_is_flagged():
    assert _looks_hallucinated("")
    assert _looks_hallucinated("   ")
