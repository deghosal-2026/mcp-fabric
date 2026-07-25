# UI Test Cases — Page Smoke Tests

> **Area:** Pages  
> **Plan reference:** Layer 4 (34 tests)  
> **Test prefix:** `TC-PAGE`  
> **Last updated:** 2026-07-24

---

## 1. Dashboard

### TC-PAGE-001: Renders 4 stat cards with mock data values

**Description:** The Dashboard displays four stat cards: Servers, Healthy, Pending Approvals, and Degraded Servers. Each card must render the correct numeric value from the `fetchDashboard()` API response so operators can assess system health at a glance.

**Severity:** Critical

**Preconditions:**
- Mock `fetchDashboard()` returns `{ server_count: 12, healthy_servers: 8, pending_approvals: 3, degraded_servers: 2 }`
- Mock `fetchServers({ per_page: '5' })` returns 2 items
- Mock `fetchApprovals({ status: 'pending', per_page: '5' })` returns 0 items
- Mock `fetchAuditEvents({ per_page: '5' })` returns 2 items

**Test Steps:**
1. Render `<DashboardPage />`
2. Find the card labeled "Servers" and read its value
3. Find the card labeled "Healthy" and read its value
4. Find the card labeled "Pending Approvals" and read its value
5. Find the card labeled "Degraded Servers" and read its value

**Expected Results:**
- The "Servers" card shows the number `12`
- The "Healthy" card shows the number `8` and has the `text-green-600` class
- The "Pending Approvals" card shows the number `3` and has the `text-yellow-600` class
- The "Degraded Servers" card shows the number `2` and has the `text-red-600` class
- All four cards are rendered in the same grid container (child of the grid div)

---

### TC-PAGE-002: Renders 3 panel sections (Recent Servers, Pending Approvals, Recent Audit Events)

**Description:** Below the stat cards, the Dashboard displays three panel sections with section headings. Each section fetches its own data independently and provides a "View all" link to the full-page view.

**Severity:** Critical

**Preconditions:**
- Mock `fetchDashboard()` returns valid stats
- Mock `fetchServers({ per_page: '5' })` returns:
  ```json
  {
    "items": [
      { "id": "srv-1", "name": "KB Server", "endpoint": "http://localhost:3001", "health_status": "healthy", "trust_level": "trusted", "owner_team": "platform", "labels": ["kb"], "team_namespace": "team:platform", "created_at": "2026-07-01T00:00:00Z", "decommissioned_at": null },
      { "id": "srv-2", "name": "Code Search", "endpoint": "http://localhost:3002", "health_status": "healthy", "trust_level": "trusted", "owner_team": "platform", "labels": ["code"], "team_namespace": "team:platform", "created_at": "2026-07-02T00:00:00Z", "decommissioned_at": null }
    ],
    "pagination": { "total": 2, "has_more": false, "per_page": 5 }
  }
  ```
- Mock `fetchApprovals({ status: 'pending', per_page: '5' })` returns 2 pending items
- Mock `fetchAuditEvents({ per_page: '5' })` returns 3 events

**Test Steps:**
1. Render `<DashboardPage />`
2. Look for the "Recent Servers" heading
3. Look for the "Pending Approvals" heading
4. Look for the "Recent Audit Events" heading
5. Verify the "Recent Servers" section renders server names and health badges
6. Verify the "Pending Approvals" section renders capability names and agent names
7. Verify the "Recent Audit Events" section renders event types and actor IDs
8. Verify each section has a "View all" link

**Expected Results:**
- The text "Recent Servers" is visible as an `<h2>` element
- The text "Pending Approvals" is visible as an `<h2>` element
- The text "Recent Audit Events" is visible as an `<h2>` element
- "Recent Servers" panel shows "KB Server" and "Code Search", each with a `<Badge>` showing their health status
- "Pending Approvals" panel shows 2 items with capability_name and agent_name
- "Recent Audit Events" panel shows 3 items with event_type (e.g., "server_registered") and actor_id
- "View all" links link to `/servers`, `/approvals`, and `/audit` respectively
- Server names are rendered as `<a>` links pointing to `/servers/srv-1` and `/servers/srv-2`

---

### TC-PAGE-003: Loading state shows skeleton, error state with retry

**Description:** The Dashboard runs 4 independent queries (stats, servers, approvals, audit). Each section wrapped in `<PageState>` must independently show a loading skeleton while its query is in flight and an error state with retry if the query fails.

**Severity:** Critical

**Preconditions:**
- All 4 queries start in `isLoading: true` state

**Test Steps:**
1. Render `<DashboardPage />` with all 4 queries in loading state
2. Observe the rendered output
3. Update the stats query to error state: `{ isLoading: false, error: new Error('Dashboard API unavailable'), data: undefined }`
4. Observe the rendered output

**Expected Results:**
- **Loading state:** No stat card numbers are visible; the stat cards grid area shows pulsing skeleton divs (`animate-pulse` class)
- **Loading state:** Each of the 3 panels shows pulsing skeleton rows, no server/approval/event data
- **Error state (stats):** The stat cards area shows an error message containing "Dashboard API unavailable" and a "Retry" button
- **Error state (other panels):** The servers, approvals, and audit panels continue to show their own loading skeletons (since only the stats query was set to error)
- Clicking the Retry button in the stats error state calls `query.refetch()` for the dashboard query

---

## 2. Servers

### TC-PAGE-004: Renders table with health/trust badges

**Description:** The Servers page displays a table listing all registered MCP servers. Each row renders the server's name, endpoint, team, and health and trust status as `<Badge>` components.

**Severity:** Critical

**Preconditions:**
- Mock `fetchServers({ per_page: '50' })` returns 2 servers:
  ```json
  {
    "items": [
      { "id": "srv-1", "name": "KB Server", "endpoint": "http://localhost:3001", "owner_team": "platform", "labels": ["kb"], "health_status": "healthy", "trust_level": "trusted", "tools": [{ "id": "t1", "tool_name": "search" }], "team_namespace": "team:platform", "created_at": "2026-07-01T00:00:00Z", "decommissioned_at": null },
      { "id": "srv-2", "name": "Deployment API", "endpoint": "http://localhost:3003", "owner_team": "platform", "labels": ["deploy"], "health_status": "degraded", "trust_level": "restricted", "tools": [{ "id": "t2", "tool_name": "deploy" }, { "id": "t3", "tool_name": "rollback" }], "team_namespace": "team:platform", "created_at": "2026-07-02T00:00:00Z", "decommissioned_at": null }
    ],
    "pagination": { "total": 2, "has_more": false, "per_page": 50 }
  }
  ```

**Test Steps:**
1. Render `<ServersPage />`
2. Wait for data to load
3. Inspect the table headers
4. Inspect the table rows

**Expected Results:**
- Table headers show: "Name", "Endpoint", "Team", "Health", "Trust", "Tools"
- Row 1 shows "KB Server", "http://localhost:3001", "platform", a green Badge with "healthy" label, a green Badge with "trusted" label, and `1` (tools count)
- Row 2 shows "Deployment API", "http://localhost:3003", "platform", a yellow Badge with "degraded" label, a yellow Badge with "restricted" label, and `2` (tools count)
- The "Register Server" button is visible in the header

---

### TC-PAGE-005: Register modal opens, form submits with correct data

**Description:** Clicking "Register Server" opens a modal with form fields for name, endpoint, owner team, and labels. Submitting the form calls `registerServer()` with the correct payload.

**Severity:** Critical

**Preconditions:**
- Mock `fetchServers()` returns empty list
- Mock `registerServer()` resolves successfully

**Test Steps:**
1. Render `<ServersPage />`
2. Click the "Register Server" button
3. Fill in the Name field with "My Test Server"
4. Fill in the Endpoint field with "http://localhost:9999"
5. Fill in the Owner Team field with "team:security"
6. Fill in the Labels field with "test, staging, experimental"
7. Click the "Save" (confirm) button in the modal

**Expected Results:**
- Modal appears with title "Register MCP Server"
- Modal shows input fields: Name (autofocused), Endpoint (placeholder "http://localhost:3001"), Owner Team, Labels (placeholder "security, production, read-only")
- Confirm button is initially disabled (when Name and Endpoint are empty)
- After filling fields, confirm button becomes enabled
- On click, `registerServer()` is called with: `{ name: "My Test Server", endpoint: "http://localhost:9999", owner_team: "team:security", labels: ["test", "staging", "experimental"] }`
- On success, modal closes, form resets, `queryClient.invalidateQueries({ queryKey: ['servers'] })` is called, and a success toast "Server registered successfully" appears

---

### TC-PAGE-006: Labels parsed from comma-separated string to array

**Description:** The labels field accepts a comma-separated string that must be split into an array of trimmed strings before being sent to the API. Empty entries from trailing/leading commas must be filtered out.

**Severity:** Important

**Preconditions:**
- Mock `registerServer()` spies on the argument

**Test Steps:**
1. Open the Register modal
2. Fill Name with "Test Server" and Endpoint with "http://localhost:5000"
3. Type "security, production, read-only" into the Labels field
4. Click the Save button

**Expected Results:**
- `registerServer()` is called with `labels: ["security", "production", "read-only"]`
- Each label is trimmed of whitespace

**Test Steps (edge cases):**
5. Close and reopen modal
6. Type " label1 , label2 , " into Labels (extra spaces around commas)
7. Submit

**Expected Results:**
- `registerServer()` is called with `labels: ["label1", "label2"]`
- Empty strings are filtered out
- Single label without commas works: "single-label" → `["single-label"]`

---

### TC-PAGE-007: Filter change triggers query refetch

**Description:** Selecting a filter option in the FilterBar changes the `filters` state, which updates the query key `['servers', filters]`, causing TanStack Query to refetch with the new parameters.

**Severity:** Important

**Preconditions:**
- Mock `fetchServers()` spy that records arguments
- Initial render loads with empty filters

**Test Steps:**
1. Render `<ServersPage />`
2. Change the Health filter dropdown to "Healthy" (value `healthy`)
3. Wait for the second query to fire

**Expected Results:**
- Initially `fetchServers()` is called with `{ per_page: '50' }`
- After changing the filter to "Healthy", `fetchServers()` is called with `{ per_page: '50', health_status: 'healthy' }`
- The query key changes from `['servers', {}]` to `['servers', { health_status: 'healthy' }]`
- The table re-renders with the new data

---

## 3. Capabilities

### TC-PAGE-008: Renders table with name, domain, status badges

**Description:** The Capability Catalog page lists all capabilities in a table with their name, domain, description, status (rendered as a Badge), and an Actions column with a Deprecate button.

**Severity:** Critical

**Preconditions:**
- Mock `fetchCapabilities({ per_page: '100' })` returns 2 capabilities:
  ```json
  {
    "items": [
      { "id": "cap-1", "name": "code:search", "domain": "code", "description": "Search codebases", "status": "active", "norm_input_schema": {}, "norm_output_schema": {}, "deprecated_at": null, "grace_period_days": 0 },
      { "id": "cap-2", "name": "deploy:rollback", "domain": "deployment", "description": "Roll back a deployment", "status": "deprecated", "norm_input_schema": {}, "norm_output_schema": {}, "deprecated_at": "2026-07-10T00:00:00Z", "grace_period_days": 14 }
    ],
    "pagination": { "total": 2, "has_more": false, "per_page": 100 }
  }
  ```

**Test Steps:**
1. Render `<CapabilitiesPage />`
2. Inspect table headers and rows

**Expected Results:**
- Table headers: "Name", "Domain", "Description", "Status", "Actions"
- Row 1 shows "code:search", "code", "Search codebases", green Badge "active", and an enabled "Deprecate" button
- Row 2 shows "deploy:rollback", "deployment", "Roll back a deployment", gray Badge "deprecated", and a disabled "Deprecate" button (opacity-50)
- The "Create Capability" button is visible in the page header

---

### TC-PAGE-009: Create modal submits

**Description:** Clicking "Create Capability" opens a modal with name, domain, and description fields. Submitting calls `createCapability()` with the form data and invalidates the capabilities query.

**Severity:** Critical

**Preconditions:**
- Mock `createCapability()` resolves successfully

**Test Steps:**
1. Render `<CapabilitiesPage />`
2. Click "Create Capability"
3. Fill Name with "security:scan"
4. Fill Domain with "security"
5. Fill Description with "Scan for vulnerabilities"
6. Click Save

**Expected Results:**
- Modal title is "Create Capability"
- Name field has placeholder "code:search", Domain has placeholder "code"
- Confirm button is disabled until Name and Domain are filled
- On submit, `createCapability()` is called with `{ name: "security:scan", domain: "security", description: "Scan for vulnerabilities" }`
- On success, modal closes, form resets, query is invalidated, success toast "Capability created" appears

---

### TC-PAGE-010: Deprecate confirm dialog opens and submits with 14 grace days

**Description:** Clicking "Deprecate" on an active capability row opens a confirm dialog. Confirming calls `deprecateCapability()` with the capability ID and a 14-day grace period.

**Severity:** Important

**Preconditions:**
- Mock `fetchCapabilities()` returns 1 active capability (code:search)
- Mock `deprecateCapability()` resolves successfully

**Test Steps:**
1. Render `<CapabilitiesPage />`
2. Click the "Deprecate" button on the "code:search" row
3. Verify the confirm dialog is rendered
4. Click the "Deprecate" button in the dialog

**Expected Results:**
- A `<Modal>` with `destructive` prop appears with title "Deprecate Capability"
- Dialog body shows text: "Are you sure you want to deprecate **code:search**?"
- Message continues: "It will be removed from all capability packs and agents will receive a deprecation notice for 14 days."
- Confirm button label is "Deprecate" and has destructive styling (`bg-red-500`)
- On confirm, `deprecateCapability()` is called with `(cap-1, 14)`
- On success, dialog closes, query is invalidated, success toast "Capability deprecated" appears

---

### TC-PAGE-011: Filter change triggers refetch

**Description:** Selecting a domain or status filter updates the query key and causes `fetchCapabilities()` to be called with the new filter parameters.

**Severity:** Important

**Preconditions:**
- Mock `fetchCapabilities()` spy records arguments

**Test Steps:**
1. Render `<CapabilitiesPage />`
2. Change the "Status" filter dropdown to "Deprecated" (value `deprecated`)

**Expected Results:**
- `fetchCapabilities()` is called with `{ per_page: '100', status: 'deprecated' }`
- Query key changes from `['capabilities', {}]` to `['capabilities', { status: 'deprecated' }]`
- Table re-renders with only deprecated capabilities

---

## 4. AgentClasses

### TC-PAGE-012: Renders table

**Description:** The Agent Classes page lists all agent classes in a table showing their name, description, namespace, and an Actions column with a "Tokens" button.

**Severity:** Critical

**Preconditions:**
- Mock `fetchAgentClasses()` returns 2 classes:
  ```json
  [
    { "id": "class-1", "name": "agent:developer", "description": "Developer agent", "team_namespace": "team:platform" },
    { "id": "class-2", "name": "agent:security", "description": "Security scanning agent", "team_namespace": "team:security" }
  ]
  ```

**Test Steps:**
1. Render `<AgentClassesPage />`
2. Inspect the table

**Expected Results:**
- Table headers: "Name", "Description", "Namespace", "Actions"
- Row 1 shows "agent:developer", "Developer agent", "team:platform", and a "Tokens" button
- Row 2 shows "agent:security", "Security scanning agent", "team:security", and a "Tokens" button
- The "Create Agent Class" button is visible in the page header

---

### TC-PAGE-013: Create modal submits

**Description:** Clicking "Create Agent Class" opens a modal. Submitting with a name calls `createAgentClass()` and invalidates the agent-classes query.

**Severity:** Critical

**Preconditions:**
- Mock `createAgentClass()` resolves successfully

**Test Steps:**
1. Render `<AgentClassesPage />`
2. Click "Create Agent Class"
3. Fill Name with "agent:reviewer"
4. Fill Description with "Code review agent"
5. Click Save

**Expected Results:**
- Modal title is "Create Agent Class"
- Name field has placeholder "agent:developer", Description is a textarea
- Confirm button is disabled until Name is filled
- On submit, `createAgentClass()` is called with `{ name: "agent:reviewer", description: "Code review agent" }`
- On success, modal closes, form resets, query invalidated, success toast "Agent class created" appears

---

### TC-PAGE-014: Token generate shows token with warning banner; close + reopen shows create form again

**Description:** The token management modal uses a show-once pattern: after generating a token, the raw token value is displayed with a warning banner, and the create form is hidden. Closing and reopening the modal must reset state back to the create form. This is critical because the token cannot be retrieved again.

**Severity:** Critical

**Preconditions:**
- Mock `fetchAgentClasses()` returns 1 class
- Mock `fetchAgentIdentities(class-1)` returns empty array initially, then 1 item after generate
- Mock `createAgentIdentity(class-1, "CI Token")` returns `{ token: "fcp_abc123def456_secret" }`

**Test Steps:**
1. Render `<AgentClassesPage />`
2. Click "Tokens" on the first row
3. Verify the create form is shown
4. Type "CI Token" in the token name input
5. Click "Generate"
6. Observe the token display
7. Close the modal (click overlay or X button)
8. Reopen the modal (click "Tokens" again)

**Expected Results:**
- **Step 3:** The modal shows an input field with placeholder "Token name", a "Generate" button (disabled until text is entered), and a list of existing tokens (empty initially)
- **Step 5:** Generate button shows "..." while loading, then:
- **Step 6:** The input form is replaced by:
  - A yellow warning banner: "Copy this token now. It will not be shown again." (bg-yellow-50 border-yellow-200)
  - The token value `fcp_abc123def456_secret` rendered in a monospace code block (font-mono)
  - No "Generate" button or name input is visible
- **Step 8:** After reopening, the modal state is reset:
  - The input form is shown again (not the token display)
  - No warning banner is visible
  - The existing token is listed with its prefix `fcp_` followed by `****` and its status

---

## 5. Policies

### TC-PAGE-015: Renders deployed policy list

**Description:** The Policy Editor page lists all deployed Rego policies showing their version number and deployment timestamp.

**Severity:** Critical

**Preconditions:**
- Mock `fetchPolicies()` returns 2 policies:
  ```json
  [
    { "id": "pol-1", "version": "1", "deployed_at": "2026-07-15T10:00:00Z" },
    { "id": "pol-2", "version": "2", "deployed_at": "2026-07-16T14:30:00Z" }
  ]
  ```

**Test Steps:**
1. Render `<PoliciesPage />`
2. Inspect the policy list

**Expected Results:**
- Page title is "Policy Editor"
- Two policy cards are visible
- Card 1 shows "v1" and the formatted date "7/15/2026, 10:00:00 AM" (or locale equivalent)
- Card 2 shows "v2" and the formatted date "7/16/2026, 2:30:00 PM" (or locale equivalent)
- The "New Policy" button is visible in the page header

---

### TC-PAGE-016: New Policy opens editor with textarea

**Description:** Clicking "New Policy" opens an inline editor panel with a monospace textarea pre-populated with a Rego placeholder.

**Severity:** Important

**Preconditions:**
- Mock `fetchPolicies()` returns empty array

**Test Steps:**
1. Render `<PoliciesPage />`
2. Click "New Policy"

**Expected Results:**
- A full-screen overlay (fixed inset-0 bg-black/50) appears
- A white panel (max-w-3xl) is centered in the overlay
- The panel title is "Edit Rego Policy"
- A textarea with class `font-mono` and height `h-96` is present
- The textarea placeholder shows: "package fabric.policy\ndefault allow := false\n..."
- A "Cancel" button and a "Deploy" button (disabled initially) are in the footer
- The "Cancel" button closes the editor

---

### TC-PAGE-017: Deploy submits and invalidates policies query

**Description:** Writing Rego content and clicking Deploy calls `deployPolicy()` with the textarea content, invalidates the policies query, and shows a success toast.

**Severity:** Critical

**Preconditions:**
- Mock `fetchPolicies()` returns initial empty array
- Mock `deployPolicy()` resolves successfully

**Test Steps:**
1. Render `<PoliciesPage />`
2. Open the New Policy editor
3. Type the following Rego content:
   ```
   package fabric.policy

   default allow := false

   allow {
       input.trust_level == "trusted"
   }
   ```
4. Click "Deploy"

**Expected Results:**
- Deploy button shows "Deploying..." while mutation is in flight
- `deployPolicy()` is called with the exact Rego content string entered in the textarea
- On success: editor closes, textarea content resets to empty, `queryClient.invalidateQueries({ queryKey: ['policies'] })` is called
- Success toast "Policy deployed" appears
- The policy list refreshes to show the newly deployed policy

---

## 6. Audit

### TC-PAGE-018: Renders audit table

**Description:** The Audit Log page displays audit events in a table with columns for time, event type, actor, and target.

**Severity:** Critical

**Preconditions:**
- Mock `fetchAuditEvents({ per_page: '50' })` returns 2 events:
  ```json
  {
    "items": [
      { "id": "evt-1", "event_type": "server_registered", "actor_type": "admin", "actor_id": "admin@fabric", "target_type": "server", "target_id": "srv-3", "details": {}, "created_at": "2026-07-20T08:00:00Z" },
      { "id": "evt-2", "event_type": "capability_request", "actor_type": "agent", "actor_id": "agent:dev-1", "target_type": "capability", "target_id": "cap-5", "details": {}, "created_at": "2026-07-20T09:30:00Z" }
    ],
    "pagination": { "total": 2, "has_more": false, "per_page": 50 }
  }
  ```

**Test Steps:**
1. Render `<AuditPage />`
2. Inspect the table

**Expected Results:**
- Table headers: "Time", "Type", "Actor", "Target"
- Row 1 shows the formatted date for "2026-07-20T08:00:00Z", "server_registered", "admin@fabric", "server"
- Row 2 shows the formatted date for "2026-07-20T09:30:00Z", "capability_request", "agent:dev-1", "capability"
- "Export" button is visible in the page header

---

### TC-PAGE-019: Export button calls exportAudit

**Description:** Clicking the Export button calls the `exportAudit()` function with the current filter state and shows a success toast with the export ID.

**Severity:** Important

**Preconditions:**
- Mock `exportAudit()` resolves with `{ export_id: "exp-20260724-001" }`

**Test Steps:**
1. Render `<AuditPage />`
2. Click the "Export" button

**Expected Results:**
- `exportAudit()` is called with `{}` (no filters active)
- On success, a toast appears: "Export started: exp-20260724-001"
- If `exportAudit()` throws, an error toast appears with the error message

---

### TC-PAGE-020: Filter by event type updates query key

**Description:** Changing the Event Type filter updates the query key `['audit', filters]` so that `fetchAuditEvents()` is called with the selected event type.

**Severity:** Important

**Preconditions:**
- Mock `fetchAuditEvents()` spy records arguments

**Test Steps:**
1. Render `<AuditPage />`
2. Change the "Event Type" filter to "Policy Change" (value `policy_change`)

**Expected Results:**
- `fetchAuditEvents()` is called with `{ per_page: '50', event_type: 'policy_change' }`
- Query key changes from `['audit', {}]` to `['audit', { event_type: 'policy_change' }]`
- Table re-renders with policy change events only

---

## 7. Approvals

### TC-PAGE-021: Renders approval table with status badges

**Description:** The Approvals page displays pending and historical approval requests in a table with agent name, capability name, status (rendered as Badge), requested date, and a Review action for pending items.

**Severity:** Critical

**Preconditions:**
- Mock `fetchApprovals({ per_page: '50' })` returns 2 requests:
  ```json
  {
    "items": [
      { "id": "apr-1", "agent_identity_id": "agent:dev-1", "capability_id": "cap-5", "server_id": "srv-3", "request_params": {}, "status": "pending", "approver_id": null, "requested_at": "2026-07-20T10:00:00Z", "resolved_at": null, "agent_name": "Dev Agent 1", "capability_name": "code:search", "server_name": "KB Server" },
      { "id": "apr-2", "agent_identity_id": "agent:sec-1", "capability_id": "cap-8", "server_id": "srv-5", "request_params": {}, "status": "approved", "approver_id": "admin@fabric", "requested_at": "2026-07-19T14:00:00Z", "resolved_at": "2026-07-19T16:00:00Z", "agent_name": "Security Scanner", "capability_name": "vulnerability:scan", "server_name": "Vuln Scanner" }
    ],
    "pagination": { "total": 2, "has_more": false, "per_page": 50 }
  }
  ```

**Test Steps:**
1. Render `<ApprovalsPage />`

**Expected Results:**
- Table headers: "Agent", "Capability", "Status", "Requested", "Actions"
- Row 1 ("Dev Agent 1", "code:search"): yellow Badge "pending", formatted date, and a "Review" button
- Row 2 ("Security Scanner", "vulnerability:scan"): green Badge "approved", formatted date, and no "Review" button (null rendered)
- "Review" button only rendered for rows where `status === 'pending'`

---

### TC-PAGE-022: Review side panel shows request details

**Description:** Clicking "Review" on a pending request opens a side panel overlay showing the agent name, capability name, server, and a note/reason textarea.

**Severity:** Critical

**Preconditions:**
- Mock `fetchApprovals()` returns 1 pending item (apr-1 from TC-PAGE-021)

**Test Steps:**
1. Render `<ApprovalsPage />`
2. Click the "Review" button on the pending row

**Expected Results:**
- An overlay (fixed inset-0 bg-black/50) appears with a white panel (max-w-lg)
- Panel title is "Review Approval Request"
- Details shown:
  - **Agent:** "Dev Agent 1"
  - **Capability:** "code:search"
  - **Server:** "KB Server"
- A textarea labeled "Note / Reason" is present for entering review notes
- Three footer buttons: "Close", "Deny" (bg-red-500), "Approve" (bg-green-500)

---

### TC-PAGE-023: Approve/Deny calls resolveApproval with correct status

**Description:** Clicking Approve or Deny in the review panel calls `resolveApproval()` with the request ID, the appropriate status, and the note text. Both mutations invalidate the approvals query on success.

**Severity:** Critical

**Preconditions:**
- Mock `fetchApprovals()` returns 1 pending item
- Mock `resolveApproval()` spies on arguments, resolves successfully

**Test Steps (Approve):**
1. Render `<ApprovalsPage />`
2. Click "Review" on the pending row
3. Type "Looks good, approved" in the Note textarea
4. Click the green "Approve" button

**Expected Results (Approve):**
- `resolveApproval()` is called with `("apr-1", "approved", "Looks good, approved")`
- Approve button is disabled while mutation is pending
- On success: panel closes, note clears, query invalidated, toast "Request approved" appears

**Test Steps (Deny):**
5. Reopen review on a pending row (re-fetch required)
6. Type "Missing required security review" in Note
7. Click the red "Deny" button

**Expected Results (Deny):**
- `resolveApproval()` is called with `("apr-1", "denied", "Missing required security review")`
- Deny button is disabled while mutation is pending
- On success: panel closes, note clears, query invalidated, toast "Request denied" appears

---

## 8. Packs

### TC-PAGE-024: Renders pack cards

**Description:** The Capability Packs page displays packs as card components showing the pack name, description, capability count, and an "Assign to class" button.

**Severity:** Critical

**Preconditions:**
- Mock `fetchPacks()` returns 2 packs:
  ```json
  [
    { "id": "pack-1", "name": "Development Tools", "description": "Code search, git, and deployment capabilities", "team_namespace": "team:platform", "capabilities": [{ "id": "cap-1", "name": "code:search" }, { "id": "cap-2", "name": "git:log" }] },
    { "id": "pack-2", "name": "Security Pack", "description": "Vulnerability scanning and dependency checks", "team_namespace": "team:security", "capabilities": [] }
  ]
  ```

**Test Steps:**
1. Render `<PacksPage />`
2. Inspect the pack cards

**Expected Results:**
- Page title is "Capability Packs"
- Two cards are rendered in a CSS grid (grid-cols-1 md:grid-cols-2 lg:grid-cols-3)
- Card 1 shows "Development Tools", "Code search, git, and deployment capabilities", "2 capabilities", and an "Assign to class" button
- Card 2 shows "Security Pack", "Vulnerability scanning and dependency checks", "0 capabilities", and an "Assign to class" button
- A "Create Pack" button is in the page header

---

### TC-PAGE-025: Create + assign flows

**Description:** The Packs page supports two modal flows: creating a new capability pack and assigning an existing pack to an agent class. Both use the `<Modal>` component and mutations.

**Severity:** Important

**Preconditions:**
- Mock `fetchPacks()` returns empty array
- Mock `fetchAgentClasses()` returns:
  ```json
  [
    { "id": "class-1", "name": "agent:developer", "description": "Developer agent", "team_namespace": "team:platform" },
    { "id": "class-2", "name": "agent:security", "description": "Security agent", "team_namespace": "team:security" }
  ]
  ```
- Mock `createPack()` resolves successfully
- Mock `assignPackToClass()` resolves successfully

**Test Steps (Create):**
1. Render `<PacksPage />`
2. Click "Create Pack"
3. Fill Name with "Observability Pack"
4. Fill Description with "Monitoring and logging capabilities"
5. Click Save (confirm button)

**Expected Results (Create):**
- Modal title is "Create Capability Pack"
- Confirm button disabled until Name is filled
- `createPack()` called with `{ name: "Observability Pack", description: "Monitoring and logging capabilities" }`
- On success: modal closes, form resets, query invalidated, toast "Pack created" appears

**Test Steps (Assign):**
6. After the pack is created and re-fetched, click "Assign to class" on a pack card
7. Verify the assign modal opens
8. Open the agent class dropdown and select "agent:security"
9. Click "Assign"

**Expected Results (Assign):**
- Modal title is "Assign to Agent Class"
- A `<select>` element with an empty default option "Select a class..." and options for "agent:developer" and "agent:security"
- Confirm button ("Assign") disabled until a class is selected
- On select of "agent:security" (value `class-2`): `assignPackToClass()` called with `(pack-1, "class-2")`
- On success: modal closes, `selectedClass` resets, query invalidated, toast "Pack assigned to class" appears

---

## 9. Alerts

### TC-PAGE-026: Renders alert table

**Description:** The Alerts page displays alert events in a table showing the alert message, rule name, fired time, and acknowledgement status (with an Acknowledge button for unacknowledged alerts).

**Severity:** Critical

**Preconditions:**
- Mock `fetchAlerts({ per_page: '50' })` returns 2 alerts:
  ```json
  {
    "items": [
      { "id": "alt-1", "rule_id": "rule-1", "message": "Server KB Server is unhealthy", "details": {}, "fired_at": "2026-07-24T06:00:00Z", "acknowledged_at": null, "acknowledged_by": null, "rule_name": "Health Check" },
      { "id": "alt-2", "rule_id": "rule-2", "message": "High rate of denied capability requests", "details": {}, "fired_at": "2026-07-24T05:00:00Z", "acknowledged_at": "2026-07-24T05:30:00Z", "acknowledged_by": "admin@fabric", "rule_name": "Denial Rate" }
    ],
    "pagination": { "total": 2, "has_more": false, "per_page": 50 }
  }
  ```

**Test Steps:**
1. Render `<AlertsPage />`
2. Inspect the table

**Expected Results:**
- Table headers: "Message", "Rule", "Fired", "Acknowledged"
- Row 1 ("Server KB Server is unhealthy", "Health Check"): formatted fired date, and an "Acknowledge" button (blue text)
- Row 2 ("High rate of denied capability requests", "Denial Rate"): formatted fired date, and a green "Yes" text (acknowledged_at is non-null)
- The "Acknowledge" button only appears for rows where `acknowledged_at` is null

---

### TC-PAGE-027: Acknowledge button calls API

**Description:** Clicking the "Acknowledge" button on an unacknowledged alert row calls `acknowledgeAlert()` with the alert ID, invalidates the alerts query, and shows a success toast.

**Severity:** Important

**Preconditions:**
- Mock `fetchAlerts()` returns 1 unacknowledged alert (alt-1 from TC-PAGE-026)
- Mock `acknowledgeAlert()` resolves successfully

**Test Steps:**
1. Render `<AlertsPage />`
2. Click the "Acknowledge" button on the first row

**Expected Results:**
- `acknowledgeAlert()` is called with `("alt-1")`
- On success: `queryClient.invalidateQueries({ queryKey: ['alerts'] })` is called
- Success toast "Alert acknowledged" appears
- After refetch with acknowledged data, the row now shows "Yes" instead of the Acknowledge button

---

## 10. AdminUsers

### TC-PAGE-028: Renders user table with role/status/MFA columns

**Description:** The Admin Users page displays a table of all admin users with their username, email, role (as colored Badge), status (as Badge), MFA status (Enabled/Disabled text), and a Deactivate action for active users other than the current user.

**Severity:** Critical

**Preconditions:**
- Set `useAuthStore` mock to return `{ user: { id: "user-1", username: "admin", role: "admin" } }`
- Mock `fetchAdminUsers()` returns 2 users:
  ```json
  [
    { "id": "user-1", "username": "admin", "email": "admin@fabric", "role": "admin", "team_namespace": "team:platform", "mfa_enabled": true, "status": "active", "created_at": "2026-06-01T00:00:00Z" },
    { "id": "user-2", "username": "jane", "email": "jane@fabric", "role": "editor", "team_namespace": "team:security", "mfa_enabled": false, "status": "active", "created_at": "2026-07-01T00:00:00Z" }
  ]
  ```

**Test Steps:**
1. Render `<AdminUsersPage />`
2. Inspect the table

**Expected Results:**
- Table headers: "Username", "Email", "Role", "Status", "MFA", "Actions"
- Row 1 ("admin", "admin@fabric"): purple Badge "admin", green Badge "active", "Enabled" in green text, no Deactivate button (current user, condition `row.original.id !== currentUser?.id` is false)
- Row 2 ("jane", "jane@fabric"): blue Badge "editor", green Badge "active", "Disabled" in gray text, a "Deactivate" button in red text
- The "Invite User" button is visible in the page header

---

### TC-PAGE-029: Invite modal submits

**Description:** Clicking "Invite User" opens a modal with username, email, and role fields. Submitting calls `inviteUser()` with the form data and invalidates the admin-users query.

**Severity:** Critical

**Preconditions:**
- Mock `inviteUser()` resolves successfully

**Test Steps:**
1. Render `<AdminUsersPage />`
2. Click "Invite User"
3. Fill Username with "bob"
4. Fill Email with "bob@fabric"
5. Select Role to "viewer"
6. Click "Send Invite"

**Expected Results:**
- Modal title is "Invite User"
- Role dropdown has 3 options: "Admin" (value admin), "Editor" (value editor), "Viewer" (value viewer)
- Confirm button label is "Send Invite"
- Confirm button disabled until Username and Email are filled
- `inviteUser()` is called with `{ username: "bob", email: "bob@fabric", role: "viewer" }`
- On success: modal closes, form resets to default role "editor", query invalidated, toast "User invited" appears

---

### TC-PAGE-030: Deactivate button hidden for current user

**Description:** The Deactivate button must be hidden for the currently logged-in user to prevent self-deactivation (which would lock the admin out of the system). It must still appear for other active users.

**Severity:** Critical

**Preconditions:**
- Set `useAuthStore` mock to return `{ user: { id: "user-1", username: "admin", role: "admin" } }`
- Mock `fetchAdminUsers()` returns:
  ```json
  [
    { "id": "user-1", "username": "admin", "email": "admin@fabric", "role": "admin", "team_namespace": "team:platform", "mfa_enabled": true, "status": "active", "created_at": "2026-06-01T00:00:00Z" },
    { "id": "user-2", "username": "jane", "email": "jane@fabric", "role": "editor", "team_namespace": "team:security", "mfa_enabled": false, "status": "active", "created_at": "2026-07-01T00:00:00Z" },
    { "id": "user-3", "username": "inactive-user", "email": "old@fabric", "role": "viewer", "team_namespace": "team:platform", "mfa_enabled": false, "status": "deactivated", "created_at": "2026-05-01T00:00:00Z" }
  ]
  ```

**Test Steps:**
1. Render `<AdminUsersPage />`
2. Inspect each row for Deactivate buttons

**Expected Results:**
- Row "admin" (id user-1, current user): **No** Deactivate button — condition `row.original.status === 'active' && row.original.id !== currentUser?.id` evaluates to false (same ID)
- Row "jane" (id user-2, different user, active): **Has** Deactivate button — condition evaluates to true
- Row "inactive-user" (id user-3, different user, deactivated): **No** Deactivate button — condition false because status is not 'active'
- If Deactivate is clicked on "jane", `deactivateUser("user-2")` is called, query invalidated, toast "User deactivated" appears

---

## 11. TrustPosture

### TC-PAGE-031: Renders server cards with trust-colored border

**Description:** The Trust Posture page displays server cards with a left border color that visually conveys the server's trust level: green for trusted, yellow for restricted, orange for approval-gated, and red for unreviewed.

**Severity:** Critical

**Preconditions:**
- Mock `fetchServers({ per_page: '200' })` returns 4 servers, one per trust level:
  ```json
  {
    "items": [
      { "id": "srv-1", "name": "KB Server", "endpoint": "http://localhost:3001", "owner_team": "team:platform", "labels": [], "health_status": "healthy", "trust_level": "trusted", "team_namespace": "team:platform", "created_at": "2026-07-01T00:00:00Z", "decommissioned_at": null },
      { "id": "srv-2", "name": "Deployment API", "endpoint": "http://localhost:3002", "owner_team": "team:platform", "labels": [], "health_status": "healthy", "trust_level": "restricted", "team_namespace": "team:platform", "created_at": "2026-07-01T00:00:00Z", "decommissioned_at": null },
      { "id": "srv-3", "name": "Vuln Scanner", "endpoint": "http://localhost:3003", "owner_team": "team:security", "labels": [], "health_status": "degraded", "trust_level": "approval-gated", "team_namespace": "team:security", "created_at": "2026-07-01T00:00:00Z", "decommissioned_at": null },
      { "id": "srv-4", "name": "New Server", "endpoint": "http://localhost:3004", "owner_team": "team:data", "labels": [], "health_status": "unhealthy", "trust_level": "unreviewed", "team_namespace": "team:data", "created_at": "2026-07-01T00:00:00Z", "decommissioned_at": null }
    ],
    "pagination": { "total": 4, "has_more": false, "per_page": 200 }
  }
  ```
- Mock `fetchAgentClasses()` returns empty array

**Test Steps:**
1. Render `<TrustPosturePage />`
2. Inspect each server card

**Expected Results:**
- Page title is "Trust Posture"
- Four server cards rendered in a CSS grid
- Card 1 (KB Server): `border-green-500 bg-green-50` classes, Badge label "trusted"
- Card 2 (Deployment API): `border-yellow-500 bg-yellow-50` classes, Badge label "restricted"
- Card 3 (Vuln Scanner): `border-orange-500 bg-orange-50` classes, Badge label "approval-gated"
- Card 4 (New Server): `border-red-500 bg-red-100` classes, Badge label "unreviewed"
- Each card shows server name, endpoint, health Badge, owner team, and a trust level dropdown
- The "unreviewed" card shows "⚠ Needs review" text in red (conditionally rendered)

---

### TC-PAGE-032: Agent class selector fetches and displays classes

**Description:** The agent class dropdown in the Trust Posture header is populated by the `fetchAgentClasses()` query and displays a list of available classes. The dropdown is wrapped in `<PageState>` so it shows loading/error states independently.

**Severity:** Important

**Preconditions:**
- Mock `fetchServers()` returns 1 server
- Mock `fetchAgentClasses()` returns:
  ```json
  [
    { "id": "class-1", "name": "agent:developer", "description": "Developer agent", "team_namespace": "team:platform" },
    { "id": "class-2", "name": "agent:security", "description": "Security agent", "team_namespace": "team:security" }
  ]
  ```
- Agent classes query starts in loading state

**Test Steps:**
1. Render `<TrustPosturePage />` with classes query in loading state
2. Update classes query to populated state

**Expected Results:**
- During loading: the dropdown area shows a pulsing skeleton (LoadingState)
- After loading completes:
  - A `<select>` element with label "Agent Class:" is visible
  - Dropdown has 3 options: "Select a class..." (default empty value), "agent:developer" (value class-1), "agent:security" (value class-2)
  - The select has focus styles: `focus:outline-none focus:ring-2 focus:ring-blue-500`

---

### TC-PAGE-033: Trust level change on dropdown fires mutation with selected class ID

**Description:** When the user selects a new trust level from a server's dropdown AND an agent class is selected, the `setTrustAssignment()` mutation is called with the correct parameters (class ID, server ID, trust level).

**Severity:** Critical

**Preconditions:**
- Mock `fetchServers()` returns 1 server (srv-1, trust_level "unreviewed")
- Mock `fetchAgentClasses()` returns 1 class (class-1, "agent:developer")
- Mock `setTrustAssignment()` resolves successfully

**Test Steps:**
1. Render `<TrustPosturePage />`
2. Wait for data to load
3. Select "agent:developer" from the agent class dropdown
4. Change the trust level dropdown on the KB Server card from "Unreviewed" to "Trusted"

**Expected Results:**
- `setTrustAssignment()` is called with `{ agentClassId: "class-1", serverId: "srv-1", trustLevel: "trusted" }`
- The actual argument sent to the API is: `setTrustAssignment("class-1", "srv-1", "trusted")`

---

### TC-PAGE-034: No mutation when no class selected (no-op guard)

**Description:** Changing a server's trust level dropdown when no agent class is selected (empty string) must NOT fire any mutation. This is a no-op guard that prevents partial state updates.

**Severity:** Important

**Preconditions:**
- Mock `fetchServers()` returns 1 server (srv-1)
- Mock `fetchAgentClasses()` returns 1 class
- `selectedClassId` starts as empty string (default)

**Test Steps:**
1. Render `<TrustPosturePage />`
2. Wait for data to load
3. DO NOT select an agent class (keep default "Select a class...")
4. Change the trust level dropdown on the KB Server card from "unreviewed" to "restricted"

**Expected Results:**
- `setTrustAssignment()` is NOT called (the onChange handler has a guard: `if (selectedClassId)` before calling `updateTrust.mutate()`)
- The dropdown value changes visually (controlled by `pendingChanges[server.id] ?? server.trust_level`) but no API call is made

---

### TC-PAGE-035: Optimistic: dropdown shows new value immediately via pendingChanges state

**Description:** When the trust level is changed, `onMutate` optimistically updates `pendingChanges` state so the dropdown shows the new value immediately without waiting for the API response. This provides instant UI feedback.

**Severity:** Important

**Preconditions:**
- Mock `fetchServers()` returns 1 server (srv-1, trust_level "unreviewed")
- Mock `fetchAgentClasses()` returns 1 class
- Mock `setTrustAssignment()` is slow (delays resolution by 500ms)

**Test Steps:**
1. Render `<TrustPosturePage />`
2. Select "agent:developer" from the agent class dropdown
3. Change trust level to "Trusted"
4. Immediately inspect the dropdown value (before the API resolves)

**Expected Results:**
- The dropdown value is "Trusted" immediately after selection (reads from `pendingChanges`)
- The value does NOT wait for the API response
- `onMutate` is called before the mutation function, setting `pendingChanges["srv-1"] = "trusted"`
- After API resolves successfully in `onSuccess`: `pendingChanges` is cleared (`setPendingChanges({})`)

---

### TC-PAGE-036: Rollback: mutation error reverts dropdown to original value

**Description:** When `setTrustAssignment()` fails, the `onError` handler removes the server's entry from `pendingChanges`, causing the dropdown to revert to the original `server.trust_level` value from the query data.

**Severity:** Critical

**Preconditions:**
- Mock `fetchServers()` returns 1 server (srv-1, trust_level "unreviewed")
- Mock `fetchAgentClasses()` returns 1 class
- Mock `setTrustAssignment()` rejects with new Error("Agent class not authorized for this trust level")

**Test Steps:**
1. Render `<TrustPosturePage />`
2. Select "agent:developer" from the agent class dropdown
3. Change trust level to "Trusted"
4. Observe optimistic dropdown shows "Trusted"
5. Wait for the mutation to fail
6. Observe the dropdown after error

**Expected Results:**
- **Step 4:** Dropdown shows "Trusted" (optimistic update via `pendingChanges`)
- **Step 6:** After the error:
  - Dropdown reverts to "Unreviewed" (original value from `server.trust_level`)
  - `pendingChanges` state no longer has an entry for "srv-1" (deleted in `onError`)
  - Error toast appears: "Agent class not authorized for this trust level"
  - The `invalidateQueries` call in `onSuccess` is NOT executed (only in success path)
  - The `onError` handler specifically deletes only the failed server's pending change (`delete next[serverId]`), leaving other pending changes intact

---

## Summary

| Prefix | Page | Test Count |
|---|---|---|
| TC-PAGE-001 to 003 | Dashboard | 3 |
| TC-PAGE-004 to 007 | Servers | 4 |
| TC-PAGE-008 to 011 | Capabilities | 4 |
| TC-PAGE-012 to 014 | AgentClasses | 3 |
| TC-PAGE-015 to 017 | Policies | 3 |
| TC-PAGE-018 to 020 | Audit | 3 |
| TC-PAGE-021 to 023 | Approvals | 3 |
| TC-PAGE-024 to 025 | Packs | 2 |
| TC-PAGE-026 to 027 | Alerts | 2 |
| TC-PAGE-028 to 030 | AdminUsers | 3 |
| TC-PAGE-031 to 036 | TrustPosture | 6 |
| (skipped) | Login | (covered in Auth/Session) |
| **Total** | | **36** |
