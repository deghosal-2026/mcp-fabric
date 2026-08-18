"""Tests for structured policy-denial feedback (#443).

A denial is a *result* (impact + reason + next allowed step), not an opaque
failure. These tests verify:
  1. `_build_denial` translates each OPA deny flag into a DenialResult.
  2. A fully-allowed decision produces no denial.
  3. The router returns the structured denial payload to the agent.
"""

from api.schemas.common import PolicyDecision
from api.schemas.routing import DenialResult
from api.services.routing_service import RoutingService


def _decision(**overrides: object) -> PolicyDecision:
    base = {
        "allow": True,
        "approval_required": False,
        "trust_level": "trusted",
        "agent_class": "agent:developer",
        "cross_team": False,
        "resource_allowed": True,
        "resource_violations": [],
        "deny_stale_mapping": False,
        "untrusted_write": False,
        "read_only_denied": False,
    }
    base.update(overrides)
    return PolicyDecision(**base)


def test_no_denial_when_allowed() -> None:
    denial = RoutingService._build_denial(_decision(), "code:review")
    assert denial is None


def test_read_only_scope_denial() -> None:
    denial = RoutingService._build_denial(_decision(read_only_denied=True), "deploy:promote")
    assert isinstance(denial, DenialResult)
    assert denial.impact == "none"
    assert denial.reason == "policy:read_only_scope"
    assert denial.suggestion is not None
    assert "read-only" in denial.suggestion


def test_untrusted_write_denial() -> None:
    denial = RoutingService._build_denial(_decision(untrusted_write=True), "doc:write")
    assert isinstance(denial, DenialResult)
    assert denial.reason == "policy:untrusted_write"
    assert "unreviewed" in (denial.suggestion or "")


def test_stale_mapping_denial() -> None:
    denial = RoutingService._build_denial(_decision(deny_stale_mapping=True), "deploy:promote")
    assert isinstance(denial, DenialResult)
    assert denial.reason == "policy:deny_stale_mapping"
    assert "stale" in (denial.suggestion or "")


def test_resource_denial() -> None:
    denial = RoutingService._build_denial(
        _decision(resource_allowed=False, resource_violations=[{"dimension": "env"}]),
        "deploy:promote",
    )
    assert isinstance(denial, DenialResult)
    assert denial.reason == "policy:resource_not_allowed"
    assert denial.suggestion is not None


def test_denial_order_prefers_read_only_scope() -> None:
    """When multiple flags fire, read_only_scope wins (most specific)."""
    denial = RoutingService._build_denial(
        _decision(read_only_denied=True, untrusted_write=True, deny_stale_mapping=True),
        "deploy:promote",
    )
    assert denial is not None
    assert denial.reason == "policy:read_only_scope"
