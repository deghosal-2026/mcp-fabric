"""Unit tests for the lambda-clustered adversarial resource-confusion fuzz harness.

Validates the two invariants that make the harness meaningful:
  1. The uniform baseline (lambda=0) reproduces the closed-form catch-rate
     formula, so the harness is consistent with the v0.2.0 math.
  2. A semantic band collapses catch under a similarity-targeting attacker
     (high lambda), while a scattered pack of the same size does NOT — the
     exact coverage gap that breadth-only scoring hides.
"""

from tests.security.test_adversarial_confusion_fuzz import (
    MAX_ERROR,
    _make_scattered,
    _run_clustered,
    _semantic_band,
    compute_expected_catch,
    generate_scenarios,
)


def test_uniform_baseline_matches_closed_form() -> None:
    """lambda=0 gives uniform selection -> catch matches 1-(P-1)/(R-1)."""
    r, p = 512, 64
    expected = compute_expected_catch(p, r)
    band = _semantic_band(r, p)
    blocked, passed = _run_clustered(band, r, 0.0, 80000, seed=42)
    empirical = blocked / (blocked + passed)
    assert abs(empirical - expected) < MAX_ERROR


def test_semantic_band_collapses_under_high_lambda() -> None:
    """A tight band is caught far less often than the closed-form baseline."""
    r, p = 512, 64
    band = _semantic_band(r, p)
    blocked, passed = _run_clustered(band, r, 100.0, 80000, seed=42)
    empirical = blocked / (blocked + passed)
    assert empirical < 0.10


def test_scattered_pack_resists_high_lambda() -> None:
    """A scattered pack keeps high catch even at high clustering."""
    r, p = 512, 64
    corr = _make_scattered(r, p)
    blocked, passed = _run_clustered(corr, r, 100.0, 80000, seed=42)
    empirical = blocked / (blocked + passed)
    assert empirical > 0.60


def test_band_worse_than_scattered_same_size() -> None:
    """Same breadth, opposite exposure: band << scattered at high lambda."""
    r, p = 512, 64
    band = _semantic_band(r, p)
    corr = _make_scattered(r, p)
    b_blocked, b_passed = _run_clustered(band, r, 100.0, 80000, seed=42)
    s_blocked, s_passed = _run_clustered(corr, r, 100.0, 80000, seed=42)
    band_catch = b_blocked / (b_blocked + b_passed)
    scattered_catch = s_blocked / (s_blocked + s_passed)
    assert band_catch < scattered_catch


def test_generate_scenarios_returns_all_names() -> None:
    """The harness emits uniform + scattered + band rows with expected fields."""
    r, n, seeds = 128, 2000, [1, 2]
    results = generate_scenarios(r, n, seeds, [0.0, 20.0, 100.0])
    names = {s.name for s in results}
    assert "uniform_baseline" in names
    assert any(x.startswith("scattered_lam") for x in names)
    assert any(x.startswith("band_lam") for x in names)
    for s in results:
        assert 0.0 <= s.empirical_catch <= 1.0
        assert s.p <= s.r
