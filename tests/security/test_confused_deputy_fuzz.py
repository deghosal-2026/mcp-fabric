#!/usr/bin/env python3
"""Confused-deputy fuzz test harness for identity-binding catch rate validation.

Empirically validates the closed-form catch rate formula:
    catch = 1 - (pack_size - 1) / (total_resources_in_domain - 1)

Each scenario simulates a confused-deputy attack: an agent with bindings
to P resources (via identity ∩ pack) is attacked with N random requests
targeting various resources in the domain. The empirical catch rate is
the fraction of requests that are blocked.

Usage:
    poetry run python tests/security/test_confused_deputy_fuzz.py
    poetry run python tests/security/test_confused_deputy_fuzz.py
        --pack-sizes 1,16,64,256,512 --output report.json
"""

import argparse
import json
import random
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

DEFAULT_R = 512
DEFAULT_N = 40000
DEFAULT_SEEDS = [24, 42, 99]
MAX_ERROR = 0.001


@dataclass
class ScenarioResult:
    name: str
    description: str
    r: int
    p: int
    n: int
    seeds: list[int]
    expected_catch: float
    empirical_catch: float
    error: float
    blocked: int
    passed: int


@dataclass
class Report:
    parameters: dict
    scenarios: list[dict]
    max_error: float
    passed: bool
    summary: str


def compute_expected_catch(p: int, r: int) -> float:
    if r <= 1:
        return 1.0
    return max(0.0, min(1.0, 1.0 - (p - 1) / (r - 1)))


def _make_domain(r: int, offset: int = 0, prefix: str = "res") -> list[str]:
    return [f"{prefix}-{i}" for i in range(offset, offset + r)]


def _make_set(n: int, offset: int = 0, prefix: str = "res") -> set[str]:
    return {f"{prefix}-{i}" for i in range(offset, offset + n)}


@dataclass
class _SeedRun:
    blocked: int
    passed: int


def _run_single(
    allowed: set[str],
    attack_domain: list[str],
    n: int,
    seed: int,
) -> _SeedRun:
    rng = random.Random(seed)
    blocked = 0
    passed = 0
    for _ in range(n):
        resource = rng.choice(attack_domain)
        if resource in allowed:
            passed += 1
        else:
            blocked += 1
    return _SeedRun(blocked=blocked, passed=passed)


def _aggregate_scenario(
    name: str,
    description: str,
    r: int,
    p: int,
    identity: set[str],
    pack: set[str],
    attack_domain: list[str],
    n: int,
    seeds: list[int],
    expected_override: float | None = None,
) -> ScenarioResult:
    allowed = identity & pack
    total_blocked = 0
    total_passed = 0
    for seed in seeds:
        run = _run_single(allowed, attack_domain, n, seed)
        total_blocked += run.blocked
        total_passed += run.passed
    total_n = total_blocked + total_passed
    expected = expected_override if expected_override is not None else compute_expected_catch(p, r)
    empirical = total_blocked / total_n if total_n > 0 else 0.0
    return ScenarioResult(
        name=name,
        description=description,
        r=r,
        p=p,
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
) -> list[Callable[[], ScenarioResult]]:
    attack_domain = _make_domain(r - 1, offset=1)
    domain_b = _make_domain(r, prefix="cap-b")

    def per_resource() -> ScenarioResult:
        return _aggregate_scenario(
            "per_resource_identity",
            "Per-resource identity: P=1, all mutations target non-owned resources",
            r,
            1,
            _make_set(1),
            _make_set(1),
            attack_domain,
            n,
            seeds,
        )

    def small_pack() -> ScenarioResult:
        return _aggregate_scenario(
            "small_pack",
            "Small pack: P=16, ~97% expected catch",
            r,
            16,
            _make_set(16),
            _make_set(16),
            attack_domain,
            n,
            seeds,
        )

    def medium_pack() -> ScenarioResult:
        return _aggregate_scenario(
            "medium_pack",
            "Medium pack: P=64, ~88% expected catch",
            r,
            64,
            _make_set(64),
            _make_set(64),
            attack_domain,
            n,
            seeds,
        )

    def large_pack() -> ScenarioResult:
        return _aggregate_scenario(
            "large_pack",
            "Large pack: P=256, ~50% expected catch",
            r,
            256,
            _make_set(256),
            _make_set(256),
            attack_domain,
            n,
            seeds,
        )

    def everything_pack() -> ScenarioResult:
        return _aggregate_scenario(
            "everything_pack",
            "Everything pack: P=R, 0% expected catch — documents the residual",
            r,
            r,
            _make_set(r),
            _make_set(r),
            attack_domain,
            n,
            seeds,
        )

    def cross_capability() -> ScenarioResult:
        return _aggregate_scenario(
            "cross_capability",
            "Cross-capability: identity bound to cap A, attacks cap B — all blocked",
            r,
            64,
            _make_set(64),
            _make_set(64),
            domain_b,
            n,
            seeds,
            expected_override=1.0,
        )

    def mixed_dimensions() -> ScenarioResult:
        p = 64
        tool_domain = [f"tool-{i}" for i in range(1, r)]
        identity_tool = _make_set(p, prefix="tool")
        pack_tool = _make_set(p, prefix="tool")
        allowed_tool = identity_tool & pack_tool
        total_blocked = 0
        total_passed = 0
        for seed in seeds:
            rng = random.Random(seed)
            for _ in range(n):
                tool = rng.choice(tool_domain)
                if tool in allowed_tool:
                    total_passed += 1
                else:
                    total_blocked += 1
        total_n = total_blocked + total_passed
        expected = compute_expected_catch(p, r)
        empirical = total_blocked / total_n if total_n > 0 else 0.0
        return ScenarioResult(
            name="mixed_dimensions",
            description="Mixed dims: P=64, stable secondary — catch matches formula",
            r=r,
            p=p,
            n=n,
            seeds=seeds,
            expected_catch=expected,
            empirical_catch=empirical,
            error=abs(empirical - expected),
            blocked=total_blocked,
            passed=total_passed,
        )

    def cross_identity_redirect() -> ScenarioResult:
        return _aggregate_scenario(
            "cross_identity_redirect",
            "Cross-identity redirect: identity A bound to 0..63, mutations target B's 128..191",
            r,
            64,
            _make_set(64),
            _make_set(64),
            sorted(_make_set(64, offset=128)),
            n,
            seeds,
            expected_override=1.0,
        )

    return [
        per_resource,
        small_pack,
        medium_pack,
        large_pack,
        everything_pack,
        cross_capability,
        mixed_dimensions,
        cross_identity_redirect,
    ]


def run_all(
    r: int = DEFAULT_R,
    n: int = DEFAULT_N,
    seeds: list[int] | None = None,
) -> Report:
    if seeds is None:
        seeds = DEFAULT_SEEDS
    scenario_fns = generate_scenarios(r, n, seeds)
    results = [fn() for fn in scenario_fns]

    max_error = max(r.error for r in results)

    return Report(
        parameters={
            "resources": r,
            "iterations_per_seed": n,
            "seeds": seeds,
        },
        scenarios=[asdict(r) for r in results],
        max_error=max_error,
        passed=max_error < MAX_ERROR,
        summary=(
            f"max_error={max_error:.6f} "
            f"{'PASS' if max_error < MAX_ERROR else 'FAIL'}"
            f" (threshold={MAX_ERROR})"
        ),
    )


def format_table(results: list[ScenarioResult]) -> str:
    header = (
        f"{'Scenario':<28} {'P':>4} {'Expected':>9}"
        f" {'Empirical':>10} {'Error':>8} {'Blocked':>8} {'Total':>7}"
    )
    sep = "-" * len(header)
    lines = [sep, header, sep]
    for r in results:
        total = r.blocked + r.passed
        lines.append(
            f"{r.name:<28} {r.p:>4} {r.expected_catch:>9.6f}"
            f" {r.empirical_catch:>10.6f} {r.error:>8.6f} {r.blocked:>8} {total:>7}"
        )
    lines.append(sep)
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Confused-deputy fuzz test for identity-binding catch rate validation"
    )
    parser.add_argument(
        "--resources",
        type=int,
        default=DEFAULT_R,
        help=f"Total resources in domain (default: {DEFAULT_R})",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=DEFAULT_N,
        help=f"Iterations per scenario per seed (default: {DEFAULT_N})",
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default=",".join(str(s) for s in DEFAULT_SEEDS),
        help=f"Comma-separated seed values (default: {','.join(str(s) for s in DEFAULT_SEEDS)})",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Write JSON report to file (default: stdout only)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    seeds = [int(s.strip()) for s in args.seeds.split(",")]

    report = run_all(r=args.resources, n=args.iterations, seeds=seeds)

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
