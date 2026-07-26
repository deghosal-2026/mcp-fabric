package fabric.policy

import future.keywords.every
import future.keywords.if

trust_levels := {
    "trusted": 3,
    "restricted": 2,
    "approval-gated": 1,
    "unreviewed": 0,
}

class_min_trust := {
    "agent:admin": 3,
    "agent:incident-responder": 2,
    "agent:deploy-monitor": 2,
    "agent:code-reviewer": 1,
    "agent:developer": 1,
    "agent:release-engineer": 2,
    "agent:new-hire": 0,
}

# Read-only tool name prefixes (matching registry_service._READ_ONLY_PREFIXES).
# Tools starting with these prefixes are considered safe (non-mutating) and
# are exempt from the untrusted-write deny rule.
_read_only_prefixes := {"get", "list", "search", "read", "find", "query", "check"}

default allow := false

allow if {
    agent_trust := class_min_trust[input.agent_class]
    server_trust := trust_levels[input.server_trust_level]
    server_trust >= agent_trust
    resource_allowed
    not deny_stale_mapping
}

approval_required if {
    input.server_trust_level == "approval-gated"
    input.agent_class != "agent:admin"
}

default cross_team_allowed := false

cross_team_allowed if {
    input.agent_namespace == input.server_namespace
}

cross_team_allowed if {
    input.server_namespace == ""
}

capability_dimensions := input.declared_dimensions

resource_allowed if {
    not capability_dimensions
}

resource_allowed if {
    count(capability_dimensions) == 0
}

resource_allowed if {
    every dim in capability_dimensions {
        dim_allowed(dim)
    }
}

dim_allowed(dim) if {
    input.identity_resources[dim] != null
    some allowed_value
    input.identity_resources[dim][allowed_value] == input.request_resources[dim]
}

resource_violations[dim] := {
    "dimension": dim,
    "requested": input.request_resources[dim],
    "allowed": input.identity_resources[dim],
} if {
    some dim in capability_dimensions
    not dim_allowed(dim)
}

# ─── Schema-Digest Safety ───

# Deny routing when the mapping status is not "active".
# This prevents routing through stale/rejected mappings even if the
# routing layer allows it. redundant security layer.
default deny_stale_mapping := false

deny_stale_mapping if {
    input.mapping_status != "active"
}

# ─── Trust-Level Tool Safety ───

# Deny write (non-read-only) tool invocations on untrusted servers.
# Untrusted = "unreviewed" or missing trust level.
# Read-only tools (get/list/search/read/find/query/check) are exempt.
default untrusted_write := false

# Triggered when the server has an explicit "unreviewed" trust level.
# Any non-read-only tool is blocked until a human reviews and promotes the trust level.
untrusted_write if {
    input.server_trust_level == "unreviewed"
    not _is_read_only_tool(input.tool_name)
}

# Triggered when the server trust level is empty/missing.
# This catches servers that were registered without a trust level set at all.
untrusted_write if {
    input.server_trust_level == ""
    not _is_read_only_tool(input.tool_name)
}

# Returns true if the tool name starts with any known read-only prefix.
# This is the inline check used by untrusted_write to exempt safe tools
# (get/list/search/read/find/query/check) from the deny rule.
_is_read_only_tool(name) if {
    some prefix in _read_only_prefixes
    startswith(name, prefix)
}

# ─── Raw Context (debugging / audit trail) ───

# Exposes the entire input document as a raw_context output field.
# This provides a full audit trail — every decision input is visible
# in the OPA response for debugging and compliance logging.
raw_context := input

result := {
    "allow": allow,
    "approval_required": approval_required,
    "cross_team": cross_team_allowed,
    "trust_level": input.server_trust_level,
    "agent_class": input.agent_class,
    "resource_allowed": resource_allowed,
    "resource_violations": resource_violations,
    # True when the mapping status is not "active" — prevents routing through
    # stale, rejected, or empty-status mappings even if all other checks pass.
    "deny_stale_mapping": deny_stale_mapping,
    # True when a non-read-only tool targets an unreviewed or trust-less server.
    # Mirrors the untrusted_write rule output for easy debugging.
    "untrusted_write": untrusted_write,
}
