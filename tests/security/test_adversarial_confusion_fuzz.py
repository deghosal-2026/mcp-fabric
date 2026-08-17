#!/usr/bin/env python3
"""Adversarial resource-confusion fuzz harness — λ-clustered (semantically targeted).

Model for a similarity-targeting attacker (alex_spinov's lambda-clustered
methodology): unlike uniform random confusion, a real attacker collapses catch
on a tight semantic pack because redirects land on resources semantically
similar to the pack's own members.

Semantic model (deterministic, dependency-free):
  - Resources sit on a 1-D semantic line indexed 0..R-1.
  - A pack is a set of allowed indices (typically a contiguous "semantic band").
  - The attacker chooses a target index with probability proportional to
        w(j) = exp( lambda * max_sim(allowed, j) )
    where max_sim(allowed, j) = max over a in allowed of (1 - |a - j|/(R-1)).
  - lambda = 0  -> uniform distribution (matches the closed-form baseline).
  - lambda -> large -> attacks concentrate near the allowed band, so a tight
    pack is hit almost exclusively on its own members -> catch collapses.

Key intuition validated here:
  Same pack size (breadth) -> OPPOSITE exposure depending on construction:
    - scattered pack  (allowed indices spread out) -> attacker can't cluster
      on a single semantic band -> high catch preserved at high lambda.
    - semantic band   (allowed indices contiguous)  -> high lambda collapses
      catch toward 0, exactly the v0.2.0 catch-rate-formula coverage gap.

Usage:
    poetry run python tests/security/test_adversarial_confusion_fuzz.py
        --resources 512 --iterations 40000 --output /tmp/adversarial.json
"""

import argparse
import json
import math
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_R = 512
DEFAULT_N = 40000
DEFAULT_SEEDS = [24, 42, 99]
#: Attacker clustering values swept by the harness. 0 == uniform baseline.
DEFAULT_LAMBDAS = [0.0, 1.0, 20.0, 100.0]
#: A semantic band at this lambda must collapse catch below this threshold.
BAND_COLLAPSE_LAMBDA = 100.0
BAND_COLLAPSE_THRESHOLD = 0.10
#: Uniform baseline must match closed form within this error (statistical,
#: P=64/R=512 over 120k samples yields ~1e-3 std; 0.01 is a safe bound).
MAX_ERROR = 0.01
PACK_SIZE = 64


@dataclass
class ScenarioResult:
    name: str
    description: str
    r: int
    p: int
    lam: float
    n: int
    seeds: list[int]
    expected_catch: float
    empirical_catch: float
    error: float
    blocked: int
    passed: int


@dataclass
class Report:
    parameters: dict[str, Any]
    scenarios: list[dict[str, Any]]
    band_triggered: bool
    passed: bool
    summary: str


def compute_expected_catch(p: int, r: int) -> float:
    if r <= 1:
        return 1.0
    return max(0.0, min(1.0, 1.0 - (p - 1) / (r - 1)))


def _max_sim_to_allowed(allowed: list[int], j: int, r: int) -> float:
    """Semantic similarity (0..1) of index j to the nearest allowed member."""
    if r <= 1:
        return 1.0
    best = 0.0
    for a in allowed:
        sim = 1.0 - abs(a - j) / (r - 1)
        if sim > best:
            best = sim
    return best


def _attacker_weights(allowed: list[int], r: int, lam: float) -> list[float]:
    """Unnormalised target weights w(j) under a lambda-clustered attacker."""
    weights = [math.exp(lam * _max_sim_to_allowed(allowed, j, r)) for j in range(r)]
    return weights


def _run_clustered(allowed: list[int], r: int, lam: float, n: int, seed: int) -> tuple[int, int]:
    """Run n attacks against a lambda-clustered supplier.

    Returns (blocked, passed). A target inside `allowed` is "passed" (the
    redirect succeeded / not caught); outside is "blocked" (caught).
    """
    rng = random.Random(seed)
    weights = _attacker_weights(allowed, r, lam)
    total = sum(weights)
    # Use cumulative distribution for O(log R) sampling.
    cumulative: list[float] = []
    acc = 0.0
    for w in weights:
        acc += w / total
        cumulative.append(acc)

    allowed_set = set(allowed)
    blocked = 0
    passed = 0
    for _ in range(n):
        u = rng.random()
        # binary search over cumulative
        lo, hi = 0, len(cumulative) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cumulative[mid] < u:
                lo = mid + 1
            else:
                hi = mid
        target = lo
        if target in allowed_set:
            passed += 1
        else:
            blocked += 1
    return blocked, passed


def _semantic_band(r: int, p: int, offset: int = 0) -> list[int]:
    """A tight contiguous block of p indices starting at `offset`."""
    return list(range(offset, offset + p))


def _make_scattered(r: int, p: int, seed: int = 7) -> list[int]:
    """p indices spread evenly across the line (semantically dispersed)."""
    if p >= r:
        return list(range(r))
    step = r / p
    idx = sorted(int(i * step) for i in range(p))
    # dedupe, fill if needed
    uniq: list[int] = []
    seen: set[int] = set()
    for i in idx:
        if i not in seen and i < r:
            seen.add(i)
            uniq.append(i)
    while len(uniq) < p:
        cand = random.Random(seed).randrange(0, r)
        if cand not in seen:
            seen.add(cand)
            uniq.append(cand)
    return sorted(uniq)


def _aggregate(
    name: str,
    description: str,
    r: int,
    allowed: list[int],
    lam: float,
    n: int,
    seeds: list[int],
    expected: float,
) -> ScenarioResult:
    total_blocked = 0
    total_passed = 0
    for seed in seeds:
        b, pobj = _run_clustered(allowed, r, lam, n, seed)
        total_blocked += b
        total_passed += pobj
    total_n = total_blocked + total_passed
    empirical = total_blocked / total_n if total_n > 0 else 0.0
    return ScenarioResult(
        name=name,
        description=description,
        r=r,
        p=len(set(allowed)),
        lam=lam,
        n=n,
        seeds=seeds,
        expected_catch=expected,
        empirical_catch=empirical,
        error=abs(empirical - expected),
        blocked=total_blocked,
        passed=total_passed,
    )


def generate_scenarios(
    r: int,
    n: int,
    seeds: list[int],
    lambdas: list[float],
) -> list[ScenarioResult]:
    p = min(PACK_SIZE, r)
    band = _semantic_band(r, p)
    scattered = _make_scattered(r, p)
    uniform_expected = compute_expected_catch(p, r)

    results: list[ScenarioResult] = []

    # Uniform baseline (lambda=0) sweep — must match closed form.
    for lam in [0.0]:
        results.append(
            _aggregate(
                "uniform_baseline",
                f"Uniform baseline (lambda={lam}): catch must match closed form",
                r,
                band,
                lam,
                n,
                seeds,
                uniform_expected,
            )
        )

    # Scattered pack under increasing clustering — expected to RETAIN catch.
    for lam in [1.0, 20.0, 100.0]:
        results.append(
            _aggregate(
                f"scattered_lam{lam:g}",
                f"Scattered pack at lambda={lam:g}: mean similarity low, catch preserved",
                r,
                scattered,
                lam,
                n,
                seeds,
                uniform_expected,
            )
        )

    # Semantic band under increasing clustering — expected to COLLAPSE.
    for lam in [1.0, 20.0, 100.0]:
        results.append(
            _aggregate(
                f"band_lam{lam:g}",
                f"Semantic band at lambda={lam:g}: tight cluster collapses catch",
                r,
                band,
                lam,
                n,
                seeds,
                uniform_expected,
            )
        )

    return results


def run_all(
    r: int = DEFAULT_R,
    n: int = DEFAULT_N,
    seeds: list[int] | None = None,
    lambdas: list[float] | None = None,
) -> Report:
    if seeds is None:
        seeds = DEFAULT_SEEDS
    if lambdas is None:
        lambdas = DEFAULT_LAMBDAS

    results = generate_scenarios(r, n, seeds, lambdas)

    band = [s for s in results if s.name.startswith("band_lam") and s.lam >= BAND_COLLAPSE_LAMBDA]
    band_triggered = bool(band) and all(b.empirical_catch < BAND_COLLAPSE_THRESHOLD for b in band)

    uniform = next((s for s in results if s.name == "uniform_baseline"), None)
    uniform_ok = uniform is not None and uniform.error < MAX_ERROR

    passed = uniform_ok and band_triggered

    return Report(
        parameters={
            "resources": r,
            "iterations_per_seed": n,
            "seeds": seeds,
            "lambdas": lambdas,
            "pack_size": PACK_SIZE,
            "band_collapse_lambda": BAND_COLLAPSE_LAMBDA,
            "band_collapse_threshold": BAND_COLLAPSE_THRESHOLD,
        },
        scenarios=[asdict(s) for s in results],
        band_triggered=band_triggered,
        passed=passed,
        summary=(
            f"uniform_ok={uniform_ok} band_triggered={band_triggered} "
            f"{'PASS' if passed else 'FAIL'}"
        ),
    )


def format_table(results: list[ScenarioResult]) -> str:
    header = (
        f"{'Scenario':<20} {'P':>4} {'lam':>6} {'Expected':>9}"
        f" {'Empirical':>10} {'Error':>8} {'Blocked':>8} {'Total':>7}"
    )
    sep = "-" * len(header)
    lines = [sep, header, sep]
    for s in results:
        total = s.blocked + s.passed
        lines.append(
            f"{s.name:<20} {s.p:>4} {s.lam:>6.1f} {s.expected_catch:>9.6f}"
            f" {s.empirical_catch:>10.6f} {s.error:>8.6f} {s.blocked:>8} {total:>7}"
        )
    lines.append(sep)
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lambda-clustered adversarial resource-confusion fuzz harness"
    )
    parser.add_argument(
        "--resources", type=int, default=DEFAULT_R, help="Total resources in domain"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=DEFAULT_N,
        help="Iterations per scenario per seed",
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default=",".join(str(s) for s in DEFAULT_SEEDS),
        help="Comma-separated seed values",
    )
    parser.add_argument(
        "--lambdas",
        type=str,
        default=",".join(f"{lam:g}" for lam in DEFAULT_LAMBDAS),
        help="Comma-separated lambda (clustering) values to sweep",
    )
    parser.add_argument("--output", type=str, default=None, help="Write JSON report to file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    seeds = [int(s.strip()) for s in args.seeds.split(",")]
    lambdas = [float(s.strip()) for s in args.lambdas.split(",")]

    report = run_all(r=args.resources, n=args.iterations, seeds=seeds, lambdas=lambdas)

    print(format_table([ScenarioResult(**s) for s in report.scenarios]))
    print()
    print(report.summary)

    if args.output:
        path = Path(args.output)
        path.write_text(json.dumps(asdict(report), indent=2))
        print(f"\nReport written to {path.resolve()}")

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
