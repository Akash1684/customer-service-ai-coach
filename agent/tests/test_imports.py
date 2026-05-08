"""Smoke test — package is importable and exposes a SemVer version."""

from __future__ import annotations

import re


def test_package_importable() -> None:
    """The `coach_agent` package imports cleanly."""
    import coach_agent  # noqa: F401


def test_package_has_semver_version() -> None:
    """`coach_agent.__version__` is a SemVer string."""
    import coach_agent

    assert isinstance(coach_agent.__version__, str)
    assert re.match(r"^\d+\.\d+\.\d+", coach_agent.__version__), (
        f"Expected SemVer, got {coach_agent.__version__!r}"
    )
