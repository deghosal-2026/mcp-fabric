package fabric.policy

test_allow_trusted_server_for_admin {
    allow with input as {
        "agent_class": "agent:admin",
        "server_trust_level": "trusted",
        "capability": "code:search",
        "team_namespace": "team:platform",
    }
}

test_allow_trusted_server_for_incident_responder {
    allow with input as {
        "agent_class": "agent:incident-responder",
        "server_trust_level": "trusted",
        "capability": "code:search",
        "team_namespace": "team:platform",
    }
}

test_allow_restricted_for_incident_responder {
    allow with input as {
        "agent_class": "agent:incident-responder",
        "server_trust_level": "restricted",
        "capability": "code:search",
    }
}

test_deny_unreviewed_server_for_incident_responder {
    not allow with input as {
        "agent_class": "agent:incident-responder",
        "server_trust_level": "unreviewed",
    }
}

test_allow_unreviewed_for_new_hire {
    allow with input as {
        "agent_class": "agent:new-hire",
        "server_trust_level": "unreviewed",
        "capability": "code:search",
    }
}

test_approval_required_for_gated_capability {
    approval_required with input as {
        "agent_class": "agent:code-reviewer",
        "server_trust_level": "approval-gated",
    }
}

test_admin_bypasses_approval {
    not approval_required with input as {
        "agent_class": "agent:admin",
        "server_trust_level": "approval-gated",
    }
}

test_cross_team_allowed_same_namespace {
    cross_team_allowed with input as {
        "agent_namespace": "team:platform",
        "server_namespace": "team:platform",
    }
}

test_cross_team_allowed_global_server {
    cross_team_allowed with input as {
        "agent_namespace": "team:security",
        "server_namespace": "",
    }
}

test_cross_team_denied_different_namespace {
    not cross_team_allowed with input as {
        "agent_namespace": "team:platform",
        "server_namespace": "team:security",
    }
}

# ─── Resource-Aware Policy Tests ───

test_resource_allowed_all_dimensions_match {
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

test_resource_denied_when_dimension_mismatches {
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

test_resource_allowed_capability_without_dimensions {
    allow with input as {
        "agent_class": "agent:developer",
        "server_trust_level": "trusted",
        "capability": "code:search",
    }
}

test_resource_denied_when_identity_bindings_empty {
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

test_resource_violations_populated_on_deny {
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

test_resource_empty_violations_when_all_match {
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

test_resource_allowed_multi_value_identity_binding {
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

test_resource_denied_missing_tenant_dimension {
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

test_resource_allowed_for_database_query {
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

test_resource_denied_for_database_query_wrong_tenant {
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

test_resource_denied_for_rollback_wrong_env {
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