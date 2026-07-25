package fabric.policy

test_allow_trusted_server_for_admin {
    allow with input as {
        "agent_class": "agent:admin",
        "server_trust_level": "trusted",
        "capability": "deployment:promote",
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
