# MCP Fabric — Admin UI User Guide

> **Version:** 1.0  
> **Applies to:** v0.1.0  
> **Last updated:** 2026-07-24

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Dashboard](#2-dashboard)
3. [Server Management](#3-server-management)
4. [Capability Catalog](#4-capability-catalog)
5. [Agent Classes](#5-agent-classes)
6. [Policy Editor](#6-policy-editor)
7. [Audit Log](#7-audit-log)
8. [Approvals](#8-approvals)
9. [Capability Packs](#9-capability-packs)
10. [Alerts](#10-alerts)
11. [Admin Users](#11-admin-users)
12. [Trust Posture](#12-trust-posture)
13. [Navigation & Layout](#13-navigation--layout)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Getting Started

### Accessing the Admin UI

The Admin UI runs on port 3000 in development:

```bash
docker-compose up        # Full stack
cd ui && npm run dev     # UI only (API proxy to localhost:8000)
```

Open `http://localhost:3000` in your browser. You'll see the login screen:

![Login page](ui-test/findings/screenshots/01-login.png)

### Logging In

1. Enter your **Username** and **Password** (provided by your platform admin)
2. Click **Login**
3. If MFA is enabled, enter your 6-digit authentication code from your authenticator app

On first login, you'll land on the Dashboard. The sidebar on the left shows all available pages, filtered by your role.

---

## 2. Dashboard

The Dashboard is the home page and gives a high-level overview of your Fabric instance:

![Dashboard](ui-test/findings/screenshots/02-dashboard.png)

### Stat Cards

Four metric cards at the top show:
- **Servers** — Total number of registered MCP servers
- **Healthy** — Servers passing health checks
- **Pending Approvals** — Capability requests awaiting human review
- **Degraded Servers** — Servers with health issues requiring attention

### Recent Activity Panels

- **Recent Servers** — Last 5 registered servers, with health status badges. Click any server to navigate to its detail view.
- **Pending Approvals** — Open approval requests requiring action. Click to jump to the Approvals page.
- **Recent Audit Events** — Latest activity across the fabric, with timestamps and actor information.

---

## 3. Server Management

The Servers page is where you register, inspect, and manage MCP servers:

![Servers list](ui-test/findings/screenshots/03-servers.png)

### Server Table

Each row shows:
- **Name** — Human-readable server identifier
- **Endpoint** — Network address (URL)
- **Team** — Owning team namespace
- **Health** — Current status (Healthy / Degraded / Unhealthy)
- **Trust** — Assigned trust level (Trusted / Restricted / Approval-gated / Unreviewed)
- **Tools** — Number of tools exposed by the server

**Filtering:** Use the dropdowns above the table to filter by Health, Trust level, or Team. Use the search box to find servers by name.

### Registering a New Server

![Register modal](ui-test/findings/screenshots/04-servers-register-modal.png)

1. Click **Register Server**
2. Fill in:
   - **Name** — A unique identifier (e.g., `KB Server`)
   - **Endpoint** — The server's URL (e.g., `http://kb.internal:3001`)
   - **Owner Team** — The team responsible (e.g., `platform`)
   - **Labels** — Comma-separated tags for organization (e.g., `knowledge, internal, read-only`)
3. Click **Save**

Fabric will automatically inspect the server's `/tools/list` endpoint and import all tool definitions. After registration, the server appears in the table with its auto-discovered tools.

### Server Detail View

Click any server row to see:
- Full server metadata
- Imported tools with their input/output schemas
- Routing rules
- Trust assignments

From the detail view, you can:
- **Re-inspect** — Refresh the tool list to detect schema changes
- **Decommission** — Begin a phased server sunset with dependency reporting

---

## 4. Capability Catalog

The Capability Catalog is the normalized abstraction layer that maps raw MCP tools to meaningful capabilities:

![Capabilities](ui-test/findings/screenshots/05-capabilities.png)

### Capability Table

Each capability shows:
- **Name** — Normalized identifier (e.g., `knowledge:search`)
- **Domain** — Functional area (code, knowledge, deployment, security, incident)
- **Description** — What the capability does
- **Status** — Active or Deprecated

**Filtering:** Filter by Domain or Status using the dropdowns. Use the search box to find capabilities.

### Creating a Capability

![Create capability modal](ui-test/findings/screenshots/06-capabilities-create-modal.png)

1. Click **Create Capability**
2. Fill in:
   - **Name** — Use the `domain:action` convention (e.g., `code:search`)
   - **Domain** — Functional grouping
   - **Description** — Clear explanation of what this capability provides
3. Click **Save**

After creation, you can **Map Tool** from the detail view to connect this capability to a specific server tool.

### Deprecating a Capability

Click **Deprecate** on any active capability. A confirmation dialog appears explaining that:
- The capability will be removed from all packs
- Agents will receive a deprecation notice for 14 days (configurable grace period)
- After grace, requests return `capability_not_found`

---

## 5. Agent Classes

Agent classes define categories of AI agents and their access levels:

![Agent Classes](ui-test/findings/screenshots/07-agent-classes.png)

### Creating an Agent Class

1. Click **Create Agent Class**
2. Enter:
   - **Name** — Use the `agent:role` convention (e.g., `agent:developer`)
   - **Description** — What this class of agent does

### Managing Tokens

Each agent class can have multiple identity tokens. Click **Tokens** on any class to:

- **Generate** a new token — the token is shown **once** with a yellow warning. Copy it immediately — it will not be shown again.
- **View existing tokens** — See token prefixes (`fcp_****`) and statuses (active/revoked/expired)
- **Rotate or revoke** tokens as needed

> ⚠ **Important:** Tokens are shown only once at creation time. If you close the modal without copying, you must generate a new token and rotate the old one.

---

## 6. Policy Editor

The Policy Editor lets you manage OPA (Open Policy Agent) Rego policies that govern access decisions:

![Policies](ui-test/findings/screenshots/08-policies.png)

### Viewing Deployed Policies

The policy list shows all deployed versions with their version number and deployment timestamp.

### Deploying a New Policy

![Policy editor](ui-test/findings/screenshots/09-policies-editor.png)

1. Click **New Policy**
2. Write or paste your Rego policy in the editor textarea
3. Click **Deploy**

The new policy becomes active immediately. Previous versions are retained for audit. Default policies shipped with Fabric:

- Trust level hierarchy (trusted → restricted → approval-gated → unreviewed)
- Agent class minimum trust requirements
- Cross-team namespace access controls
- Approval-gated capability rules

---

## 7. Audit Log

The Audit Log provides a complete, immutable record of all activity across the fabric:

![Audit Log](ui-test/findings/screenshots/10-audit.png)

### Event Types

| Type | Description |
|---|---|
| `capability_request` | An agent made a capability request |
| `policy_change` | An admin deployed or modified a policy |
| `server_registered` | A new MCP server was added to the registry |
| `server_decommissioned` | A server was removed from the registry |
| `approval_resolved` | A pending approval was approved or denied |

### Filtering

- **Event Type** — Show only specific activity categories
- **Actor** — Filter by agent or admin actions
- **Search** — Find events by actor ID
- **Date range** — Use cursor pagination to browse historical data

### Exporting

Click **Export** to generate a structured JSON export of filtered audit events for compliance reporting (SOC2, SOX, etc.).

---

## 8. Approvals

The Approvals page manages human-in-the-loop review for approval-gated capabilities:

![Approvals](ui-test/findings/screenshots/11-approvals.png)

### Approval Queue

Each pending request shows:
- **Agent** — Which agent made the request
- **Capability** — What capability was requested (e.g., `deployment:promote`)
- **Status** — Pending, Approved, or Denied
- **Requested** — When the request was made

Filter by status to see only pending, approved, or denied requests.

### Reviewing a Request

![Review panel](ui-test/findings/screenshots/12-approvals-review.png)

Click **Review** on any pending request to open the review panel:

1. Review the request details: agent, capability, server, and parameters
2. Add a **Note / Reason** (optional but recommended for audit)
3. Choose:
   - **Approve** — Route the request to the server
   - **Deny** — Reject the request with a reason

Every approval and denial is logged to the audit trail.

---

## 9. Capability Packs

Packs let you curate groups of capabilities for different agent classes:

![Capability Packs](ui-test/findings/screenshots/13-packs.png)

### Creating a Pack

1. Click **Create Pack**
2. Enter a name and description
3. From the detail view, add capabilities and assign to agent classes

### Assigning to Classes

Use the **Assign** button to connect a pack to one or more agent classes. Agents in those classes will automatically see the pack's capabilities in their surface. When a capability is deprecated, it's automatically removed from all packs.

### Use Case: New Hire Onboarding

Create a "New Hire — Platform Engineer" pack with read-only capabilities (docs search, code search, PR status) and assign it to the `agent:new-hire` class. As engineers ramp up, promote them to a class with a broader pack.

---

## 10. Alerts

The Alerts page surfaces operational issues that need attention:

![Alerts](ui-test/findings/screenshots/14-alerts.png)

### Alert Types

| Trigger | Example |
|---|---|
| Server degradation | "Code Search server degraded — failover count 3 in 5m" |
| Server unreachable | "Vuln Scanner unreachable for 2m" |
| Unreviewed server | "New server has been unreviewed for 7 days" |
| Denial spike | "Capability denial rate exceeded 10% threshold" |

### Acknowledging Alerts

Click **Acknowledge** on any alert to indicate you've seen it. Acknowledged alerts remain in the log for reference but are visually marked as handled. Filter by acknowledged/unacknowledged status.

---

## 11. Admin Users

Manage human administrators who access the Fabric admin UI:

![Admin Users](ui-test/findings/screenshots/15-admin-users.png)

### User Table

Each user shows:
- **Username** and **Email**
- **Role** — Admin, Editor, or Viewer
- **Status** — Active, Invited, or Deactivated
- **MFA** — Whether multi-factor authentication is enabled

### Inviting a User

![Invite modal](ui-test/findings/screenshots/16-admin-users-invite.png)

1. Click **Invite User**
2. Enter:
   - **Username**
   - **Email** — The invitation will be sent here
   - **Role** — Choose access level

### Role Definitions

| Role | Permissions |
|---|---|
| **Admin** | Full access to all pages and actions |
| **Editor** | Can manage servers, capabilities, policies, approvals, packs. Cannot manage admin users. |
| **Viewer** | Read-only access to Dashboard, Servers, Capabilities, Audit Log, and Trust Posture |

### Deactivating Users

Click **Deactivate** on any active user. You cannot deactivate your own account. Deactivated users cannot log in.

---

## 12. Trust Posture

The Trust Posture page gives a security-focused view of all servers and their trust levels:

![Trust Posture](ui-test/findings/screenshots/17-trust-posture.png)

### Server Cards

Each server is displayed as a card with a color-coded left border:
- 🟢 **Green** — Trusted
- 🟡 **Yellow** — Restricted
- 🟠 **Orange** — Approval-gated
- 🔴 **Red** — Unreviewed

Each card shows the server name, endpoint, health status, owner team, and current trust level.

### Managing Trust Levels

![Trust Posture with class selected](ui-test/findings/screenshots/18-trust-posture-class-selected.png)

1. **Select an Agent Class** from the dropdown at the top right
2. For each server, use the trust level dropdown to change its trust assignment for the selected class
3. Changes take effect immediately — agents in that class will see updated access on their next capability request

Changes are optimistic: the UI updates immediately and reverts if the API call fails.

### Reviewing Unreviewed Servers

Servers with trust level "Unreviewed" show a "⚠ Needs review" badge. These servers should be reviewed and assigned a trust level before agents can use them. Use this dashboard to quickly identify and address unreviewed servers.

---

## 13. Navigation & Layout

### Sidebar

The sidebar on the left provides navigation to all pages. Active pages are highlighted with a blue background. The sidebar items are filtered by your role — admins see all pages, editors see management pages, viewers see read-only pages.

### Top Bar

The top bar shows:
- **Welcome message** with your username
- **Role badge** indicating your permission level
- **Logout button** to end your session

### Error Handling

If a page crashes unexpectedly, an error boundary catches the failure and shows:
- An error message describing the issue
- **Try again** — Attempts to recover the page
- **Go to Dashboard** — Navigates to the home page

---

## 14. Troubleshooting

### Login Issues

| Problem | Solution |
|---|---|
| Wrong credentials | Check username/password. Passwords are case-sensitive. |
| MFA code not working | Ensure your authenticator app's time is synced. Try the recovery code. |
| Account locked | Contact your admin. Accounts lock after 5 failed attempts. |

### Server Registration

| Problem | Solution |
|---|---|
| Server not appearing after registration | Check that the server endpoint is reachable from the Fabric API. |
| Tools not imported | Verify the server implements the MCP `/tools/list` endpoint. |
| Server shows "Unhealthy" | The server may be down or unreachable. Check the endpoint URL. |

### Capability Mapping

| Problem | Solution |
|---|---|
| Capability not available to agents | Check that: (1) a tool is mapped, (2) trust level is set for the agent class, (3) the agent class is assigned to the pack containing the capability. |
| Wrong server selected for a capability | Adjust routing rules from the capability detail view or server detail view. |

### Audit & Compliance

| Problem | Solution |
|---|---|
| Export taking too long | Large exports may take time. Check the background tasks view. |
| Missing audit events | Ensure the Fabric API has database connectivity. Audit writes are synchronous. |

### Getting Help

- **GitHub Issues:** [github.com/deghosal-2026/mcp-fabric/issues](https://github.com/deghosal-2026/mcp-fabric/issues)
- **Documentation:** See `docs/` for architecture, deployment, and API reference
