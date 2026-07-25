package fabric.policy

import future.keywords.every

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

default allow := false

allow {
    agent_trust := class_min_trust[input.agent_class]
    server_trust := trust_levels[input.server_trust_level]
    server_trust >= agent_trust
    resource_allowed
}

approval_required {
    input.server_trust_level == "approval-gated"
    input.agent_class != "agent:admin"
}

default cross_team_allowed := false

cross_team_allowed {
    input.agent_namespace == input.server_namespace
}

cross_team_allowed {
    input.server_namespace == ""
}

capability_dimensions := input.declared_dimensions

resource_allowed {
    not capability_dimensions
}

resource_allowed {
    count(capability_dimensions) == 0
}

resource_allowed {
    every dim in capability_dimensions {
        dim_allowed(dim)
    }
}

dim_allowed(dim) {
    input.identity_resources[dim] != null
    some allowed_value
    input.identity_resources[dim][allowed_value] == input.request_resources[dim]
}

resource_violations[dim] := {
    "dimension": dim,
    "requested": input.request_resources[dim],
    "allowed": input.identity_resources[dim],
} {
    some dim in capability_dimensions
    not dim_allowed(dim)
}

result := {
    "allow": allow,
    "approval_required": approval_required,
    "cross_team": cross_team_allowed,
    "trust_level": input.server_trust_level,
    "agent_class": input.agent_class,
    "resource_allowed": resource_allowed,
    "resource_violations": resource_violations,
}
