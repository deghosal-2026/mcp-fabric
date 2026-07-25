package fabric.policy

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
    "agent:new-hire": 0,
}

default allow := false

allow {
    agent_trust := class_min_trust[input.agent_class]
    server_trust := trust_levels[input.server_trust_level]
    server_trust >= agent_trust
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

result := {
    "allow": allow,
    "approval_required": approval_required,
    "cross_team": cross_team_allowed,
    "trust_level": input.server_trust_level,
    "agent_class": input.agent_class,
}
