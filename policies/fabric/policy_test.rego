package fabric.policy

import future.keywords.if
import future.keywords.in

test_allow_trusted_server_for_admin if {
    allow with input as {
        "agent_class": "agent:admin",
        "server_trust_level": "trusted",
        "capability": "code:search",
        "team_namespace": "team:platform",
    }
}

test_allow_trusted_server_for_incident_responder if {
    allow with input as {
        "agent_class": "agent:incident-responder",
        "server_trust_level": "trusted",
        "capability": "code:search",
        "team_namespace": "team:platform",
    }
}

test_allow_restricted_for_incident_responder if {
    allow with input as {
        "agent_class": "agent:incident-responder",
        "server_trust_level": "restricted",
        "capability": "code:search",
    }
}

test_deny_unreviewed_server_for_incident_responder if {
    not allow with input as {
        "agent_class": "agent:incident-responder",
        "server_trust_level": "unreviewed",
    }
}

test_allow_unreviewed_for_new_hire if {
    allow with input as {
        "agent_class": "agent:new-hire",
        "server_trust_level": "unreviewed",
        "capability": "code:search",
    }
}

test_approval_required_for_gated_capability if {
    approval_required with input as {
        "agent_class": "agent:code-reviewer",
        "server_trust_level": "approval-gated",
    }
}

test_admin_bypasses_approval if {
    not approval_required with input as {
        "agent_class": "agent:admin",
        "server_trust_level": "approval-gated",
    }
}

test_cross_team_allowed_same_namespace if {
    cross_team_allowed with input as {
        "agent_namespace": "team:platform",
        "server_namespace": "team:platform",
    }
}

test_cross_team_allowed_global_server if {
    cross_team_allowed with input as {
        "agent_namespace": "team:security",
        "server_namespace": "",
    }
}

test_cross_team_denied_different_namespace if {
    not cross_team_allowed with input as {
        "agent_namespace": "team:platform",
        "server_namespace": "team:security",
    }
}

# ─── Resource-Aware Policy Tests ───

test_resource_allowed_all_dimensions_match if {
    allow with input as {
        "agent_class": "agent:release-engineer",
        "server_trust_level": "trusted",
        "capability": "deployment:promote",
        "identity_resources": {
            "env": ["staging", "dev"],
            "tenant": ["acme-corp"],
            "service": ["config-api"],
        },
        "request_resources": {
            "env": "staging",
            "tenant": "acme-corp",
            "service": "config-api",
        },
        "declared_dimensions": ["env", "tenant", "service"],
    }
}

test_resource_denied_when_dimension_mismatches if {
    not allow with input as {
        "agent_class": "agent:release-engineer",
        "server_trust_level": "trusted",
        "capability": "deployment:promote",
        "identity_resources": {
            "env": ["staging", "dev"],
            "tenant": ["acme-corp"],
        },
        "request_resources": {
            "env": "prod",
            "tenant": "acme-corp",
        },
        "declared_dimensions": ["env", "tenant"],
    }
}

test_resource_allowed_capability_without_dimensions if {
    allow with input as {
        "agent_class": "agent:developer",
        "server_trust_level": "trusted",
        "capability": "code:search",
    }
}

test_resource_denied_when_identity_bindings_empty if {
    not allow with input as {
        "agent_class": "agent:release-engineer",
        "server_trust_level": "trusted",
        "capability": "deployment:promote",
        "identity_resources": {},
        "request_resources": {
            "env": "staging",
            "tenant": "acme-corp",
        },
        "declared_dimensions": ["env", "tenant"],
    }
}

test_resource_violations_populated_on_deny if {
    violations := resource_violations with input as {
        "agent_class": "agent:release-engineer",
        "server_trust_level": "trusted",
        "capability": "deployment:promote",
        "identity_resources": {
            "env": ["staging", "dev"],
            "tenant": ["acme-corp"],
        },
        "request_resources": {
            "env": "prod",
            "tenant": "acme-corp",
        },
        "declared_dimensions": ["env", "tenant"],
    }
    violations["env"] == {
        "dimension": "env",
        "requested": "prod",
        "allowed": ["staging", "dev"],
    }
    not allow with input as {
        "agent_class": "agent:release-engineer",
        "server_trust_level": "trusted",
        "capability": "deployment:promote",
        "identity_resources": {
            "env": ["staging", "dev"],
            "tenant": ["acme-corp"],
        },
        "request_resources": {
            "env": "prod",
            "tenant": "acme-corp",
        },
        "declared_dimensions": ["env", "tenant"],
    }
}

test_resource_empty_violations_when_all_match if {
    violations := resource_violations with input as {
        "agent_class": "agent:release-engineer",
        "server_trust_level": "trusted",
        "capability": "deployment:promote",
        "identity_resources": {
            "env": ["staging"],
            "tenant": ["acme-corp"],
            "service": ["config-api"],
        },
        "request_resources": {
            "env": "staging",
            "tenant": "acme-corp",
            "service": "config-api",
        },
        "declared_dimensions": ["env", "tenant", "service"],
    }
    count(violations) == 0
    allow with input as {
        "agent_class": "agent:release-engineer",
        "server_trust_level": "trusted",
        "capability": "deployment:promote",
        "identity_resources": {
            "env": ["staging"],
            "tenant": ["acme-corp"],
            "service": ["config-api"],
        },
        "request_resources": {
            "env": "staging",
            "tenant": "acme-corp",
            "service": "config-api",
        },
        "declared_dimensions": ["env", "tenant", "service"],
    }
}

test_resource_allowed_multi_value_identity_binding if {
    allow with input as {
        "agent_class": "agent:release-engineer",
        "server_trust_level": "trusted",
        "capability": "deployment:promote",
        "identity_resources": {
            "env": ["dev", "staging", "qa"],
            "tenant": ["acme-corp"],
            "service": ["config-api"],
        },
        "request_resources": {
            "env": "qa",
            "tenant": "acme-corp",
            "service": "config-api",
        },
        "declared_dimensions": ["env", "tenant", "service"],
    }
}

test_resource_denied_missing_tenant_dimension if {
    not allow with input as {
        "agent_class": "agent:release-engineer",
        "server_trust_level": "trusted",
        "capability": "deployment:promote",
        "identity_resources": {
            "env": ["staging"],
            "tenant": ["acme-corp"],
        },
        "request_resources": {
            "env": "staging",
        },
        "declared_dimensions": ["env", "tenant"],
    }
}

test_resource_allowed_for_database_query if {
    allow with input as {
        "agent_class": "agent:developer",
        "server_trust_level": "restricted",
        "capability": "database:query",
        "identity_resources": {
            "tenant": ["acme-corp"],
            "service": ["user-db"],
        },
        "request_resources": {
            "tenant": "acme-corp",
            "service": "user-db",
        },
        "declared_dimensions": ["tenant", "service"],
    }
}

test_resource_denied_for_database_query_wrong_tenant if {
    not allow with input as {
        "agent_class": "agent:developer",
        "server_trust_level": "restricted",
        "capability": "database:query",
        "identity_resources": {
            "tenant": ["acme-corp"],
            "service": ["user-db"],
        },
        "request_resources": {
            "tenant": "evil-corp",
            "service": "user-db",
        },
        "declared_dimensions": ["tenant", "service"],
    }
}

test_resource_denied_for_rollback_wrong_env if {
    not allow with input as {
        "agent_class": "agent:release-engineer",
        "server_trust_level": "approval-gated",
        "capability": "deployment:rollback",
        "identity_resources": {
            "env": ["staging"],
            "tenant": ["acme-corp"],
        },
        "request_resources": {
            "env": "prod",
            "tenant": "acme-corp",
        },
        "declared_dimensions": ["env", "tenant"],
    }
}

# ─── Schema-Digest Tests ───

# Confirms that an admin with "trusted" trust level is blocked when the
# mapping status is "stale" — stale mappings are never routable.
test_deny_stale_mapping_blocks_allow if {
    not allow with input as {
        "agent_class": "agent:admin",
        "server_trust_level": "trusted",
        "capability": "code:search",
        "mapping_status": "stale",
    }
}

# Verifies deny_stale_mapping fires when the mapping status is "rejected".
test_deny_stale_mapping_rejected if {
    deny_stale_mapping with input as {
        "mapping_status": "rejected",
    }
}

# Verifies deny_stale_mapping does NOT fire when status is "active".
test_deny_stale_mapping_not_triggered_active if {
    not deny_stale_mapping with input as {
        "mapping_status": "active",
    }
}

# Verifies deny_stale_mapping fires on an empty status string,
# treating missing/empty status as stale.
test_deny_stale_mapping_empty_is_stale if {
    deny_stale_mapping with input as {
        "mapping_status": "",
    }
}

# ─── Untrusted Write Tests ───

# Verifies that a write tool (deploy_service) on an "unreviewed" server
# triggers the untrusted_write deny rule.
test_untrusted_write_blocks_write_on_unreviewed if {
    untrusted_write with input as {
        "server_trust_level": "unreviewed",
        "tool_name": "deploy_service",
    }
}

# Verifies that a read-only tool (get_status) on an "unreviewed" server
# is exempt from untrusted_write — reads are safe even without review.
test_untrusted_write_allows_read_on_unreviewed if {
    not untrusted_write with input as {
        "server_trust_level": "unreviewed",
        "tool_name": "get_status",
    }
}

# Verifies that write tools on "trusted" servers do NOT trigger untrusted_write.
test_untrusted_write_not_triggered_on_trusted if {
    not untrusted_write with input as {
        "server_trust_level": "trusted",
        "tool_name": "deploy_service",
    }
}

# Verifies that a query-prefixed tool on an "unreviewed" server is
# exempt (query is in the read-only prefix list).
test_untrusted_write_allows_query_on_unreviewed if {
    not untrusted_write with input as {
        "server_trust_level": "unreviewed",
        "tool_name": "query_users",
    }
}

# ─── Raw Context Tests ───

# Verifies that raw_context returns the full input document as-is.
# This ensures the debug/audit field is always populated.
test_raw_context_returns_input if {
    raw_context == {"agent_class": "agent:test"} with input as {"agent_class": "agent:test"}
}

# ─── New Combo: stale + unreviewed = double deny ───

# Verifies that a tool is denied when BOTH conditions are true:
# the mapping is stale AND the server is unreviewed.
test_deny_stale_and_unreviewed if {
    not allow with input as {
        "agent_class": "agent:developer",
        "server_trust_level": "unreviewed",
        "capability": "doc:write",
        "mapping_status": "stale",
        "tool_name": "create_doc",
    }
}
# ─── Agent-Level Read-Only Scope (#445) ───

# Verifies that a read-only-scoped agent is denied a mutating tool.
test_read_only_denied_on_mutating if {
    allow == false with input as {
        "agent_class": "agent:developer",
        "server_trust_level": "trusted",
        "capability": "deploy:promote",
        "mapping_status": "active",
        "tool_name": "deploy_service",
        "agent_read_only": true,
        "tool_class": "mutating",
    }
}

# Verifies that a read-only-scoped agent IS allowed a read-only tool.
test_read_only_allowed_on_read_only_tool if {
    allow with input as {
        "agent_class": "agent:developer",
        "server_trust_level": "trusted",
        "capability": "deploy:list",
        "mapping_status": "active",
        "tool_name": "get_deployments",
        "agent_read_only": true,
        "tool_class": "read_only",
    }
}

# Verifies that a non-read-only agent is NOT denied by the read-only scope rule.
test_read_only_denied_not_triggered_for_full_agent if {
    not read_only_denied with input as {
        "agent_class": "agent:developer",
        "server_trust_level": "trusted",
        "capability": "deploy:promote",
        "mapping_status": "active",
        "tool_name": "deploy_service",
        "agent_read_only": false,
        "tool_class": "mutating",
    }
}

# Verifies that the read_only_denied flag is surfaced in the result output.
test_read_only_denied_flag_in_result if {
    read_only_denied with input as {
        "agent_class": "agent:developer",
        "server_trust_level": "trusted",
        "mapping_status": "active",
        "tool_name": "deploy_service",
        "agent_read_only": true,
        "tool_class": "mutating",
    }
}

# ─── Origin Context (many-to-one collisions, #441) ───

# Verifies that OPA receives the immutable raw call context (server + tool
# identity) so a policy can still distinguish origin despite normalization.
test_raw_context_includes_server_and_tool_identity if {
    ctx := raw_context with input as {
        "agent_class": "agent:developer",
        "server_id": "server-low-trust",
        "tool_name": "promote",
        "capability": "deployment:promote",
    }
    ctx.server_id == "server-low-trust"
    ctx.tool_name == "promote"
}

# Verifies raw_context is distinct for two different origins, so a policy can
# key on the origin (e.g. deny a low-trust server presenting a high-trust
# capability name).
test_raw_context_distinguishes_origin if {
    a := raw_context with input as {"server_id": "server-a", "tool_name": "promote"}
    b := raw_context with input as {"server_id": "server-b", "tool_name": "promote"}
    a != b
}
