# MCP Fabric — Product Requirements Document

> **Status:** Approved  
> **Version:** 1.0  
> **Last updated:** 2026-07-22  
> **Approved by:** Debashish Ghosal

> **TLDR:** A fabric layer for MCP servers: discovery, schema normalization, trust policies, capability routing, and tool composition across many MCP backends.

---

## WHY — The Problem

### The Painful Truth

A pile of MCP servers is not a platform.

MCP solves one important problem: a standard interface for AI tools and data. It does not solve the next problem that appears immediately after success: tool ecosystem sprawl.

As soon as a team adds multiple MCP servers, several hard questions emerge:

- Which tools should be exposed to which agents?
- How should overlapping capabilities be described?
- What trust level should be assigned to each server?
- How should an agent choose between several tools that look similar?
- How should a platform team audit and govern usage across the whole tool ecosystem?

### Market Context

MCP is growing rapidly. The number of publicly available MCP servers, clients, and integrations is accelerating. Much of the community energy right now is focused on building individual servers — connecting one more tool, wrapping one more API.

That work is valuable, but it creates a second-order problem: the more successful MCP becomes, the more urgent the governance and discovery problem becomes.

MCP Fabric occupies the space directly above that growth curve. If MCP grows, the need for tool governance, routing, packaging, and discovery grows with it.

### User Problems

**Problem 1: Tool Discovery Is Unstructured**

Agents and developers see many tools but lack a coherent capability model. There is no way to ask "which server can help me understand this incident?" and get a ranked, policy-respected answer.

**Problem 2: Schema Drift and Naming Drift**

Different servers expose similar actions with different names, parameters, and result conventions. Two servers might both offer "search" but expect different inputs and return different shapes. Agents have no standard way to normalize across them.

**Problem 3: Trust and Permission Ambiguity**

There is often no clear answer to which tools are safe for which workflows. A code search tool and a deployment tool live side by side with the same implicit trust level. Platform teams lack controls to restrict powerful tools to specific agent classes.

**Problem 4: No Tool Ecosystem Governance**

Even if individual servers are well built, the platform has no single place to audit usage, resolve overlap, or curate bundles for different users. Compliance and oversight are manual or nonexistent.

---

## WHAT — MCP Fabric

### Vision

An organization has many MCP servers: code search, docs, incidents, PRs, cost analytics, deployment tools, knowledge retrieval, and internal governance systems. Instead of connecting clients to each one manually, the organization connects agents to MCP Fabric.

MCP Fabric provides:

- a registry of all servers and tools
- normalized capability metadata
- trust and permission levels
- routing from requested capability to best-fit tool
- curated capability packs for different agent classes
- full audit of routed calls and policy decisions

Agents stop thinking in terms of arbitrary server sprawl and instead receive a coherent capability layer.

### Who It's For

**Primary:** Platform teams and advanced agent builders managing multiple MCP servers.

**Secondary:**
- Developer experience teams building internal AI tooling platforms
- OSS builders creating reusable MCP ecosystems
- Teams standardizing how AI agents interact with internal tools and data

**Not For:**
- Users who only need one or two local tools
- Teams that do not yet have an MCP footprint

### Product Scope

**In Scope:**
- MCP server registry
- Capability normalization and cataloging
- Trust and permission layer
- Capability-based routing
- Audit logs and usage analytics
- Simple admin UI

**Out of Scope for Initial Versions:**
- Replacing MCP clients
- Rewriting third-party MCP servers
- Solving every auth model in v1
- Full enterprise directory integration

### Design Principles

- **Do not hide protocol reality unnecessarily** — transparency over magic
- **Normalize enough to help, not so much that semantics are lost** — capability modeling is a balance, not a brute-force problem
- **Make trust explicit and inspectable** — every routing decision should be explainable
- **Optimize for curated capability distribution, not raw tool count** — a small well-governed set beats a large ungoverned one

---

## Customer User Journeys

### Journey 1: Platform Engineer Registers a New MCP Server

**Persona:** Priya, platform engineer on a team managing 12 MCP servers for internal AI agents.

**Scenario:** The security team has built a new MCP server that exposes vulnerability scanning and dependency audit tools. Priya needs to add it to the platform so approved agents can use it — but not all agents should have access to vulnerability data.

**Step by Step:**

1. Priya opens the MCP Fabric admin UI and navigates to the server registry.
2. She enters the server endpoint and metadata (name, owner team, description, version).
3. Fabric inspects the server's `/tools/list` endpoint and pulls in all exposed tool definitions and schemas.
4. The admin UI shows the imported tools with auto-detected input/output schemas and a suggested trust level.
5. Priya reviews the tool list: `scan_vulnerabilities`, `list_dependencies`, `check_deprecation`.
6. She sets `scan_vulnerabilities` to "restricted" (requires explicit approval) and the others to "trusted."
7. She tags the server with labels: `security`, `production`, `read-only`.
8. Fabric maps each tool into the capability catalog — `scan_vulnerabilities` maps to `vulnerability:scan`, `list_dependencies` maps to `dependency:list`.
9. Priya saves. The server is now live in the registry and available to agents matching the trust policy.

**Outcome:** A new MCP server is registered, its tools are inspected and classified, trust levels are assigned, and capabilities are normalized — all in a single UI session. Agents can discover and use the tools without Priya touching any client configuration.

---

### Journey 2: Agent Requests a Capability Through the Fabric

**Persona:** An automated incident response agent ("Igor") operating in a production environment with access to incident management, code search, deployment, and knowledge base MCP servers.

**Scenario:** A P1 incident is triggered. Igor needs to find recent code changes that could be related, check if there's a known runbook, and assess blast radius — all through different tools.

**Step by Step:**

1. Igor receives an alert and needs capability `code:blameless-diff` to find recent changes to the failing service.
2. Igor sends a capability request to MCP Fabric: `{ capability: "code:blameless-diff", params: { service: "payment-api", since: "2h" } }`.
3. Fabric's routing engine resolves the capability against the registry. Three MCP servers advertise related capabilities:
   - Code Search server — capability `code:blameless-diff`, trust level `trusted`
   - Git History server — capability `code:diff`, trust level `trusted`
   - Docs server — capability `code:blameless-diff`, trust level `restricted` (docs-only context)
4. The policy layer checks Igor's agent class (`incident-responder`) against each server's trust policy. All three are allowed, but the Docs server is lower confidence for this use case.
5. The routing engine selects the Code Search server (best capability match + trusted + lowest latency).
6. Fabric proxies the request, returns the normalized response, and logs the routing decision.
7. Igor proceeds with the incident response. Later, Igor also fetches the runbook via capability `knowledge:runbook-get` and assesses blast radius via `dependency:impact-analysis`.

**Outcome:** Igor gets the right tool for each task without knowing which server provides it. Fabric handled discovery, policy check, routing, and audit transparently. The incident response is faster and safer than if Igor had to query each server manually.

---

### Journey 3: Platform Team Curates a Capability Bundle for New Hires

**Persona:** Alex, developer experience lead, onboarding a new engineer to the platform team.

**Scenario:** New hires need access to a focused set of tools: docs search, code search, PR status, and onboarding guides. They should not have access to deployment, vulnerability scanning, or cost analytics tools until they're ramped.

**Step by Step:**

1. Alex opens the admin UI and navigates to "Capability Packs."
2. She creates a new pack called "New Hire — Platform Engineer."
3. She browses the capability catalog and selects:
   - `knowledge:doc-search` (trusted, read-only)
   - `code:search` (trusted, read-only)
   - `code:pr-status` (trusted, read-only)
   - `onboarding:guide-get` (trusted)
4. She saves the pack and assigns it to the agent identity class `agent:new-hire`.
5. When a new hire's agent connects to Fabric, it sees only the capabilities in this pack.
6. Alex can later promote the agent to the full `agent:platform-engineer` class, which unlocks deployment and vulnerability tools.
7. Fabric provides a usage report showing which capabilities the pack is using most and where new hires request capabilities that are not in their pack (signal for expansion).

**Outcome:** Alex can onboard new engineers with a curated, safe tool surface. No manual per-server configuration. No risk of exposing powerful tools too early. Usage data helps evolve the pack over time.

---

### Journey 4: Security Admin Reviews Trust Posture and Audit Logs

**Persona:** Jordan, security engineer responsible for AI tool governance across the organization.

**Scenario:** A quarterly audit is due. Jordan needs to review which MCP servers are registered, what trust levels are assigned, whether any policy exceptions have been granted, and whether any unusual access patterns exist.

**Step by Step:**

1. Jordan opens the Fabric admin dashboard and goes to the "Trust Posture" view.
2. The dashboard shows all 15 registered servers, each with:
   - Trust level (trusted / restricted / approval-gated)
   - Owner team
   - Last health check status
   - Number of tools exposed
   - Recent policy changes
3. Jordan notices one server listed as "unreviewed" — a developer team registered it last week but no one assigned a trust level.
4. Jordan drills in, reviews the tool list, and marks it as "restricted" pending a full security review.
5. Jordan then opens the Audit Log and filters by "denied requests" over the last 30 days.
6. Several denied requests stand out: an agent tried to call `deployment:promote` from a `read-only` agent class.
7. Jordan reviews the denial reason: policy match — correct behavior. No exception needed.
8. Jordan also sees a trend: three different agents requested `database:query` in the last week, but no server offers that capability. This becomes a signal to the platform team.
9. Jordan exports the audit report as JSON for the compliance system.

**Outcome:** Jordan has full visibility into the MCP tool ecosystem. Servers without trust review are caught. Policy violations are auditable. Capability gaps are surfaced from real agent demand. The platform is governable.

---

### Journey 5: Agent Onboards and Gets Its Capability Surface

**Persona:** A new incident response agent ("Igor v2") being deployed for the first time into production.

**Scenario:** The team has built a new agent to handle deployment-health monitoring. It needs access to deployment status, service metrics, and incident tools — but not vulnerability or cost data. Before it can make any capability requests, it must connect to Fabric and get assigned an identity class.

**Step by Step:**

1. The agent starts up with a pre-shared identity token (API key or signed JWT embedded in its deployment config).
2. Agent calls Fabric's connect endpoint with its identity token and declared role: `{ intent: "deployment-health-monitor" }`.
3. Fabric validates the token against the identity store. The token maps to the pre-registered agent identity `agent:deploy-monitor`.
4. Fabric looks up the agent class `agent:deploy-monitor` and resolves its assigned capability pack.
5. Fabric returns the agent's capability surface — a curated list of capabilities it can request:
   - `deployment:status` (trusted)
   - `service:health-metrics` (trusted)
   - `incident:create` (trusted)
   - `incident:get` (trusted)
6. The agent parses its capability surface and is ready to operate within those boundaries.
7. On its first capability request — `deployment:status` — Fabric checks the agent class, confirms `trusted` policy, routes the call, and logs it.
8. On a later request for `vulnerability:scan` — Fabric denies it (not in the assigned capability pack) and logs the denial.

**Outcome:** The agent connected with zero manual server configuration. It received a capability surface scoped exactly to its role. No risky tools are accidentally exposed. The journey from deploy → connect → operate takes seconds and requires no platform engineer intervention beyond the initial agent class setup.

---

### Journey 6: Server Failure — Graceful Degradation and Transparent Fallback

**Persona:** Igor the incident response agent (from Journey 2), mid-incident at 2 AM.

**Scenario:** A production incident is in progress. Igor has been routing capability requests through Fabric for 20 minutes. The Code Search server suddenly becomes unresponsive — a network partition in the hosting cluster. Igor must not fail.

**Step by Step:**

1. Igor requests `code:blameless-diff` for the payment API to identify recent changes.
2. Fabric routes the request to the Code Search server — primary choice based on best capability match, trusted policy, and historical low latency.
3. The request times out after 5 seconds. Fabric retries once — same result.
4. Fabric marks Code Search as `degraded` in the registry, increments its failure counter, and timestamps the event.
5. Fabric checks its fallback chain for `code:blameless-diff`. The Git History server advertises `code:diff` — a partial match but sufficient for recent-change analysis.
6. Policy check: Git History is `trusted` for Igor's agent class `agent:incident-responder`.
7. Fabric routes the request to Git History. The response shape differs from Code Search (commit-level instead of line-level detail), but Fabric normalizes it to the standard `code:blameless-diff` output schema.
8. Fabric logs the full event: primary server failed, fallback server used, normalization applied, latency delta (+800ms).
9. Fabric triggers an alert: "Code Search server degraded — failover count 3 in last 5 minutes. Notify platform-oncall."
10. The platform on-call engineer receives the alert and begins investigating the Code Search outage.
11. Igor continues its incident response using Git History for code diffs. The user never sees the failure.

**Outcome:** A server failure at 2 AM didn't block the incident response. Fabric handled fallback, normalization, and alerting transparently. The platform team was notified without the agent or its user needing to know the route changed. The pathway from failure → fallback → alert → investigation is fully captured in audit.

---

### Journey 7: Approval-Gated Capability — Human-in-the-Loop Review

**Persona:** CRBot, a code review agent that suggests fixes. Priya, the platform engineer responsible for deployment gates.

**Scenario:** CRBot has completed a code review and identified a safe configuration change to fix a feature flag misconfiguration. It wants to promote the change to staging. The deployment capability is `approval-gated` for CRBot's agent class — a human must approve before Fabric routes the call.

**Step by Step:**

1. CRBot finishes its review. It determines the fix is low-risk: a feature flag toggle in staging. It requests capability `deployment:promote` with parameters `{ service: "config-api", env: "staging", change: "toggle feature flag enable-new-checkout" }`.
2. Fabric checks the policy layer. `deployment:promote` is tagged `approval-gated` for agent class `agent:code-reviewer`.
3. Fabric does not route the request. Instead, it creates a pending approval record with full context:
   - Agent: CRBot (code-reviewer)
   - Capability: deployment:promote
   - Parameters: config-api, staging, feature flag toggle
   - Server: Deployment Server v2.1
   - Timestamp
4. Fabric sends a notification to the deployment approver group: "CRBot requests deployment:promote — review in admin UI."
5. Priya receives the notification. She opens the admin UI and reviews the request. She sees it's a low-risk staging toggle from a trusted reviewer agent.
6. Priya clicks "Approve." Fabric logs the approval decision and immediately routes the request to the Deployment Server.
7. The Deployment Server executes the promote action and returns the result. Fabric normalizes the response and passes it back to CRBot with the approval trail attached.
8. If Priya had clicked "Deny," Fabric would return a standardized denial to CRBot with the reason she provided, log the denial, and close the approval record.

**Outcome:** Sensitive capabilities are gated behind human approval without blocking agent workflows entirely. The approval flow is fast, auditable, and doesn't require the agent to know the mechanism — it just waits for a response. Every approval or denial is captured for compliance.

---

### Journey 8: OSS Contributor Self-Hosts and Tests End-to-End

**Persona:** Taylor, an open-source developer who builds MCP servers and wants to try MCP Fabric.

**Scenario:** Taylor found MCP Fabric on GitHub. She has two local MCP servers running: a filesystem server and a git server. She wants to see if Fabric makes them feel like a single coherent platform. She has 10 minutes to get a first impression.

**Step by Step:**

1. Taylor clones the repo and reads the README. One command: `docker-compose up`.
2. She runs it. Docker pulls images and within 60 seconds the admin UI is at `http://localhost:8000/admin`.
3. Taylor opens the admin UI. The server registry is empty — she's the first user of this instance.
4. She clicks "Register Server" and enters her filesystem server endpoint: `http://localhost:3001`. She adds metadata: "Local FS Server," owner "taylor-dev," labels `filesystem`, `local`.
5. Fabric inspects the server, pulls its tool list (`read_file`, `write_file`, `list_directory`, `search_files`), and displays them with auto-detected schemas.
6. Taylor repeats for her git server on `http://localhost:3002`. Fabric imports `git_diff`, `git_log`, `git_status`.
7. Taylor navigates to the Capability Catalog. She maps the imported tools to capabilities: filesystem tools → `fs:read`, `fs:write`, `fs:list`, `fs:search`; git tools → `code:diff`, `code:log`, `code:status`.
8. She creates an agent class `agent:developer` and assigns both servers as `trusted`.
9. Taylor opens a terminal and sends a test request via curl: `POST /capability/request { "capability": "code:diff", "params": { "repo": ".", "since": "1h" } }`. She includes the agent identity header.
10. Fabric routes to the git server, returns the diff normalized, and logs the call. The response is clean and consistent.
11. Taylor checks the Audit Log in the admin UI — her test call is there with routing detail, latency, and server chosen.
12. Total time from clone to first successful capability request: under 8 minutes.

**Outcome:** Taylor validated the full Fabric flow — registry, capability mapping, routing, audit — entirely locally with her own MCP servers. No cloud dependencies. No configuration files to hand-edit. She's now positioned to contribute, extend, or integrate Fabric with her own ecosystem. The OSS onboarding experience is measured in single-digit minutes.

---

### Journey 9: Capability Conflict Resolution — Two Servers Claim the Same Thing

**Persona:** Priya, platform engineer (from Journey 1), managing a growing server ecosystem.

**Scenario:** The platform now has 14 MCP servers. During registration of a new code intelligence server, Fabric detects that `code:search` is now claimed by two different servers. Priya must decide which server handles which kind of search request — or whether both can coexist with routing rules.

**Step by Step:**

1. Priya finishes registering the new Code Intelligence server (v0.9). Fabric inspects its tools and maps them to capabilities automatically.
2. During capability mapping, Fabric shows a conflict banner: "Capability `code:search` is claimed by 2 servers — review routing."
3. Priya opens the conflict resolution view. A side-by-side comparison appears:

   | | Code Search (v1.2) | Code Intelligence (v0.9) |
   |---|---|---|
   | Capability | code:search | code:search |
   | Input params | query, file_pattern, max_results | query, scope, include_tests |
   | Output | lines[] | results[] with relevance ranking |
   | Latency (avg) | 400ms | 200ms |
   | Trust level | trusted | trusted |

4. Priya notes that Code Intelligence is faster and returns ranked results, but doesn't support `file_pattern` filtering. Code Search is slower but supports file-pattern-based scoping.
5. Priya sets a routing rule:
   - **Primary:** Code Intelligence for general `code:search` (faster, ranked results).
   - **Fallback/Override:** Code Search when `params.file_pattern` is present in the request.
6. She saves the routing rule. Fabric now routes `code:search` requests based on parameter presence — no agent needs to know which server handles which request.
7. Fabric logs the conflict resolution: who resolved it, when, what rules were set. This is visible to Jordan in future audits.

**Outcome:** Two servers with overlapping capabilities coexist with clear, inspectable routing logic. Priya resolved the conflict in minutes without removing either server. Agents get the best tool for each specific request without knowing the behind-the-scenes server selection. The decision is auditable.

---

### Journey 10: Server Upgrade with Schema Diff — Breaking Change Review

**Persona:** Priya managing a version upgrade of a critical MCP server.

**Scenario:** The Code Search server team ships v2.0. The `search_code` tool now requires a new `context_lines` parameter, drops `file_pattern`, and returns structured results instead of raw text lines. Priya needs to update Fabric's registry without breaking agents that expect the old schema.

**Step by Step:**

1. Priya opens the Code Search server entry in the admin UI and clicks "Re-inspect."
2. Fabric re-fetches the tool list from the server's `/tools/list` endpoint.
3. Fabric compares the new tool definitions against the stored previous version and shows a schema diff:

   ```
   search_code:
     + context_lines (required, int) — new required parameter
     - file_pattern (was optional, string) — removed
     ~ output format: lines[] → results[] {line, score, snippet}
   
   search_symbols:
     + (new tool) — no previous version
   ```

4. Fabric flags the `search_code` changes as **potentially breaking** — removed parameter, changed output schema. It warns that agents expecting the old schema may get errors.
5. Priya reviews the diff. She updates the capability mapping for `code:search` to reflect the new `context_lines` parameter in the normalized input schema. She sets the parameter as required in the catalog so agents discover the change when they query capabilities.
6. She registers the new `search_symbols` tool and maps it to capability `code:symbol-search`.
7. She activates the updated server entry. Fabric now routes `code:search` with the v2 schema.
8. Priya also toggles a deprecation banner on the previous capability mapping: "Schema changed 2026-08-15 — see updated `code:search` input contract." Agents that list capabilities before making requests will see this.
9. Jordan (the security admin from Journey 4) will see the schema change recorded in the audit log — which server changed, what changed, when, and who approved it.

**Outcome:** Server upgrades don't create silent breakage. Fabric diffs old and new schemas, flags breaking changes for human review, and lets the platform engineer activate with full context. Agents can self-discover schema changes through the capability catalog. The change is auditable.

---

### Journey 11: Server Decommission — Graceful Sunset and Migration

**Persona:** Priya, platform engineer, sunsetting a legacy MCP server that has been replaced by a newer one.

**Scenario:** The old Docs Search server (v1.0, unmaintained, deprecated in favor of Knowledge Base v2.0) needs to be removed from the platform. Three agent classes currently depend on its `knowledge:doc-search` capability. Priya cannot just delete it — she must migrate agents safely.

**Step by Step:**

1. Priya opens the Docs Search server entry in the admin UI and clicks "Decommission."
2. Fabric shows a dependency report: "This server provides capability `knowledge:doc-search` used by 3 agent classes (developer, incident-responder, new-hire) and handles ~40 requests/day."
3. Priya confirms that Knowledge Base v2.0 is already registered and provides an equivalent capability `knowledge:doc-search` with a richer schema.
4. Priya initiates a phased decommission:
   - **Phase 1 — Grace period:** Fabric keeps routing to Docs Search but attaches a deprecation header to every response. Agents can see the deprecation notice.
   - **Phase 2 — Migration:** Priya redirects `knowledge:doc-search` routing to Knowledge Base v2.0 as primary, with Docs Search as fallback for 7 days.
   - **Phase 3 — Sunset:** After 7 days, Priya confirms zero fallback events. She completes the decommission.
5. Fabric removes the server from the registry, archives its tool definitions and capability mappings, and logs the full timeline.
6. The server no longer appears in agent capability surfaces. Any agent that still tries to reference it gets a standardized "capability migrated" response pointing to Knowledge Base v2.0.
7. Jordan can see the full decommission trail in the audit log: who initiated it, what phases occurred, what timelines were followed.

**Outcome:** A server was removed without breaking any agent. Fabric provided visibility into dependencies, a phased migration path, and full audit traceability. Agents were redirected transparently. The platform shrunk without any outages.

---

### Journey 12: Capability Deprecation — Retiring a Capability Without Surprise

**Persona:** Alex, DevEx lead (from Journey 3), who defined the `onboarding:guide-get` capability used in the new-hire pack.

**Scenario:** The onboarding process has changed. New hires now use an interactive onboarding agent that doesn't need `onboarding:guide-get` — the capability has zero usage over the last 30 days. Alex wants to retire it cleanly from the catalog.

**Step by Step:**

1. Alex opens the Capability Catalog and navigates to `onboarding:guide-get`. The detail view shows: last used 38 days ago, 0 agents currently assigned, 1 pack includes it (New Hire — Platform Engineer).
2. Alex clicks "Deprecate." Fabric warns: "This capability is included in 1 capability pack. Deprecation will remove it from the pack."
3. Alex confirms. Fabric marks `onboarding:guide-get` as `deprecated` with a deprecation date.
4. Fabric removes it from the "New Hire" capability pack automatically.
5. For the next 14 days (configurable grace period), any agent that explicitly requests `onboarding:guide-get` receives a deprecation response: `{ status: "deprecated", message: "onboarding:guide-get has been retired. Use the interactive onboarding agent instead.", retired_on: "2026-09-01" }`.
6. After the grace period, the capability is fully removed from the catalog. Requests return a standard `capability_not_found` error.
7. Alex can see the deprecation lifecycle in the audit log: who deprecated it, when, what grace period was set, whether any agents made deprecated requests during the grace window.

**Outcome:** Capabilities don't vanish without warning. Agents get a grace period with a clear migration path. Pack maintainers are notified automatically. The deprecation lifecycle is fully auditable.

---

### Journey 13: Agent Error Handling — Malformed Requests and Fabric Errors

**Persona:** Igor the incident response agent (from Journeys 2 and 6), encountering errors from Fabric itself.

**Scenario:** Igor makes a series of capability requests during an incident. One request has a malformed parameter, one capability doesn't exist, and Fabric itself experiences a brief internal error. Igor must stay operational through all of these.

**Step by Step:**

1. Igor requests `code:blameless-diff` with a malformed parameter: `{ "service": "payment-api", "since": "not-a-timestamp" }`.
2. Fabric validates the input against the normalized schema for `code:blameless-diff`. The `since` parameter expects an ISO 8601 timestamp or relative duration.
3. Fabric returns a `400 Bad Request` with a structured error: `{ "error": "invalid_parameter", "parameter": "since", "expected": "ISO 8601 timestamp or relative duration (e.g., '2h')", "received": "not-a-timestamp" }`.
4. Igor corrects its parameter and retries. Fabric routes and returns the result successfully.
5. Later, Igor requests capability `vulnerability:deep-scan` — a capability that does not exist in the catalog.
6. Fabric returns `404 Not Found`: `{ "error": "capability_not_found", "capability": "vulnerability:deep-scan", "suggestion": "Did you mean 'vulnerability:scan'?" }`.
7. Igor switches to `vulnerability:scan` and gets the result.
8. During a subsequent request, Fabric's PostgreSQL connection pool briefly exhausts. The routing engine cannot resolve capabilities.
9. Fabric returns `503 Service Unavailable`: `{ "error": "fabric_degraded", "message": "Fabric is temporarily unavailable. Retry in 5 seconds.", "retry_after": 5 }`.
10. Igor waits 5 seconds, retries, and the request succeeds. Fabric logs the degradation event internally for investigation.

**Outcome:** Every error from Fabric is structured, actionable, and includes enough context for agents to self-correct (invalid params → fix and retry, missing capability → suggestion, fabric down → retry-after). Agents never receive raw stack traces or opaque failures. Error handling is a first-class surface, not an afterthought.

---

### Journey 14: Anti-Journey — When NOT to Use MCP Fabric

**Persona:** Dev, a solo developer building a single AI coding assistant that uses two MCP servers: filesystem and git.

**Scenario:** Dev heard about MCP Fabric from a colleague and wonders if they should add it to their setup. They have 2 tools, 1 agent, and no governance requirements. Fabric would add overhead without solving a real problem for them.

**Step by Step:**

1. Dev reads the MCP Fabric README and sees: "Not for users who only need one or two local tools."
2. Dev pauses and evaluates their setup:
   - 2 MCP servers (filesystem, git)
   - 1 agent (coding assistant)
   - No team, no platform governance needs
   - No trust boundaries — Dev fully trusts both servers
3. Dev asks: "What would Fabric add for me?"
   - **Registry?** Dev already knows both servers by heart. No discovery problem.
   - **Capability catalog?** Two tools with obvious names (`read_file`, `git_diff`). No naming drift.
   - **Policy layer?** One agent, fully trusted. No policy decisions to make.
   - **Routing?** Each tool maps to one server. No ambiguity.
   - **Audit?** Dev doesn't need governance reports.
4. Dev decides: Fabric is the wrong tool for this setup. It adds a routing hop, configuration overhead, and a dependency stack (PostgreSQL, Redis) for zero benefit.
5. Dev's setup stays simple: agent → direct MCP connections. Total configuration: 2 server endpoints. Zero Fabric infrastructure.
6. Dev notes: "If my setup grows to 5+ servers or I add team members, I'll revisit Fabric."
7. The Fabric project gains a clear signal: here's where Fabric adds value, and here's where it doesn't.

**Outcome:** The anti-journey defines Fabric's boundaries as clearly as the happy-path journeys. Fabric is for teams with tool sprawl, governance needs, and multiple agent classes. It is not for solo developers with 1-3 tools. Both the project and the potential user win by knowing this upfront.

---

### Journey 15: Incremental Migration — Adopting Fabric Server by Server

**Persona:** Marcus, platform lead at a 40-person engineering org with 8 MCP servers connected directly to agents. No governance, no audit, no trust controls — just raw connections.

**Scenario:** Marcus wants to adopt MCP Fabric, but he cannot do a big-bang cutover. Eight servers power daily workflows for three agent classes. Any downtime or misconfiguration blocks engineers. He needs to migrate one server at a time, validate at each step, and keep some servers on direct connections until trust reviews are complete.

**Step by Step:**

1. Marcus deploys MCP Fabric in parallel with the existing setup. Fabric runs alongside the direct connections — agents can use either path during migration.
2. Marcus picks the lowest-risk server first: Docs Search (read-only, no write operations, lowest blast radius).
3. He registers Docs Search in Fabric, maps its tools to capabilities, assigns `trusted` to the developer agent class, and verifies the routing works.
4. He configures the developer agent class to route `knowledge:doc-search` through Fabric while keeping all other capabilities on direct connections. This is **dual-mode** — Fabric for one capability, direct for the rest.
5. For one week, Fabric routes doc-search requests. Marcus monitors audit logs for errors, latency regressions, or routing anomalies. None appear.
6. Marcus repeats for two more read-only servers: Git History and Code Search. Each server is registered, mapped, and added to the developer agent class. Each goes through a 3-day validation window.
7. After three read-only servers are fully migrated through Fabric, Marcus tackles the first write-enabled server: Deployment (approval-gated for non-admin agent classes). He registers it, sets `approval-gated` policy for the developer class, and verifies the approval flow works end-to-end.
8. After 4 weeks, six of eight servers are routed through Fabric. The remaining two (internal tooling servers with complex auth) stay on direct connections with a plan to migrate in the next quarter.
9. Marcus configures Fabric's audit pipeline to capture all routed calls across the migrated servers. For the first time, the platform team has visibility into agent tool usage.
10. The migration is tracked in Fabric's own audit log: which servers were migrated, when, who approved, what validation windows passed.

**Outcome:** Fabric was adopted incrementally — no big-bang cutover, no downtime, no broken agent workflows. Migration started with low-risk read-only servers and progressed to write-enabled servers with approval gates. The platform team gained governance incrementally rather than all at once. Unmigrated servers remain on direct connections with a clear plan.

---

### Journey 16: First-Time Deployment — Greenfield Fabric from Zero

**Persona:** Marcus, platform lead who has never used MCP Fabric before. No servers registered. No agents configured. A blank slate.

**Scenario:** Marcus has heard about MCP Fabric and wants to evaluate it for his team. He deploys it locally, registers his first MCP server, creates his first agent class, and makes his first capability request — all from scratch.

**Step by Step:**

1. Marcus clones the repo and runs `docker-compose up`. Within 60 seconds, the Fabric API and admin UI are running.
2. Marcus opens `http://localhost:8000/admin`. He sees an empty dashboard with a prompt: "Register your first MCP server to get started."
3. He clicks "Register Server" and enters his team's knowledge base MCP server endpoint. He adds metadata: "KB Server," owner "platform-team," labels `knowledge`, `internal`.
4. Fabric inspects the server, imports 4 tools (`search_kb`, `get_article`, `list_categories`, `ask_question`), and displays them in the admin UI.
5. Marcus navigates to the Capability Catalog. The imported tools are listed as unmapped. He maps each tool to a capability: `knowledge:search`, `knowledge:article-get`, `knowledge:categories`, `knowledge:qa`.
6. Marcus navigates to "Agent Classes" and creates his first class: `agent:developer`. He assigns the KB Server as `trusted` for this class.
7. Marcus opens a terminal and sends his first Fabric request: `curl -H "Authorization: Bearer <agent-token>" -d '{"capability": "knowledge:search", "params": {"query": "deployment runbook"}}' http://localhost:8000/capability/request`.
8. Fabric resolves the `knowledge:search` capability to the KB Server, checks policy (trusted for developer class), routes the request, normalizes the response, logs the call, and returns the result.
9. Marcus checks the Audit Log — his request is there with full routing detail. He checks the Trust Posture view — one server, reviewed, trusted.
10. Total time from `docker-compose up` to first successful capability request: under 10 minutes.

**Outcome:** Fabric went from zero to operational in a single session. Marcus registered a server, defined capabilities, created an agent class, made a request, and verified the audit trail — all without reading documentation beyond the README. The greenfield experience is measured in minutes.

---

### Journey 17: Human Developer Debugs Agent Tool Selection

**Persona:** Ravi, a backend engineer whose coding assistant agent keeps getting wrong results from code search. He doesn't administer Fabric — he just wants to understand why his agent is failing.

**Scenario:** Ravi's agent has been returning irrelevant code search results all morning. He suspects the agent is hitting the wrong MCP server but has no visibility. He opens Fabric's audit log (to which he has read-only access) to trace the routing decisions.

**Step by Step:**

1. Ravi opens the Fabric admin UI. He has a `viewer` role — he can browse audit logs, capability catalog, and server inventory, but cannot modify anything.
2. He navigates to the Audit Log and filters by his agent ID and capability `code:search` for the last 2 hours.
3. He sees his agent's last 12 `code:search` requests. All 12 routed to the "Git History" server, not "Code Intelligence."
4. He clicks into one routing decision to see the detail: "Selected Git History — capability match: partial (code:diff → routed as code:search fallback). Code Intelligence was not selected — server was degraded (unhealthy at request time)."
5. Ravi realizes Code Intelligence was down during his morning session. Fabric fell back to Git History, which returns commit-level search instead of line-level search — hence the irrelevant results.
6. Ravi can't fix the server, but he now understands the behavior. He checks server health — Code Intelligence is back online.
7. He retries the same capability request via his agent. Fabric now routes to Code Intelligence (healthy, best match). Results are relevant.
8. Ravi leaves a comment on the routing decision for the platform team: "Git History fallback for code:search returns commit-level results, not useful for line-level code search. Consider adjusting the fallback chain or adding a quality weight."

**Outcome:** A non-admin developer traced their agent's behavior through Fabric with read-only access. They identified a server degradation, understood the fallback behavior, and provided actionable feedback to the platform team — all without filing a ticket or waiting for an admin to investigate.

---

### Journey 18: Compliance Export — SOC2 Audit Evidence

**Persona:** Jordan, security engineer (from Journey 4), preparing for a SOC2 Type II audit.

**Scenario:** The auditors need evidence that all AI agent tool access is logged, policy-enforced, and reviewable. They want: all capability requests for Q3 2026, filtered to production agent classes, with approval trails for any gated capabilities, in a structured format.

**Step by Step:**

1. Jordan opens the Fabric admin UI and navigates to "Audit Export."
2. She configures the export:
   - Date range: 2026-07-01 to 2026-09-30
   - Agent classes: `incident-responder`, `deploy-monitor`, `code-reviewer` (production only, excludes `developer` and `new-hire`)
   - Event types: capability requests, denials, approvals, policy changes
   - Format: JSON (machine-readable for the auditor's tooling) + CSV summary (for human review)
3. Fabric generates the export. The JSON file contains every request with: timestamp, agent ID, agent class, capability, parameters (sanitized), server selected, policy evaluation result, routing decision reason, latency, outcome.
4. Jordan reviews the CSV summary before sending:
   - Total requests: 14,203
   - Denials: 47 (all policy-correct — no unauthorized access)
   - Approval-gated requests: 32 (all approved by authorized approvers, all within policy)
   - Failed/fallback: 12 (all server degradations, all resolved via fallback)
5. Jordan generates an attestation report: "All agent capability access during Q3 2026 was routed through MCP Fabric. Policy enforcement covered 100% of requests. No unauthorized access detected. 47 denials matched expected policy. 32 gated requests were approved with auditable trails."
6. She exports the attestation alongside the structured data and sends both to the auditors.
7. Jordan configures a recurring quarterly export job in Fabric so this is automated next quarter.

**Outcome:** A SOC2 audit request was fulfilled in minutes with structured, queryable evidence. Every request, denial, approval, and policy decision was traceable. No manual log scraping or spreadsheet assembly was required.

---

### Journey 19: Policy Sandbox — Testing Before Production Rollout

**Persona:** Priya, platform engineer, preparing to change the trust level of the Deployment Server from `trusted` to `approval-gated` for the developer agent class.

**Scenario:** The platform team wants to tighten deployment controls — developers should not be able to promote to production without human approval. But Priya is nervous: what if the new policy accidentally blocks a legitimate deployment workflow? She wants to test the policy in a sandbox before applying it to production agents.

**Step by Step:**

1. Priya navigates to the Policy Editor and creates a new policy rule: "Deployment Server → approval-gated for agent class developer."
2. Instead of activating it immediately, she clicks "Test in Sandbox."
3. Fabric creates a sandbox environment — a parallel policy evaluation path that runs against real requests but does not affect routing.
4. For the next 48 hours, every `deployment:promote` request from a developer agent is evaluated against BOTH the active policy (trusted — routes normally) AND the sandbox policy (approval-gated — would have held the request).
5. Priya monitors the sandbox results in a side-by-side view:
   - 12 requests were evaluated
   - Under the sandbox policy, 9 would have been held for approval, 3 would have been denied (parameters outside allowed scope)
   - 0 requests would have been incorrectly blocked (no false positives)
6. Priya reviews the 3 denied requests — all were deployments to production with parameters the new policy correctly restricts. The policy is working as intended.
7. She also checks: 1 request was a deployment to staging — under the sandbox policy it would have been approval-gated, not denied. Correct — staging deployments should require approval but not be blocked entirely.
8. Confident after 48 hours of shadow evaluation, Priya activates the policy. Fabric applies it to all future requests immediately.
9. The sandbox results are archived in the audit log as evidence of pre-production testing.

**Outcome:** A policy change was tested against real traffic for 48 hours before activation. Priya had full visibility into what would have changed — what would have been approved-gated, what would have been denied, and whether any false positives occurred. Production agents were never affected during testing.

---

### Journey 20: Multi-Team Ownership — Namespace Separation

**Persona:** Priya (platform team) and Sara (security team lead), each managing their own servers with different trust models. Marcus (platform lead) overseeing the shared Fabric instance.

**Scenario:** The platform team owns 8 MCP servers (code, docs, deployment, CI/CD). The security team owns 3 (vulnerability scanning, dependency audit, secret detection). Security servers have stricter trust requirements — only security-auditor agents should access vulnerability data. Platform servers are more open. Both teams share one Fabric instance.

**Step by Step:**

1. Marcus configures Fabric with team namespaces: `team:platform` and `team:security`.
2. Priya registers the platform team's 8 servers. Each is tagged `team:platform`. She sets trust levels appropriate for developer and incident-responder agent classes.
3. Sara registers the security team's 3 servers. Each is tagged `team:security`. She sets `vulnerability:scan` and `secret:detect` as `restricted` — only accessible to agent class `agent:security-auditor`.
4. Priya cannot see or modify Sara's server trust levels (her admin role is scoped to `team:platform`). Sara cannot modify Priya's servers.
5. Sara creates the `agent:security-auditor` class with access to all security servers and read-only access to select platform servers (code search, incident data — for context during audits).
6. Marcus, as platform lead, has cross-team visibility. He can see all 11 servers, all agent classes, and all policies. He can override if needed but prefers team-level ownership.
7. During a quarterly review (Journey 18), Jordan exports audit data. The export includes team-level attribution: which team's servers handled which requests, which team's agents made which requests.
8. A new server registration by the data team triggers a cross-team review flow: the data team's server exposes `database:query`. Sara flags it for review because it overlaps with security audit capabilities. Priya and Sara resolve the conflict together (similar to Journey 9).

**Outcome:** Two teams coexist on one Fabric instance with separate namespaces, trust models, and admin scopes. Each team owns its servers and policies. The platform lead has cross-team visibility. Audit trails include team attribution. Cross-team capability conflicts are resolved collaboratively.

---

### Journey 21: Agent Developer Integrates Fabric API

**Persona:** Dana, an agent developer building a new deployment-health monitoring agent. She needs to integrate her agent with Fabric's capability request API.

**Scenario:** Dana has built agent logic before — but always against direct MCP server connections. This is her first time routing through Fabric. She needs to understand the API contract, handle responses, and manage errors.

**Step by Step:**

1. Dana reads the Fabric API documentation (or the OpenAPI spec). She learns the key endpoints:
   - `POST /auth/connect` — agent authenticates and receives its capability surface
   - `GET /capabilities` — list all capabilities available to this agent
   - `POST /capability/request` — make a capability request
   - `GET /capability/status/{request_id}` — check status of an approval-gated request
2. Dana generates an agent identity token from the admin UI (or receives one from Priya). She stores it in her agent's config.
3. In her agent's startup code, she calls `POST /auth/connect` with the token. Fabric returns:
   ```json
   {
     "agent_id": "deploy-monitor-01",
     "agent_class": "agent:deploy-monitor",
     "capability_surface": [
       "deployment:status",
       "service:health-metrics",
       "incident:create",
       "incident:get"
     ]
   }
   ```
4. Dana's agent stores the capability surface and uses it to validate its own requests before sending them.
5. She writes the capability request function: `POST /capability/request` with `{ "capability": "...", "params": {...} }`. She handles three response types:
   - `200` — success, use the normalized response
   - `202` — approval-gated, poll `/capability/status/{id}` for resolution
   - `4xx/5xx` — error, handle per Journey 13's error contract
6. She tests her integration with Fabric running locally (via docker-compose). She registers a mock deployment server, maps its tools, creates her agent class, and validates the full flow.
7. Her agent is production-ready within a day. The integration code is ~50 lines — most of the complexity is in Fabric, not in her agent.

**Outcome:** An agent developer integrated Fabric with a well-defined API contract in under a day. The agent's integration code is thin — authentication, capability discovery, request/response handling. All governance, routing, and policy complexity lives in Fabric.

---

### Journey 22: Agent Discovers Capabilities at Startup

**Persona:** Igor the incident response agent (from Journeys 2 and 6), starting up after a restart.

**Scenario:** Igor was restarted during a deployment. On startup, it needs to know what capabilities are available to it before making any requests. Capabilities may have changed since its last run — servers were added or removed, policies were updated. Igor should not cache stale capability data.

**Step by Step:**

1. Igor starts up and calls `POST /auth/connect` with its identity token.
2. Fabric returns Igor's capability surface: 12 capabilities across 5 servers, all `trusted` or `trusted (approval-gated)`.
3. Igor calls `GET /capabilities` to get full details on each capability: input schema, output schema, trust level, whether approval is required, deprecation status.
4. Igor discovers that `code:blameless-diff` has a new required parameter `context_lines` (from Journey 10's schema change). Igor updates its internal capability model to include this parameter.
5. Igor also discovers that `onboarding:guide-get` is now deprecated (from Journey 12). Igor logs a warning: "Capability onboarding:guide-get is deprecated — use interactive onboarding agent instead."
6. Igor's startup completes. It has a fresh, validated capability surface with full schema details. No stale caches.
7. Igor registers for capability change notifications (webhook or polling). If a capability is added, removed, deprecated, or schema-changed, Igor will receive a notification and can refresh its surface without restarting.

**Outcome:** Igor discovered its exact capability surface at startup, with full schemas, deprecation notices, and trust levels. It adapted to a schema change automatically. No restart needed to pick up new capabilities — change notifications keep it current.

---

### Journey 23: Agent Batches Multiple Capability Requests

**Persona:** Igor, mid-incident, needing three pieces of information simultaneously.

**Scenario:** A P1 incident is active. Igor needs to: (1) find recent code changes to the failing service, (2) check the runbook for known mitigation steps, and (3) assess blast radius by identifying dependent services. These three requests are independent — Igor should not make them sequentially, waiting for each to complete before starting the next.

**Step by Step:**

1. Igor constructs a batch request to Fabric: `POST /capability/batch` with three capability requests in a single payload:
   ```json
   {
     "requests": [
       { "id": "req-1", "capability": "code:blameless-diff", "params": { "service": "payment-api", "since": "2h" } },
       { "id": "req-2", "capability": "knowledge:runbook-get", "params": { "service": "payment-api" } },
       { "id": "req-3", "capability": "dependency:impact-analysis", "params": { "service": "payment-api" } }
     ]
   }
   ```
2. Fabric evaluates all three requests independently and in parallel. Each goes through the standard pipeline: policy check → routing → server call → normalization.
3. Request 1 routes to Code Search (primary, healthy). Request 2 routes to Knowledge Base. Request 3 routes to Dependency Mapper.
4. After all three complete (or timeout), Fabric returns a batch response:
   ```json
   {
     "results": [
       { "id": "req-1", "status": "success", "data": {...}, "server": "code-search", "latency_ms": 320 },
       { "id": "req-2", "status": "success", "data": {...}, "server": "kb-server", "latency_ms": 180 },
       { "id": "req-3", "status": "error", "error": "server_degraded", "fallback_used": false, "message": "Dependency Mapper timed out — retry in 5s" }
     ]
   }
   ```
5. Igor gets two successful results and one failure with a clear retry instruction. Total round-trip time: ~350ms (max of the three parallel requests) instead of ~850ms (sequential). During an incident, 500ms matters.

**Outcome:** Igor made three independent capability requests in a single round-trip. Fabric evaluated them in parallel, each through its own policy/routing/server path. The batch response gave Igor everything it needed — successes and failures — in one structured payload. Incident response latency improved by >50%.

---

### Journey 24: Fabric Disaster Recovery — Backup and State Restoration

**Persona:** Marcus, platform lead, responding to a corrupted PostgreSQL volume at 3 AM.

**Scenario:** The PostgreSQL instance backing Fabric has suffered a volume corruption. The registry, capability catalog, policy rules, and audit logs are potentially lost. Marcus needs to restore Fabric's state from backup and bring the platform back online without re-registering all 15 servers and re-creating all policies from memory.

**Step by Step:**

1. Marcus receives an alert: Fabric API is returning 500s — PostgreSQL connection failures.
2. He investigates and confirms volume corruption. The Fabric API cannot read or write state.
3. Marcus provisions a fresh PostgreSQL instance. He configures Fabric to connect to it.
4. He runs Fabric's restore command: `fabric-admin restore --backup latest --target postgres://new-instance/mcp_fabric`.
5. Fabric restores from the most recent backup (taken automatically every 6 hours, with transaction log streaming for point-in-time recovery):
   - Server registry: all 15 servers restored with metadata, tool definitions, and trust levels
   - Capability catalog: all mappings and normalized schemas restored
   - Policy rules: all trust levels, agent classes, and routing rules restored
   - Capability packs: all 4 packs restored with their capability assignments
   - Audit log: restored up to the last committed transaction before the corruption
   - Alert history and approval records: restored
6. Fabric validates the restored state: it health-checks all 15 registered servers, confirms capability mappings resolve, and verifies agent identity tokens are valid.
7. Total downtime: 22 minutes. Data loss: ~30 seconds of audit events (transactions committed after the last backup and before corruption).
8. Fabric triggers a post-restore alert: "State restored from backup at 03:22 UTC. 15 servers validated. 4 capability packs restored. Audit gap: 30 seconds."
9. Marcus documents the incident and schedules a review of backup frequency (currently every 6 hours — may reduce to hourly for production).

**Outcome:** Fabric's state was fully restored from backup in under 30 minutes. All configuration (servers, capabilities, policies, packs) was recovered — no manual re-registration. Audit log was recovered with minimal data loss. The platform team didn't spend the night re-creating policies from memory.

---

### Journey 25: Fabric Version Upgrade — Zero-Downtime Rollout

**Persona:** Marcus, upgrading Fabric from v0.1.0 to v0.2.0 with new features (capability packs, conflict detection, richer trust review).

**Scenario:** Fabric v0.2.0 ships with database schema migrations, new API endpoints, and updated UI. Marcus needs to upgrade the production Fabric instance without blocking agent capability requests. Agents should not notice the upgrade.

**Step by Step:**

1. Marcus reads the v0.2.0 release notes. The upgrade includes:
   - Database migration: new `capability_packs` table, new `conflict_resolution` table, new columns in `policies`
   - New API endpoints: `POST /capability/batch`, `POST /policy/sandbox`
   - Updated admin UI with bundle curator and conflict resolution views
   - Backward-compatible API — all v0.1.0 endpoints unchanged
2. Marcus runs a pre-upgrade dry run in staging: `fabric-admin upgrade --check v0.2.0`. It reports: "3 migrations pending. 0 breaking changes. Estimated migration time: 12 seconds."
3. Marcus deploys Fabric v0.2.0 using a blue-green strategy:
   - Two Fabric API instances are running behind a load balancer
   - He takes Instance B out of rotation, upgrades it, runs migrations, and validates
   - Instance B is healthy: v0.2.0, migrations applied, API responds correctly
   - He puts Instance B back in rotation, takes Instance A out, upgrades Instance A
   - Both instances are now v0.2.0
4. During the upgrade, agents were routed to the healthy instance. Zero capability requests were dropped. Latency increased by ~50ms during the brief single-instance window — within normal variance.
5. Marcus verifies: new API endpoints are live (`/capability/batch` returns 200), admin UI shows the new bundle curator view, existing endpoints behave identically.
6. He checks the audit log: agent activity was uninterrupted. No routing anomalies during the upgrade window.
7. Marcus sends a release announcement to the platform team: "Fabric v0.2.0 is live — capability packs, batch requests, conflict detection, and policy sandbox are now available."

**Outcome:** Fabric was upgraded from v0.1.0 to v0.2.0 with zero downtime and zero dropped requests. Agents never noticed. The platform team gained new features without any disruption to existing workflows.

---

### Journey 26: Admin User Management and Role-Based Access

**Persona:** Marcus, onboarding Priya as a new platform engineer and Ravi as a read-only viewer.

**Scenario:** The Fabric admin UI is currently open to anyone with the URL. Marcus needs to add authentication and role-based access: admins (full control), editors (manage servers and policies within their team), and viewers (read-only access to audit logs and catalog). He also needs to revoke access when someone leaves.

**Step by Step:**

1. Marcus navigates to "Admin Users" in the Fabric settings. Currently, there is one user: Marcus (role: `admin`).
2. He clicks "Invite User" and enters Priya's email. He assigns her role `editor` scoped to `team:platform`. She will be able to manage platform servers, policies, and capability packs — but not security team servers and not admin settings.
3. Priya receives an invite email with a one-time setup link. She sets her password and enables MFA (optional, configurable by admin policy).
4. Marcus invites Ravi with role `viewer` — no team scope (can view all servers and audit logs but cannot modify anything). Ravi sets up his account.
5. Marcus configures the default session timeout: 8 hours for admins, 24 hours for viewers. Failed login attempts lock the account for 15 minutes after 5 failures.
6. Three months later, a platform engineer leaves the team. Marcus navigates to their user entry and clicks "Deactivate." The account is immediately disabled. Any active sessions are revoked.
7. Fabric logs all admin user events: invitations, role changes, password resets, deactivations, and failed login attempts. These are visible in a separate "Admin Audit" view accessible only to the `admin` role.

**Outcome:** Fabric admin access is role-based with team-level scoping. Admins have full control. Editors manage their team's servers and policies. Viewers get read-only visibility into audit logs and catalog. User lifecycle (invite → activate → deactivate) is managed within Fabric with full audit trails.

---

### Journey 27: Capability Taxonomy Design — Building the Namespace

**Persona:** Priya, platform engineer, designing the initial capability taxonomy for the organization's first 6 MCP servers.

**Scenario:** Six servers are registered in Fabric with 30+ tools across them. Raw tool names are inconsistent: `search_code`, `findInRepo`, `code_lookup` all mean similar things. Priya needs to design a capability namespace that normalizes these tools into a coherent, queryable model that agents and humans both understand.

**Step by Step:**

1. Priya opens the Capability Catalog. All 30+ tools are listed as unmapped. Fabric suggests auto-mappings based on tool name similarity, input/output schema analysis, and common capability patterns — but Priya wants to design the taxonomy intentionally.
2. She starts with a namespace convention: `domain:action`. Domains are broad categories of what agents do in this organization:
   - `code:` — source code operations
   - `knowledge:` — documentation and knowledge base
   - `deployment:` — deployment and release operations
   - `incident:` — incident management
   - `dependency:` — service dependency analysis
   - `security:` — vulnerability and compliance
3. She maps the first batch of tools:
   - `search_code` (Code Search), `findInRepo` (Code Intelligence), `code_lookup` (Git History) → all map to `code:search`
   - `get_blameless_diff` → `code:blameless-diff`
   - `list_dependencies` → `dependency:list`
4. Fabric detects that three tools map to `code:search` and flags a capability conflict (triggers Journey 9 later).
5. Priya defines the normalized input/output schema for each capability. For `code:search`:
   - Input: `query` (required, string), `file_pattern` (optional, string), `max_results` (optional, int, default 20)
   - Output: `results[]` with `file`, `line`, `snippet`, `score`
6. She documents the taxonomy in a shared wiki, linked from the Capability Catalog: "When adding a new server, map new tools to existing capabilities where possible. Propose new capabilities in the #platform-fabric Slack channel before creating them."
7. Three months later, a new server introduces a tool `symbol_search`. Priya decides it's distinct enough from `code:search` to warrant a new capability: `code:symbol-search`. She follows the naming convention and documents it.
8. A developer proposes a capability `repo:find` — but Priya notes that `repo` is not a domain in the current taxonomy. She maps it to `code:search` and adds `repo` as an alias so agents using that term still find the right capability.

**Outcome:** A coherent capability taxonomy was designed intentionally, not auto-generated. The namespace convention (`domain:action`) scales. New capabilities follow the convention. Aliases handle terminology drift across teams. The taxonomy is documented and governed — not a free-for-all.

---

### Journey 28: Telemetry and Observability — Monitoring Fabric Itself

**Persona:** Marcus, platform lead, setting up observability for the Fabric instance to ensure it's healthy and performant.

**Scenario:** Fabric is now routing ~5,000 capability requests per day across 15 servers. Marcus needs to monitor Fabric itself: request volume, latency distribution, error rates, server health trends, and routing accuracy. He also wants to be alerted before users notice problems.

**Step by Step:**

1. Fabric exposes Prometheus metrics at `/metrics` and OpenTelemetry traces. Marcus configures Prometheus to scrape Fabric and Grafana to visualize the data.
2. He builds a Fabric health dashboard with:
   - **Request volume:** requests/minute, by capability, by agent class, by server
   - **Latency:** p50/p95/p99 latency for routing decisions + server calls, by capability
   - **Error rates:** 4xx/5xx rates, fallback events, server health degradation events
   - **Routing accuracy:** percentage of requests routed to primary vs fallback server
   - **Policy decisions:** approvals, denials, approval-gated requests pending
   - **Catalog health:** unmapped tools, unresolved conflicts, unreviewed servers
3. Marcus sets up alerts in Prometheus Alertmanager:
   - Routing latency p95 > 500ms for 5 minutes → notify platform-oncall
   - Server health degradation > 3 servers simultaneously → notify platform-oncall
   - Denial rate spike > 10% of requests for any agent class → notify security-oncall
   - Unreviewed server count > 0 for > 48 hours → notify platform-lead
   - Fabric API error rate > 1% for 5 minutes → notify platform-oncall
4. During an incident (Journey 6), Fabric's telemetry surfaces the issue: Code Search latency spikes to 2s, Fabric starts falling back to Git History, the fallback count trends upward. Marcus sees the degradation in Grafana before the alert fires.
5. Marcus uses OpenTelemetry traces to debug a specific slow request: the trace shows the capability resolution took 12ms, policy check took 3ms, and the server call took 1,800ms — the bottleneck is the MCP server, not Fabric.
6. Monthly, Marcus reviews the telemetry trends: routing accuracy is 94% (above the 90% target), p95 routing latency is 280ms (well within bounds), and 3 new servers were registered last month (growth signal).

**Outcome:** Fabric itself is observable. Marcus can see request volume, latency, errors, and routing decisions in real time. Alerts fire before users notice problems. Traces pinpoint whether slowness is in Fabric or in the target MCP servers. The platform team operates Fabric with the same observability standards they expect from the services they manage.

---

### Journey 29: Authentication — Agent Identity and Admin Access

**Persona:** Marcus, configuring Fabric's authentication model for agents and admin UI users.

**Scenario:** Fabric is moving from local development to team use. Marcus needs to lock down access: agents must prove their identity before making capability requests, and admin UI users must authenticate with credentials. Unauthenticated access should be impossible.

**Step by Step:**

1. Marcus configures Fabric's authentication settings:
   - **Agent auth:** API key or JWT bearer tokens. Tokens are issued per agent identity, bound to an agent class, and can be rotated or revoked.
   - **Admin UI auth:** Username/password with optional MFA (TOTP or WebAuthn). OAuth2 (Google, GitHub) as an optional alternative.
2. Marcus creates the first agent identity token for Igor (incident-responder):
   - Navigates to "Agent Identities" → "Create Token"
   - Assigns token to agent class `agent:incident-responder`
   - Sets expiration: 90 days (auto-renewable)
   - Sets rate limit: 100 requests/minute
   - Labels: `production`, `incident-response`
   - Fabric generates a signed JWT. Marcus stores it in Igor's deployment config.
3. Igor's startup code (from Journey 22) includes the token in the `Authorization: Bearer <token>` header. Fabric validates the token on every request:
   - Token is not expired
   - Token is not revoked
   - Token's agent class matches the claimed identity
   - Rate limit is not exceeded
4. Marcus configures token rotation: 7 days before expiry, Fabric sends a notification to the token owner. Marcus can rotate the token — Fabric issues a new JWT and sets a 24-hour grace period where both old and new tokens are valid (so Igor can pick up the new token without a hard cutover).
5. If Igor's token is compromised (detected via unusual request patterns or reported by security), Marcus revokes it immediately. All requests with that token are rejected with `401 Unauthorized`. Fabric logs the revocation with a timestamp and reason.
6. For admin UI access, Priya logs in with her username/password + TOTP code. Her session is valid for 8 hours. Fabric logs the login event with IP address and user agent.
7. Marcus configures an IP allow-list for admin UI access: only connections from the corporate VPN IP range are accepted. Agent API access is unrestricted (agents may run from various environments).

**Outcome:** Fabric's authentication model covers both agents (API key / JWT with rotation, revocation, rate limits) and admin users (password + MFA + OAuth). Unauthenticated access returns `401`. Token lifecycle is managed within Fabric. Compromised tokens can be revoked immediately. All auth events are logged.

---

## Feature Catalog

### 1. Registry

The single source of truth for every MCP server connected to the fabric.

| Feature | Description |
|---|---|
| Server registration | Add, update, remove MCP server endpoints with metadata |
| Auto-inspection | On registration, fetch `/tools/list` and import all tool definitions |
| Metadata store | Name, owner, version, description, labels, trust level, health status |
| Health checks | Periodic pings to registered servers (optional, configurable interval) |
| Status dashboard | See all servers, their tool counts, health, and last-updated |

### 2. Capability Catalog

Normalizes raw MCP tool definitions into a queryable, consistent capability model.

| Feature | Description |
|---|---|
| Tool ingestion | Parse tool definitions from registered MCP servers |
| Capability mapping | Map raw tools to normalized capability terms (e.g., `code:search`, `incident:get`) |
| Schema normalization | Store unified input/output schemas with original schemas preserved |
| Conflict detection | Flag tools from different servers that map to the same capability for review |
| Search and browse | Query the catalog by capability name, tool name, server, or label |

### 3. Routing Engine

Selects the right server and tool for each capability request.

| Feature | Description |
|---|---|
| Capability resolution | Match an incoming capability request to one or more candidate tools |
| Policy-aware selection | Filter candidates by agent class trust policy before ranking |
| Latency hints | Optionally prefer lower-latency servers when multiple match |
| Fallback chain | If the primary server fails, try the next best match |
| Response normalization | Return a consistent response shape regardless of which server handled the request |
| Explainability | Attach the routing decision reason to each response for audit and debugging |

### 4. Policy Layer

Controls which agents can access which tools under which conditions.

| Feature | Description |
|---|---|
| Trust levels | Assign `trusted`, `restricted`, or `approval-gated` to each server or individual tool |
| Agent class mapping | Define agent classes and map them to allowed trust levels |
| Policy rules | Simple Python rules for conditions, exceptions, and overrides |
| Approval workflows | Optional async approval flow for `approval-gated` capability requests |
| Policy audit trail | Log every policy match, denial, and exception |

### 5. Audit Pipeline

Captures every routed call, denial, fallback, and policy decision.

| Feature | Description |
|---|---|
| Request log | Every capability request: agent, capability, server chosen, latency, outcome |
| Denial log | Every denied request: agent, capability, policy rule that denied it |
| Policy change log | Every trust level change, agent class update, or rule modification |
| Export | JSON and CSV export for compliance and analysis |
| Retention | Configurable retention window with automatic archival |

### 6. Admin UI

A web interface for managing the fabric.

| Feature | Description |
|---|---|
| Server inventory | Table of all registered servers with health, trust level, tool count |
| Capability browser | Search and browse the capability catalog with drill-down into tools |
| Policy editor | Create and modify trust levels, agent classes, and policy rules |
| Bundle curator | Create capability packs by selecting capabilities and assigning agent classes |
| Audit viewer | Filterable log viewer for requests, denials, and policy changes |
| Trust posture | At-a-glance view of unreviewed servers, policy exceptions, and risk signals |

### 7. Alerting

Proactive notifications for events that require platform team attention.

| Feature | Description |
|---|---|
| Health degradation alerts | Notify when a server fails N consecutive health checks or failover count spikes |
| Unreviewed server alert | Notify when a server remains unreviewed beyond a configurable threshold (default 48 hours) |
| Denial rate spike alert | Notify when an agent class experiences a sudden increase in denied capability requests |
| Schema change notification | Notify admins when a server's tool schema changes after re-inspection |
| Notification channels | Email, webhook, Slack — configurable per alert type |
| Alert history | Browse and filter past alerts alongside audit logs |

These alerts surface naturally in existing journeys — Jordan (Journey 4) gets proactive alerts instead of purely manual review, and the platform team is notified automatically during server failures (Journey 6).

### 8. Telemetry and Observability

Monitoring Fabric itself — request metrics, traces, dashboards, and alerts for the platform team operating Fabric.

| Feature | Description |
|---|---|
| Prometheus metrics | `/metrics` endpoint exposing request volume, latency distribution, error rates, routing decisions, policy evaluations |
| OpenTelemetry traces | Distributed traces for every capability request: resolution → policy → route → server call → normalize → return |
| Health check endpoint | `/health` returning Fabric API status, database connectivity, Redis connectivity |
| Pre-built Grafana dashboard | JSON dashboard definition for request volume, latency, errors, server health, routing accuracy |
| Alert rules | Configurable alert thresholds for latency spikes, error rate increases, server degradation, unreviewed servers |
| Trace sampling | Configurable sampling rate (100% in dev, 10% in production) to manage trace volume |

### 9. Authentication

Securing Fabric access for agents and admin users.

| Feature | Description |
|---|---|
| Agent authentication | API key or JWT bearer token per agent identity, bound to agent class |
| Token management | Issue, rotate, revoke agent tokens with grace periods and expiration |
| Rate limiting | Configurable requests-per-minute limits per agent identity |
| Admin UI authentication | Username/password with optional MFA (TOTP, WebAuthn), OAuth2 (Google, GitHub) |
| Role-based access | `admin` (full control), `editor` (team-scoped), `viewer` (read-only audit/catalog) |
| Session management | Configurable session timeout, forced logout, concurrent session limits |
| IP allow-listing | Optional IP range restriction for admin UI access |
| Auth audit log | Login events, token rotations, revocations, failed attempts — separate from capability audit |

---

## Success Metrics

| Metric | Target | How to Measure |
|---|---|---|
| Agent tool selection consistency | Agents choose the same best tool for the same capability request >95% of the time | Audit log analysis |
| Audit coverage | 100% of routed calls and denials captured in audit pipeline | Pipeline health check |
| Time to register new server | < 5 minutes from endpoint URL to production availability | UX benchmark |
| Trust review lag | No server remains unreviewed for > 48 hours | Registry status tracking |
| Capability pack adoption | 80%+ of agents use curated packs rather than raw server access | Agent class distribution |
| External engagement | 3+ external contributors or adopters within 6 months of v0.1.0 | GitHub issues, PRs, discussions |
| Routing accuracy | Correct server selected for capability request >90% of evaluation cases | Manual eval against test scenarios |
| Fabric API availability | 99.9% uptime during business hours | Prometheus uptime metrics |
| Routing latency (p95) | < 500ms total (Fabric overhead < 50ms, server call remainder) | Prometheus histogram |
| Telemetry coverage | 100% of capability requests traced, 100% of metrics exported | Telemetry health dashboard |
| Unauthenticated access | 0 successful unauthenticated requests | Auth audit log |

---

## PR/FAQ

**FOR IMMEDIATE RELEASE**

### MCP Fabric Launches to Turn a Pile of MCP Servers Into a Real Agentic Platform

**SEATTLE, WA** — Debashish Ghosal today announced MCP Fabric, an open-source tool mesh for MCP ecosystems. MCP Fabric provides discovery, schema normalization, trust policies, and capability routing so teams can run many MCP servers as a coherent agentic platform rather than a loose collection of connectors.

"MCP is becoming the interface standard for agent tools, but standards don't remove platform problems," said Ghosal. "Once teams have many servers, they need discovery, curation, and trust controls. MCP Fabric is that missing layer."

Available at [github.com/deghosal-2026/mcp-fabric](https://github.com/deghosal-2026/mcp-fabric).

### FAQ

**Q: Isn't MCP already enough?**

A: MCP standardizes the interface. MCP Fabric manages the ecosystem that grows on top of it.

**Q: Who benefits most?**

A: Platform teams, AI infrastructure teams, and advanced builders working with many MCP servers.

**Q: Can this be built locally?**

A: Yes. The reference architecture is deliberately local-first and OSS-only.

**Q: How is this different from a simple proxy?**

A: A proxy relays calls. MCP Fabric models capabilities, enforces policy, resolves ambiguity, and provides audit. The hard part is not forwarding requests — it is choosing the right tool under the right policy and explaining why.

**Q: What makes the MVP good enough?**

A: If an agent connected through the fabric has a cleaner, safer, more understandable tool experience than the same agent connected directly to raw server sprawl, the MVP is meaningful.

---

## Future Considerations

Scenarios and features explicitly deferred from v0.1.0 — important, but not in the initial build scope.

### Multi-Environment Separation (dev / staging / prod)

A production incident response agent should not see dev servers, and a dev agent should never route through production servers. Currently, Fabric trusts the platform engineer to label servers correctly. A first-class environment tag with enforced isolation (servers tagged `env:prod` are invisible to agents tagged `env:dev` and vice versa) is a natural v0.2.0 addition.

### Rate Limiting and Quota

There is no mechanism today to prevent an agent from flooding the fabric with capability requests. Rate limiting per agent class, per capability, and per server — with configurable quotas and burst allowances — belongs in the routing engine as a policy extension.

### API and CLI Access for CI/CD

All journeys are UI-driven. Platform teams running automated tests or CI pipelines need programmatic access: register servers, update policies, and query audit logs via API or CLI. The admin API exists internally — exposing it with stable endpoints and authentication is a v0.2.0+ item.

### PII and Sensitive Data Controls in Audit Logs

Tool responses may contain sensitive data (code, configuration, customer identifiers). The audit pipeline today logs routed calls with full response payloads. A configurable redaction or sampling policy for audit log content — or the ability to log only metadata (capability, server, latency) without the response body — should be added before production deployment.

### Horizontal Scaling of Fabric Itself

Fabric is a central routing layer. As server count and request volume grow, Fabric itself becomes a bottleneck. The current architecture assumes a single Fabric instance. Multi-instance Fabric with shared registry state, leader election for health checks, and distributed routing is a future scaling concern.

### API Versioning for the Fabric Protocol

The capability request format, agent identity format, and normalized response schema will evolve. A versioned Fabric API (`/v1/capability/request` vs `/v2/`) lets clients and agents adopt changes without breakage. This should be designed before the first external integration lands.

### Multi-Organization / Federation

Two organizations each running their own Fabric instance may want to share select capabilities (e.g., a partner team's docs search server). Cross-fabric federation — capability sharing, trust delegation, and audit across Fabric instances — is a long-term platform vision.

---

## Glossary

| Term | Definition |
|---|---|
| **Agent** | An AI system that makes capability requests through Fabric. Each agent has an identity and belongs to exactly one agent class. |
| **Agent class** | A named group of agents that share the same trust profile and capability surface (e.g., `agent:incident-responder`, `agent:developer`). |
| **Agent identity** | A unique identifier for an agent, authenticated via API key or JWT. Bound to one agent class. |
| **Capability** | A normalized, abstract description of what an agent can do (e.g., `code:search`, `incident:get`). Defined by the platform team in the Capability Catalog. |
| **Capability catalog** | The central registry of all capabilities, their normalized schemas, and their mappings to specific MCP server tools. |
| **Capability mapping** | The relationship between a raw MCP server tool and its normalized capability. A single capability can map to tools from multiple servers. |
| **Capability pack** | A curated set of capabilities assigned to an agent class. Defines the full capability surface that agents of that class can access. |
| **Capability request** | An API call from an agent to Fabric asking for a specific capability with parameters. |
| **Capability surface** | The set of capabilities available to a specific agent, returned at authentication time. |
| **Conflict** | When two or more MCP servers claim the same capability. Resolved by a platform engineer with routing rules. |
| **Fallback** | When the primary server for a capability is unavailable, Fabric routes to the next-best server. |
| **Fabric** | Shorthand for MCP Fabric — the tool mesh layer between agents and MCP servers. |
| **MCP server** | Any server implementing the Model Context Protocol. Registered in Fabric's server registry. |
| **Policy** | Rules that determine whether an agent class can access a capability from a given server. Based on trust levels and agent class mappings. |
| **Registry** | The canonical store of all MCP servers registered with Fabric, including their metadata, tool definitions, health status, and trust assignments. |
| **Routing engine** | The component that selects which MCP server to route a capability request to, based on capability match, policy, latency, and routing rules. |
| **Routing rule** | An explicit preference set by a platform engineer to resolve capability conflicts (e.g., "use Server A for general requests, Server B when `file_pattern` is present"). |
| **Schema diff** | The difference between a server's current tool definitions and a previous version. Used during server upgrades to detect breaking changes. |
| **Trust level** | The classification of a server or tool: `trusted` (no restrictions), `restricted` (limited agent classes), or `approval-gated` (human approval required per request). |

## Assumptions

Fabric is built on the following assumptions. If any of these change significantly, the product scope may need revisiting.

1. **MCP adoption continues to grow.** Fabric's value increases with the number of MCP servers an organization runs. If MCP adoption stalls or the protocol is replaced, Fabric's relevance diminishes.

2. **Teams will run multiple MCP servers.** Fabric is not useful for teams with 1-3 servers. The assumption is that MCP server sprawl is common (and growing) among teams building agentic systems.

3. **MCP servers implement the standard `/tools/list` endpoint.** Fabric relies on MCP servers correctly exposing their tool definitions for auto-inspection. Non-compliant servers can still be registered but won't benefit from auto-discovery.

4. **Platform teams want governance, not just connectivity.** Fabric adds a routing hop and configuration overhead. This tradeoff only makes sense if the team values governance, audit, and curated tool access — not just raw connectivity.

5. **Agents can tolerate an additional ~50ms routing overhead.** Fabric sits in the critical path. The assumption is that the governance and safety benefits justify the latency cost for most use cases. Latency-sensitive real-time systems may need to route around Fabric for specific calls.

6. **Agent identity is manageable.** Fabric assumes agents have stable identities (API keys or JWTs) that can be issued, rotated, and revoked. If agent identity management is chaotic or absent, Fabric's policy layer cannot function.

7. **Local-first development is valuable for OSS adoption.** The architecture assumes Docker Compose and local PostgreSQL/Redis provide a meaningful development experience for contributors.

## Known Unknowns / Open Questions

1. **Capability taxonomy standardization.** Should Fabric ship with a default taxonomy (common capability names like `code:search`, `incident:get`) or remain entirely user-defined? A default taxonomy accelerates onboarding but risks being wrong for many teams. A user-defined taxonomy is flexible but creates more setup work.

2. **Human approval UX at scale.** Journey 7 shows one approval. What happens when an organization has 50 approval-gated requests per hour? Does Fabric need an approval queue, bulk approve/deny, auto-approval for low-risk patterns? The current design works for low volume but needs revisiting at scale.

3. **Server health check depth.** Currently, Fabric health-checks servers by pinging `/tools/list`. Is this sufficient? A server can respond to `/tools/list` but fail on actual tool calls. Deeper health checks (calling a "canary" tool periodically) add reliability but also add load on target servers.

4. **Audit log retention and PII.** Journey 18 shows audit export for compliance, but the PRD doesn't specify defaults for log retention, PII redaction, or right-to-deletion. These are important for GDPR, SOC2, and enterprise adoption but are complex to design upfront.

5. **Fabric as a single point of failure.** If Fabric goes down, agents cannot make capability requests. The blue-green upgrade (Journey 25) mitigates planned downtime, but unplanned outages still block agents. Should Fabric support a "degraded mode" where agents fall back to direct server connections? This would require agents to maintain a dual connection model.

6. **MCP protocol evolution.** MCP is a developing standard. New MCP features (streaming responses, bidirectional communication, resource templates) may require Fabric to evolve its routing, normalization, and policy models. How tightly should Fabric couple to the current MCP spec vs. build abstractions that survive protocol changes?

7. **Pricing / sustainability.** Fabric is open-source and MIT-licensed. If adoption grows, maintaining the project requires sustained contribution. Is the plan purely community-driven maintenance, or is there a long-term sustainability model (sponsorship, managed hosting, enterprise support)?
