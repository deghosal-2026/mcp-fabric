# Security Testing Guide

How to run and interpret the confused-deputy fuzz test harness.

## Overview

The fuzz harness (`tests/security/test_confused_deputy_fuzz.py`) empirically validates the identity-binding catch rate formula:

```
catch = 1 - (pack_size - 1) / (total_resources_in_domain - 1)
```

It runs 8 scenarios, each simulating a confused-deputy attack where an agent's bindings are exploited to access unintended resources. The empirical catch rate is compared against the theoretical value (max error < 0.001).

## 8 Scenarios

| Scenario | R | P | Expected Catch | What It Tests |
|---|---|---|---|---|
| Per-resource identity | 512 | 1 | 1.0000 | Narrowest pack — complete protection |
| Small pack | 512 | 16 | ~0.9706 | Small pack — strong but not perfect |
| Medium pack | 512 | 64 | ~0.8767 | Moderate pack — most real-world case |
| Large pack | 512 | 256 | ~0.5010 | Large pack — half of attacks slip through |
| Everything pack | 512 | 512 | 0.0000 | Giant pack — zero protection (the residual) |
| Cross-capability | 512 | 64 | 1.0000 | Attack targets a different capability entirely |
| Mixed dimensions | 512 | 64 | ~0.8767 | Multiple resource dims — primary dim dominates |
| Cross-identity redirect | 512 | 64 | 1.0000 | Attack targets another identity's resources |

## Running

```bash
# Default run (40k iterations x 3 seeds = 120k per scenario)
poetry run python tests/security/test_confused_deputy_fuzz.py

# Quick smoke test (10k iterations)
poetry run python tests/security/test_confused_deputy_fuzz.py --iterations 10000

# Custom parameters
poetry run python tests/security/test_confused_deputy_fuzz.py \
    --resources 256 \
    --iterations 50000 \
    --seeds 7,13,42 \
    --output report.json
```

### CLI Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--resources` | 512 | Total resources in the domain |
| `--iterations` | 40000 | Iterations per seed per scenario |
| `--seeds` | 24,42,99 | Comma-separated RNG seeds |
| `--output` | (stdout) | Path to write JSON report |

## Interpreting Results

The table printed to stdout shows:

- **P** — Pack size (number of bound resources)
- **Expected** — Theoretical catch rate from the closed-form formula
- **Empirical** — Measured catch rate from the simulation
- **Error** — Absolute difference |empirical - theoretical|
- **Blocked** — Total blocked requests across all seeds
- **Total** — Total requests (iterations x seeds)

A **PASS** result means all scenarios have error < 0.001.

## JSON Report

The `--output` flag writes a structured JSON report:

```json
{
  "parameters": {
    "resources": 512,
    "iterations_per_seed": 40000,
    "seeds": [24, 42, 99]
  },
  "scenarios": [
    {
      "name": "per_resource_identity",
      "expected_catch": 1.0,
      "empirical_catch": 1.0,
      "error": 0.0,
      "blocked": 120000,
      "passed": 0
    }
  ],
  "max_error": 0.000622,
  "passed": true
}
```

 ## Nightly CI

A GitHub Actions workflow (`.github/workflows/nightly.yml`) runs the fuzz harness every day at 6 AM UTC. On failure, it uploads the report as a build artifact and prints a notification message.

To trigger manually: go to the Actions tab → Nightly Security Fuzz → Run workflow.

## Lambda-Clustered Adversarial Fuzz (v0.4.0, #440)

The uniform-random confused-deputy harness above validates the *baseline* catch
rate, but a real attacker does not pick targets uniformly — a similarity-targeting
attacker clusters on semantically similar resources, collapsing catch on a tight
semantic pack. The lambda-clustered harness
(`tests/security/test_adversarial_confusion_fuzz.py`) models this: resources sit on
a 1-D semantic line, and the attacker picks a target with probability proportional
to `exp(lambda * max_sim(allowed, j))`.

- `lambda = 0` → uniform selection → must match the closed-form formula (regression guard).
- `lambda -> large` → attacks concentrate near the pack's semantic band → a **tight
  semantic band** collapses catch toward ~0.07, while a **scattered pack** of the
  same size keeps catch ~0.82. This is the breadth-only coverage gap: same pack
  size, opposite exposure, purely from construction.

Run it directly:

```bash
poetry run python tests/security/test_adversarial_confusion_fuzz.py --iterations 40000 \
  --output /tmp/adversarial-fuzz-report.json
```

Unit tests (`tests/security/test_adversarial_confusion_fuzz_unit.py`) pin the
invariants: uniform baseline matches closed form, band collapses below 0.10,
scattered resists above 0.60, and band is always worse than scattered for the same
size. The nightly workflow runs both harnesses.


## When to Update

Add new scenarios when:
- A new resource dimension type is added
- The binding model changes (e.g., pack inheritance rules)
- A new attack vector is discovered that the formula should account for
