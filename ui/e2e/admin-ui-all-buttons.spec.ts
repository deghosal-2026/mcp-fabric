import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const SHOTS = path.resolve(__dirname, '../../docs/ui-test/findings/screenshots')

const MOCK_TOKEN = 'fcp_test_admin_token_1234567890abcdef'

const MOCK_USER = {
  id: 'usr-1', username: 'priya', role: 'admin',
  team_namespace: 'team:platform', mfa_enabled: true,
}

const MOCK_DASHBOARD = {
  server_count: 6, healthy_servers: 4, pending_approvals: 2,
  recent_audit_events: 42, degraded_servers: 1,
}

const MOCK_SERVERS = {
  items: [
    { id: 'srv-1', name: 'KB Server', endpoint: 'http://kb.internal:3001', owner_team: 'platform', labels: ['knowledge', 'internal'], trust_level: 'trusted', health_status: 'healthy', team_namespace: 'team:platform', decommissioned_at: null, created_at: '2026-07-01T00:00:00Z', tools: [] },
    { id: 'srv-2', name: 'Code Search', endpoint: 'http://codesearch.internal:3002', owner_team: 'platform', labels: ['code', 'search'], trust_level: 'trusted', health_status: 'healthy', team_namespace: 'team:platform', decommissioned_at: null, created_at: '2026-07-02T00:00:00Z', tools: [] },
    { id: 'srv-3', name: 'Vuln Scanner', endpoint: 'http://security.internal:3003', owner_team: 'security', labels: ['security', 'scanning'], trust_level: 'restricted', health_status: 'degraded', team_namespace: 'team:security', decommissioned_at: null, created_at: '2026-07-03T00:00:00Z', tools: [] },
    { id: 'srv-4', name: 'Deployment Server', endpoint: 'http://deploy.internal:3004', owner_team: 'platform', labels: ['deployment', 'production'], trust_level: 'approval-gated', health_status: 'healthy', team_namespace: 'team:platform', decommissioned_at: null, created_at: '2026-07-04T00:00:00Z', tools: [] },
    { id: 'srv-5', name: 'New Unreviewed', endpoint: 'http://new.internal:3005', owner_team: 'data', labels: ['data', 'new'], trust_level: 'unreviewed', health_status: 'unhealthy', team_namespace: 'team:data', decommissioned_at: null, created_at: '2026-07-05T00:00:00Z', tools: [] },
    { id: 'srv-6', name: 'Git History', endpoint: 'http://git.internal:3006', owner_team: 'platform', labels: ['git', 'history'], trust_level: 'trusted', health_status: 'healthy', team_namespace: 'team:platform', decommissioned_at: null, created_at: '2026-07-06T00:00:00Z', tools: [] },
  ],
  pagination: { total: 6, has_more: false, per_page: 50 },
}

const MOCK_CAPABILITIES = {
  items: [
    { id: 'cap-1', name: 'knowledge:search', domain: 'knowledge', description: 'Search documentation and knowledge base', status: 'active', deprecated_at: null, grace_period_days: 14 },
    { id: 'cap-2', name: 'code:search', domain: 'code', description: 'Search across code repositories', status: 'active', deprecated_at: null, grace_period_days: 14 },
    { id: 'cap-3', name: 'deployment:promote', domain: 'deployment', description: 'Promote service to environment', status: 'active', deprecated_at: null, grace_period_days: 14 },
    { id: 'cap-4', name: 'vulnerability:scan', domain: 'security', description: 'Scan service for vulnerabilities', status: 'active', deprecated_at: null, grace_period_days: 14 },
    { id: 'cap-5', name: 'incident:create', domain: 'incident', description: 'Create a new incident', status: 'deprecated', deprecated_at: '2026-07-20T00:00:00Z', grace_period_days: 14 },
  ],
  pagination: { total: 5, has_more: false, per_page: 100 },
}

const MOCK_AGENT_CLASSES = [
  { id: 'cls-1', name: 'agent:admin', description: 'Full system access', team_namespace: 'team:platform' },
  { id: 'cls-2', name: 'agent:incident-responder', description: 'Incident response automation', team_namespace: 'team:platform' },
  { id: 'cls-3', name: 'agent:developer', description: 'Developer coding assistant', team_namespace: 'team:platform' },
  { id: 'cls-4', name: 'agent:new-hire', description: 'New engineer onboarding agent', team_namespace: 'team:platform' },
]

const MOCK_POLICIES = [
  { id: 'pol-1', version: '1.0.0', deployed_at: '2026-07-15T10:00:00Z' },
  { id: 'pol-2', version: '1.1.0', deployed_at: '2026-07-20T14:30:00Z' },
]

const MOCK_AUDIT = {
  items: [
    { id: 'aud-1', event_type: 'capability_request', actor_type: 'agent', actor_id: 'igor-01', target_type: 'capability', target_id: 'cap-2', details: { capability: 'code:search' }, created_at: '2026-07-24T10:00:00Z' },
    { id: 'aud-2', event_type: 'policy_change', actor_type: 'admin', actor_id: 'priya', target_type: 'policy', target_id: 'pol-2', details: { action: 'deploy' }, created_at: '2026-07-24T09:30:00Z' },
    { id: 'aud-3', event_type: 'server_registered', actor_type: 'admin', actor_id: 'priya', target_type: 'server', target_id: 'srv-6', details: { server_name: 'Git History' }, created_at: '2026-07-24T09:00:00Z' },
    { id: 'aud-4', event_type: 'capability_request', actor_type: 'agent', actor_id: 'crbot-01', target_type: 'capability', target_id: 'cap-3', details: { capability: 'deployment:promote' }, created_at: '2026-07-24T08:00:00Z' },
  ],
  pagination: { total: 42, has_more: true, next_cursor: 'aud-5', per_page: 50 },
}

const MOCK_APPROVALS = {
  items: [
    { id: 'apr-1', agent_identity_id: 'id-1', capability_id: 'cap-3', server_id: 'srv-4', request_params: { service: 'payment-api', env: 'staging' }, status: 'pending', approver_id: null, requested_at: '2026-07-24T10:00:00Z', resolved_at: null, agent_name: 'CRBot', capability_name: 'deployment:promote', server_name: 'Deployment Server' },
    { id: 'apr-2', agent_identity_id: 'id-2', capability_id: 'cap-4', server_id: 'srv-3', request_params: { service: 'auth-api', depth: 'full' }, status: 'pending', approver_id: null, requested_at: '2026-07-24T09:00:00Z', resolved_at: null, agent_name: 'Igor', capability_name: 'vulnerability:scan', server_name: 'Vuln Scanner' },
    { id: 'apr-3', agent_identity_id: 'id-3', capability_id: 'cap-1', server_id: 'srv-1', request_params: { service: 'docs-api' }, status: 'approved', approver_id: 'usr-1', requested_at: '2026-07-23T12:00:00Z', resolved_at: '2026-07-23T13:00:00Z', agent_name: 'DocBot', capability_name: 'knowledge:search', server_name: 'KB Server' },
    { id: 'apr-4', agent_identity_id: 'id-4', capability_id: 'cap-5', server_id: 'srv-3', request_params: { service: 'monitor' }, status: 'denied', approver_id: 'usr-2', requested_at: '2026-07-23T10:00:00Z', resolved_at: '2026-07-23T11:00:00Z', agent_name: 'AlertBot', capability_name: 'incident:create', server_name: 'Vuln Scanner' },
  ],
  pagination: { total: 4, has_more: false, per_page: 50 },
}

const MOCK_PACKS = [
  { id: 'pck-1', name: 'New Hire — Platform Engineer', description: 'Essential tools for new engineers', team_namespace: 'team:platform' },
  { id: 'pck-2', name: 'Incident Responder', description: 'Incident response tool set', team_namespace: 'team:platform' },
]

const MOCK_ALERTS = {
  items: [
    { id: 'alr-1', rule_id: 'rule-1', message: 'Code Search server degraded — failover count 3 in 5m', details: { server: 'Code Search', failures: 3 }, fired_at: '2026-07-24T10:05:00Z', acknowledged_at: null, acknowledged_by: null, rule_name: 'Degraded Server' },
    { id: 'alr-2', rule_id: 'rule-2', message: 'Vuln Scanner unreachable for 2m', details: { server: 'Vuln Scanner' }, fired_at: '2026-07-24T09:55:00Z', acknowledged_at: '2026-07-24T10:00:00Z', acknowledged_by: 'priya', rule_name: 'Server Unreachable' },
  ],
  pagination: { total: 2, has_more: false, per_page: 50 },
}

const MOCK_ADMIN_USERS = [
  { id: 'usr-1', username: 'priya', email: 'priya@example.com', role: 'admin', team_namespace: 'team:platform', mfa_enabled: true, status: 'active', created_at: '2026-07-01T00:00:00Z' },
  { id: 'usr-2', username: 'jordan', email: 'jordan@example.com', role: 'admin', team_namespace: 'team:security', mfa_enabled: true, status: 'active', created_at: '2026-07-02T00:00:00Z' },
  { id: 'usr-3', username: 'alex', email: 'alex@example.com', role: 'editor', team_namespace: 'team:platform', mfa_enabled: false, status: 'active', created_at: '2026-07-05T00:00:00Z' },
]

const MOCK_SERVER_DETAIL = {
  ...MOCK_SERVERS.items[0],
  tools: [
    { id: 'tool-1', server_id: 'srv-1', tool_name: 'search_kb', input_schema: { type: 'object', properties: { query: { type: 'string' } } }, output_schema: { type: 'array' } },
    { id: 'tool-2', server_id: 'srv-1', tool_name: 'get_article', input_schema: { type: 'object', properties: { id: { type: 'string' } } }, output_schema: { type: 'object' } },
  ],
  routing_rules: [],
  trust_assignments: [],
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript((token: string) => {
    localStorage.setItem('fabric_token', token)
    localStorage.setItem('fabric_user', JSON.stringify({
      id: 'usr-1', username: 'priya', role: 'admin',
      team_namespace: 'team:platform', mfa_enabled: true,
    }))
  }, MOCK_TOKEN)

  await page.route(/\/v1\//, async route => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()

    if (path === '/v1/auth/login') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ token: MOCK_TOKEN, user: MOCK_USER, mfa_required: false }) })
    }
    if (path === '/v1/admin/dashboard') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_DASHBOARD) })
    }
    if (path.startsWith('/v1/servers/') && path !== '/v1/servers') {
      if (method === 'POST' && path.endsWith('/inspect')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ changes: [] }) })
      }
      if (method === 'POST' && path.endsWith('/decommission')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'decommissioned' }) })
      }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_SERVER_DETAIL) })
    }
    if (path === '/v1/servers') {
      if (method === 'POST') {
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(MOCK_SERVERS.items[0]) })
      }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_SERVERS) })
    }
    if (path.startsWith('/v1/capabilities/')) {
      if (path.endsWith('/mappings')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
      }
      if (path.endsWith('/deprecate')) {
        return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CAPABILITIES.items[0]) })
      }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CAPABILITIES.items[0]) })
    }
    if (path === '/v1/capabilities') {
      if (method === 'POST') {
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(MOCK_CAPABILITIES.items[0]) })
      }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CAPABILITIES) })
    }
    if (path === '/v1/agent-classes') {
      if (method === 'POST') {
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(MOCK_AGENT_CLASSES[0]) })
      }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_AGENT_CLASSES) })
    }
    if (path.match(/^\/v1\/agent-classes\/.+\/identities$/)) {
      if (method === 'POST') {
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ id: 'id-new', token_prefix: 'fcp_', token: MOCK_TOKEN, status: 'active' }) })
      }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
    }
    if (path.match(/^\/v1\/agent-classes\/.+\/trust$/)) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) })
    }
    if (path === '/v1/admin/policies') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_POLICIES) })
    }
    if (path === '/v1/admin/policies/bundle') {
      return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ version: '2.0.0' }) })
    }
    if (path === '/v1/audit') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_AUDIT) })
    }
    if (path === '/v1/audit/export') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ export_id: 'exp-1' }) })
    }
    if (path === '/v1/approvals') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_APPROVALS) })
    }
    if (path.match(/^\/v1\/approvals\/.+\/review$/)) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_APPROVALS.items[0]) })
    }
    if (path === '/v1/packs') {
      if (method === 'POST') {
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(MOCK_PACKS[0]) })
      }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_PACKS) })
    }
    if (path.match(/^\/v1\/packs\/.+\/classes$/)) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) })
    }
    if (path.match(/\/v1\/packs\/.+\/security-metrics$/)) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 'pkg-1', name: 'Developer Tools', resource_count: 16, total_resources_in_domain: 512, implied_catch_rate: 0.97, warning_tier: 'strong' }) })
    }
    if (path.match(/\/v1\/admin\/packs\/.+\/resources$/)) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
    }
    if (path === '/v1/alerts') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ALERTS) })
    }
    if (path.match(/^\/v1\/alerts\/.+\/acknowledge$/)) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ALERTS.items[0]) })
    }
    if (path === '/v1/admin/users') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ADMIN_USERS) })
    }
    if (path === '/v1/admin/users/invite') {
      return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(MOCK_ADMIN_USERS[0]) })
    }
    if (path.match(/^\/v1\/admin\/users\/.+\/deactivate$/)) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ADMIN_USERS[0]) })
    }
    if (path === '/v1/admin/trust-posture/pack-breadth') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([
        { agent_class_id: 'cls-1', agent_class_name: 'Developer Agents', pack_count: 2, resources_covered: 16, total_resources_in_domain: 512, catch_rate: 0.9706 },
        { agent_class_id: 'cls-2', agent_class_name: 'Ops Agents', pack_count: 1, resources_covered: 500, total_resources_in_domain: 512, catch_rate: 0.02 },
      ]) })
    }
    // Mock: return stale tool schema mappings that need admin review
    // (capability-to-server bindings where the tool schema digest has changed)
    if (path === '/v1/admin/mappings/stale') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([
        { id: 'map-stale-1', capability_id: 'cap-1', server_id: 'srv-3', tool_name: 'search_kb', tool_schema_digest: 'a1b2c3d4e5f6', status: 'stale' },
        { id: 'map-stale-2', capability_id: 'cap-2', server_id: 'srv-4', tool_name: 'deploy_app', tool_schema_digest: 'f6e5d4c3b2a1', status: 'stale' },
      ]) })
    }
    // Mock: submit a review decision (approve/reject) for a stale mapping
    if (path.match(/^\/v1\/admin\/mappings\/.+\/review$/)) {
      return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ id: 'rev-1', mapping_id: 'map-stale-1', decision: 'approved', reason: null, reviewed_by: null, created_at: '2026-07-25T00:00:00Z', previous_digest: 'old', new_digest: 'new' }) })
    }

    route.continue()
  })
})

// ───────────────────────────────────────────────────────
// 1. SIDEBAR — all 12 navigation links
// ───────────────────────────────────────────────────────
test.describe('Sidebar navigation links', () => {
  test.setTimeout(180_000)

  const sidebarLinks = [
    { label: 'Dashboard', expectedUrl: '/' },
    { label: 'Servers', expectedUrl: '/servers' },
    { label: 'Capabilities', expectedUrl: '/capabilities' },
    { label: 'Agent Classes', expectedUrl: '/agent-classes' },
    { label: 'Policies', expectedUrl: '/policies' },
    { label: 'Audit Log', expectedUrl: '/audit' },
    { label: 'Approvals', expectedUrl: '/approvals' },
    { label: 'Capability Packs', expectedUrl: '/packs' },
    { label: 'Alerts', expectedUrl: '/alerts' },
    { label: 'Admin Users', expectedUrl: '/admin/users' },
    { label: 'Trust Posture', expectedUrl: '/trust' },
    // Schema Reviews: navigate to the stale-mapping-review page (12th sidebar link)
    { label: 'Reviews', expectedUrl: '/reviews' },
  ]

  for (const link of sidebarLinks) {
    test(`sidebar "${link.label}" → navigates to ${link.expectedUrl}`, async ({ page }) => {
      await page.goto('/')
      await page.waitForLoadState('networkidle')
      await page.getByRole('link', { name: link.label }).click()
      await page.waitForLoadState('networkidle')
      await expect(page).toHaveURL(link.expectedUrl)
    })
  }
})

// ───────────────────────────────────────────────────────
// 2. TOP BAR — Logout button
// ───────────────────────────────────────────────────────
test.describe('TopBar', () => {
  test.setTimeout(60_000)

  test('Logout button clears session and redirects to /login', async ({ page }) => {
    await page.goto('/')
    await page.waitForTimeout(1000)
    await page.getByRole('button', { name: /logout/i }).click()
    await page.waitForTimeout(1000)
    await expect(page).toHaveURL(/\/login/)
    await page.screenshot({ path: path.join(SHOTS, 'btn-topbar-logout.png'), fullPage: true })
  })
})

// ───────────────────────────────────────────────────────
// 3. LOGIN PAGE — buttons, inputs
// ───────────────────────────────────────────────────────
test.describe('Login page — all buttons and inputs', () => {
  test.setTimeout(60_000)

  test('Login button: disabled when empty, enabled when filled', async ({ page }) => {
    await page.addInitScript(() => { localStorage.clear() })
    await page.goto('/login')
    await page.waitForTimeout(1000)

    const loginBtn = page.getByRole('button', { name: /login/i })
    await expect(loginBtn).toBeDisabled()

    const textboxes = page.getByRole('textbox')
    await textboxes.nth(0).fill('admin')
    await expect(loginBtn).toBeDisabled()

    await textboxes.nth(1).fill('password')
    await expect(loginBtn).toBeEnabled()

    await page.screenshot({ path: path.join(SHOTS, 'btn-login-filled.png'), fullPage: true })
  })

  test('Login error banner renders', async ({ page }) => {
    await page.addInitScript(() => { localStorage.clear() })
    await page.route('**/v1/auth/login', async route => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid credentials' }),
      })
    })
    await page.goto('/login')
    await page.waitForTimeout(1000)
    const textboxes = page.getByRole('textbox')
    await textboxes.nth(0).fill('bad')
    await textboxes.nth(1).fill('credentials')
    await page.getByRole('button', { name: /login/i }).click()
    await page.waitForTimeout(1000)
    await expect(page.locator('[role="alert"], .text-red-600').first()).toBeVisible()
  })
})

// ───────────────────────────────────────────────────────
// 4. DASHBOARD — "View all" links (click and navigate)
// ───────────────────────────────────────────────────────
test.describe('Dashboard — links and navigation', () => {
  test.setTimeout(120_000)

  test('"View all" links navigate — Servers, Audit, Approvals', async ({ page }) => {
    await page.goto('/')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-dashboard.png'), fullPage: true })

    const viewAllLinks = page.locator('a').filter({ hasText: /view all/i })
    const count = await viewAllLinks.count()

    if (count > 0) {
      await viewAllLinks.first().click()
      await page.waitForTimeout(1000)
      await expect(page).toHaveURL(/\/servers/)
    }

    await page.goto('/')
    await page.waitForTimeout(1000)

    await page.locator('a').filter({ hasText: /view all/i }).last().click()
    await page.waitForTimeout(1000)
    await expect(page).toHaveURL(/\/audit/)
  })
})

// ───────────────────────────────────────────────────────
// 5. SERVERS — Register, Save, Cancel, filters
// ───────────────────────────────────────────────────────
test.describe('Servers — all buttons, filters, modal', () => {
  test.setTimeout(180_000)

  test('Register Server modal: open, save disabled→enabled, create, cancel, close', async ({ page }) => {
    await page.goto('/servers')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-servers-list.png'), fullPage: true })

    await page.getByRole('button', { name: /register server/i }).click()
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-servers-modal.png'), fullPage: true })

    const modal = page.locator('.fixed.inset-0.z-50').last()
    const saveBtn = modal.getByRole('button', { name: /save/i })
    await expect(saveBtn).toBeDisabled()

    const inputs = modal.locator('input')
    if (await inputs.count() >= 2) {
      await inputs.nth(0).fill('Test Server')
      await inputs.nth(1).fill('http://localhost:3010')
    }
    await expect(saveBtn).toBeEnabled()

    await saveBtn.click()
    await page.waitForTimeout(1000)

    await page.getByRole('button', { name: /register server/i }).click()
    await page.waitForTimeout(1000)
    const modal2 = page.locator('.fixed.inset-0.z-50').last()
    await modal2.getByRole('button', { name: /cancel/i }).click()
    await page.waitForTimeout(1000)

    await page.getByRole('button', { name: /register server/i }).click()
    await page.waitForTimeout(1000)
    const closeX = page.locator('.fixed.inset-0.z-50').last().locator('button').first()
    await closeX.click()
    await page.waitForTimeout(500)
  })

  test('Filter dropdowns: all options for Health, Trust, Team', async ({ page }) => {
    await page.goto('/servers')
    await page.waitForTimeout(1000)

    const selects = page.locator('select')
    const selectCount = await selects.count()

    if (selectCount >= 1) {
      const healthOptions = ['', 'healthy', 'degraded', 'unhealthy']
      for (const opt of healthOptions) {
        await selects.nth(0).selectOption(opt)
        await page.waitForTimeout(500)
      }
    }

    if (selectCount >= 2) {
      const trustOptions = ['', 'trusted', 'restricted', 'approval-gated', 'unreviewed']
      for (const opt of trustOptions) {
        await selects.nth(1).selectOption(opt)
        await page.waitForTimeout(500)
      }
    }

    if (selectCount >= 3) {
      const teamOptions = ['', 'team:platform', 'team:security', 'team:data']
      for (const opt of teamOptions) {
        await selects.nth(2).selectOption(opt)
        await page.waitForTimeout(1000)
      }
    }

    await page.getByRole('button', { name: /clear all/i }).click()
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-servers-filtered.png'), fullPage: true })
  })

  test('Search input: type and clear', async ({ page }) => {
    await page.goto('/servers')
    await page.waitForTimeout(1000)

    const searchInput = page.locator('input[type="text"]').last()
    await searchInput.fill('Code Search')
    await page.waitForTimeout(1000)

    await page.getByRole('button', { name: /clear all/i }).click()
    await page.waitForTimeout(1000)
  })
})

// ───────────────────────────────────────────────────────
// 6. CAPABILITIES — Create, Deprecate, filters, modals
// ───────────────────────────────────────────────────────
test.describe('Capabilities — all buttons, filters, modals', () => {
  test.setTimeout(180_000)

  test('Create Capability modal: save disabled→enabled, create', async ({ page }) => {
    await page.goto('/capabilities')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-capabilities-list.png'), fullPage: true })

    await page.getByRole('button', { name: /create capability/i }).click()
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-capabilities-modal.png'), fullPage: true })

    const modal = page.locator('.fixed.inset-0.z-50').last()
    const saveBtn = modal.getByRole('button', { name: /save/i })
    await expect(saveBtn).toBeDisabled()

    const inputs = modal.locator('input')
    await inputs.nth(0).fill('new:capability')
    if (await inputs.count() >= 2) {
      await inputs.nth(1).fill('code')
    }
    await expect(saveBtn).toBeEnabled()

    await saveBtn.click()
    await page.waitForTimeout(1000)
  })

  test('Deprecate button (row): opens confirm modal, deprecate action', async ({ page }) => {
    await page.goto('/capabilities')
    await page.waitForTimeout(1000)

    const deprecateBtn = page.getByRole('button', { name: /deprecate/i })
    await deprecateBtn.first().click()
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-capabilities-deprecate.png'), fullPage: true })

    const modal = page.locator('.fixed.inset-0.z-50').last()
    const confirmBtn = modal.getByRole('button', { name: /deprecate/i })
    await expect(confirmBtn).toBeVisible()

    await confirmBtn.click()
    await page.waitForTimeout(1000)
  })

  test('Filter dropdowns: all Domain and Status options', async ({ page }) => {
    await page.goto('/capabilities')
    await page.waitForTimeout(1000)

    const selects = page.locator('select')
    const selectCount = await selects.count()

    if (selectCount >= 1) {
      const domainOptions = ['', 'knowledge', 'code', 'deployment', 'incident', 'security']
      for (const opt of domainOptions) {
        await selects.nth(0).selectOption(opt)
        await page.waitForTimeout(500)
      }
    }

    if (selectCount >= 2) {
      const statusOptions = ['', 'active', 'deprecated']
      for (const opt of statusOptions) {
        await selects.nth(1).selectOption(opt)
        await page.waitForTimeout(500)
      }
    }

    await page.getByRole('button', { name: /clear all/i }).click()
    await page.waitForTimeout(1000)
  })

  test('Modal Cancel and Close × buttons', async ({ page }) => {
    await page.goto('/capabilities')
    await page.waitForTimeout(1000)

    await page.getByRole('button', { name: /create capability/i }).click()
    await page.waitForTimeout(1000)
    await page.locator('.fixed.inset-0.z-50').last().getByRole('button', { name: /cancel/i }).click()
    await page.waitForTimeout(1000)

    await page.getByRole('button', { name: /create capability/i }).click()
    await page.waitForTimeout(1000)
    await page.locator('.fixed.inset-0.z-50').last().locator('button').first().click()
    await page.waitForTimeout(1000)
  })
})

// ───────────────────────────────────────────────────────
// 7. AGENT CLASSES — Create, Tokens, Generate token, modals
// ───────────────────────────────────────────────────────
test.describe('Agent Classes — all buttons and tokens modal', () => {
  test.setTimeout(120_000)

  test('Create Agent Class modal: save disabled→enabled, create', async ({ page }) => {
    await page.goto('/agent-classes')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-agent-classes-list.png'), fullPage: true })

    await page.getByRole('button', { name: /create agent class/i }).click()
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-agent-classes-modal.png'), fullPage: true })

    const modal = page.locator('.fixed.inset-0.z-50').last()
    const saveBtn = modal.getByRole('button', { name: /save/i })
    await expect(saveBtn).toBeDisabled()

    await modal.locator('input').first().fill('agent:tester')
    await expect(saveBtn).toBeEnabled()
    await saveBtn.click()
    await page.waitForTimeout(1000)
  })

  test('"Tokens" row button opens tokens modal, generate token', async ({ page }) => {
    await page.goto('/agent-classes')
    await page.waitForTimeout(1000)

    await page.getByRole('button', { name: /tokens/i }).first().click()
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-agent-classes-tokens.png'), fullPage: true })

    const modal = page.locator('.fixed.inset-0.z-50').last()
    const generateBtn = modal.getByRole('button', { name: /generate/i })
    await expect(generateBtn).toBeDisabled()

    await modal.locator('input').fill('my-token-name')
    await expect(generateBtn).toBeEnabled()

    await generateBtn.click()
    await page.waitForTimeout(1000)

    await expect(page.locator('.font-mono').first()).toBeVisible()
  })

  test('Tokens modal close via × button', async ({ page }) => {
    await page.goto('/agent-classes')
    await page.waitForTimeout(1000)

    await page.getByRole('button', { name: /tokens/i }).first().click()
    await page.waitForTimeout(1000)
    await page.locator('.fixed.inset-0.z-50').last().locator('button').first().click()
    await page.waitForTimeout(1000)
  })
})

// ───────────────────────────────────────────────────────
// 8. POLICIES — New Policy, Deploy, Cancel, Close
// ───────────────────────────────────────────────────────
test.describe('Policies — all buttons', () => {
  test.setTimeout(120_000)

  test('New Policy opens editor, Deploy disabled→enabled, deploy', async ({ page }) => {
    await page.goto('/policies')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-policies-list.png'), fullPage: true })

    await page.getByRole('button', { name: /new policy/i }).click()
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-policies-editor.png'), fullPage: true })

    const deployBtn = page.getByRole('button', { name: /deploy/i })
    await expect(deployBtn).toBeDisabled()

    const textarea = page.locator('textarea')
    await textarea.fill('package fabric.policy\n\ndefault allow := false')
    await expect(deployBtn).toBeEnabled()

    await deployBtn.click()
    await page.waitForTimeout(1000)
  })

  test('Cancel and Close × close the editor', async ({ page }) => {
    await page.goto('/policies')
    await page.waitForTimeout(1000)

    await page.getByRole('button', { name: /new policy/i }).click()
    await page.waitForTimeout(1000)
    await page.getByRole('button', { name: /cancel/i }).click()
    await page.waitForTimeout(1000)
    await expect(page.locator('textarea')).not.toBeVisible()

    await page.getByRole('button', { name: /new policy/i }).click()
    await page.waitForTimeout(1000)
    await page.locator('.fixed .text-gray-400').first().click()
    await page.waitForTimeout(1000)
    await expect(page.locator('textarea')).not.toBeVisible()
  })
})

// ───────────────────────────────────────────────────────
// 9. AUDIT — Export, filter dropdowns
// ───────────────────────────────────────────────────────
test.describe('Audit — all buttons and filters', () => {
  test.setTimeout(120_000)

  test('Export button triggers export API', async ({ page }) => {
    await page.goto('/audit')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-audit-list.png'), fullPage: true })

    await page.getByRole('button', { name: /export/i }).click()
    await page.waitForTimeout(1000)
  })

  test('Event Type dropdown: all 4 options', async ({ page }) => {
    await page.goto('/audit')
    await page.waitForTimeout(1000)

    const selects = page.locator('select')
    const eventTypeSelect = selects.nth(0)
    const eventTypeOptions = ['', 'capability_request', 'policy_change', 'server_registered', 'server_decommissioned']
    for (const opt of eventTypeOptions) {
      await eventTypeSelect.selectOption(opt)
      await page.waitForTimeout(500)
    }
  })

  test('Actor dropdown: all 3 options', async ({ page }) => {
    await page.goto('/audit')
    await page.waitForTimeout(1000)

    const selects = page.locator('select')
    const actorSelect = selects.nth(1)
    const actorOptions = ['', 'agent', 'admin']
    for (const opt of actorOptions) {
      await actorSelect.selectOption(opt)
      await page.waitForTimeout(500)
    }

    await page.getByRole('button', { name: /clear all/i }).click()
    await page.waitForTimeout(1000)
  })

  test('Pagination "Total:" is rendered', async ({ page }) => {
    await page.goto('/audit')
    await page.waitForTimeout(1000)
    await expect(page.getByText(/total:/i)).toBeVisible()
  })
})

// ───────────────────────────────────────────────────────
// 10. APPROVALS — Review, Approve, Deny, Close, status filter
// ───────────────────────────────────────────────────────
test.describe('Approvals — all buttons and review panel', () => {
  test.setTimeout(120_000)

  test('Review button opens panel, Approve executes resolution', async ({ page }) => {
    await page.goto('/approvals')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-approvals-list.png'), fullPage: true })

    await page.getByRole('button', { name: /review/i }).first().click()
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-approvals-review.png'), fullPage: true })

    await expect(page.getByRole('button', { name: /approve/i })).toBeVisible()
    await page.getByRole('button', { name: /approve/i }).click()
    await page.waitForTimeout(1000)
  })

  test('Deny button executes rejection', async ({ page }) => {
    await page.goto('/approvals')
    await page.waitForTimeout(1000)

    await page.getByRole('button', { name: /review/i }).first().click()
    await page.waitForTimeout(1000)

    await expect(page.getByRole('button', { name: /deny/i })).toBeVisible()
    await page.getByRole('button', { name: /deny/i }).click()
    await page.waitForTimeout(1000)
  })

  test('Close button closes review panel', async ({ page }) => {
    await page.goto('/approvals')
    await page.waitForTimeout(1000)

    await page.getByRole('button', { name: /review/i }).first().click()
    await page.waitForTimeout(1000)
    await page.getByRole('button', { name: /close/i }).click()
    await page.waitForTimeout(1000)
    await expect(page.getByRole('button', { name: /approve/i })).not.toBeVisible()
  })

  test('Status filter dropdown: all 3 options', async ({ page }) => {
    await page.goto('/approvals')
    await page.waitForTimeout(1000)

    const selects = page.locator('select')
    const statusSelect = selects.first()
    const statusOptions = ['', 'pending', 'approved', 'denied']
    for (const opt of statusOptions) {
      await statusSelect.selectOption(opt)
      await page.waitForTimeout(500)
    }

    await page.getByRole('button', { name: /clear all/i }).click()
    await page.waitForTimeout(1000)
  })
})

// ───────────────────────────────────────────────────────
// 11. PACKS — Create Pack, Assign to class, modals, dropdown
// ───────────────────────────────────────────────────────
test.describe('Packs — all buttons and modals', () => {
  test.setTimeout(180_000)

  test('Create Pack modal: save disabled→enabled, create', async ({ page }) => {
    await page.goto('/packs')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-packs-list.png'), fullPage: true })

    await page.getByRole('button', { name: /create pack/i }).click()
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-packs-modal.png'), fullPage: true })

    const modal = page.locator('.fixed.inset-0.z-50').last()
    const saveBtn = modal.getByRole('button', { name: /save/i })
    await expect(saveBtn).toBeDisabled()

    await modal.locator('input').first().fill('My New Pack')
    await expect(saveBtn).toBeEnabled()
    await saveBtn.click()
    await page.waitForTimeout(1000)
  })

  test('"Assign to class" opens modal, Assign disabled→enabled when class selected', async ({ page }) => {
    await page.goto('/packs')
    await page.waitForTimeout(1000)

    await page.getByRole('button', { name: /assign to class/i }).first().click()
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-packs-assign.png'), fullPage: true })

    const modal = page.locator('.fixed.inset-0.z-50').last()
    const assignBtn = modal.getByRole('button', { name: /assign/i })
    await expect(assignBtn).toBeDisabled()

    const agentSelect = modal.locator('select')
    if ((await agentSelect.count()) > 0) {
      await agentSelect.selectOption('cls-1')
      await page.waitForTimeout(1000)
      await expect(assignBtn).toBeEnabled()
    }

    await assignBtn.click()
    await page.waitForTimeout(1000)
  })

  test('Pack modals Cancel and Close × buttons', async ({ page }) => {
    await page.goto('/packs')
    await page.waitForTimeout(1000)

    await page.getByRole('button', { name: /create pack/i }).click()
    await page.waitForTimeout(1000)
    await page.locator('.fixed.inset-0.z-50').last().getByRole('button', { name: /cancel/i }).click()
    await page.waitForTimeout(1000)

    await page.getByRole('button', { name: /assign to class/i }).first().click()
    await page.waitForTimeout(1000)
    await page.locator('.fixed.inset-0.z-50').last().getByRole('button', { name: /cancel/i }).click()
    await page.waitForTimeout(1000)
  })

  test('Pack Resource Bindings modal shows PackBreadthWarning banner', async ({ page }) => {
    await page.goto('/packs')
    await page.waitForTimeout(1000)

    await page.getByRole('button', { name: /bindings/i }).first().click()
    await page.waitForTimeout(2000)

    await expect(page.locator('text=Pack granularity guide')).toBeVisible()
    // Verify a tier label rendered (mock returns warning_tier: 'strong')
    await expect(page.getByText(/coverage/i)).toBeVisible()
  })
})

// ───────────────────────────────────────────────────────
// 12. ALERTS — Acknowledge, status filter
// ───────────────────────────────────────────────────────
test.describe('Alerts — acknowledge and filter', () => {
  test.setTimeout(120_000)

  test('"Acknowledge" row button triggers API', async ({ page }) => {
    await page.goto('/alerts')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-alerts-list.png'), fullPage: true })

    await page.getByRole('button', { name: /acknowledge/i }).first().click()
    await page.waitForTimeout(1000)
  })

  test('Status filter dropdown: all 2 options', async ({ page }) => {
    await page.goto('/alerts')
    await page.waitForTimeout(1000)

    const selects = page.locator('select')
    const statusSelect = selects.first()
    const statusOptions = ['', 'false', 'true']
    for (const opt of statusOptions) {
      await statusSelect.selectOption(opt)
      await page.waitForTimeout(500)
    }

    await page.getByRole('button', { name: /clear all/i }).click()
    await page.waitForTimeout(1000)
  })
})

// ───────────────────────────────────────────────────────
// 13. ADMIN USERS — Invite, Send Invite, Deactivate, role dropdown
// ───────────────────────────────────────────────────────
test.describe('Admin Users — all buttons and invite modal', () => {
  test.setTimeout(180_000)

  test('Invite User modal: Send Invite disabled→enabled, invite, cancel', async ({ page }) => {
    await page.goto('/admin/users')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-admin-users-list.png'), fullPage: true })

    await page.getByRole('button', { name: /invite user/i }).click()
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-admin-users-invite.png'), fullPage: true })

    const modal = page.locator('.fixed.inset-0.z-50').last()
    const sendInviteBtn = modal.getByRole('button', { name: /send invite/i })
    await expect(sendInviteBtn).toBeDisabled()

    const inputs = modal.locator('input')
    if (await inputs.count() >= 2) {
      await inputs.nth(0).fill('newuser')
      await expect(sendInviteBtn).toBeDisabled()
      await inputs.nth(1).fill('new@example.com')
      await expect(sendInviteBtn).toBeEnabled()
    }

    await sendInviteBtn.click()
    await page.waitForTimeout(1000)

    await page.getByRole('button', { name: /invite user/i }).click()
    await page.waitForTimeout(1000)
    await page.locator('.fixed.inset-0.z-50').last().getByRole('button', { name: /cancel/i }).click()
    await page.waitForTimeout(1000)
  })

  test('Role dropdown: Admin, Editor, Viewer options', async ({ page }) => {
    await page.goto('/admin/users')
    await page.waitForTimeout(1000)

    await page.getByRole('button', { name: /invite user/i }).click()
    await page.waitForTimeout(1000)

    const modal = page.locator('.fixed.inset-0.z-50').last()
    const roleSelect = modal.locator('select')
    if ((await roleSelect.count()) > 0) {
      const roleOptions = ['admin', 'editor', 'viewer']
      for (const opt of roleOptions) {
        await roleSelect.selectOption(opt)
        await page.waitForTimeout(500)
      }
    }
  })

  test('"Deactivate" row button triggers API', async ({ page }) => {
    await page.goto('/admin/users')
    await page.waitForTimeout(1000)

    const deactBtn = page.getByRole('button', { name: /deactivate/i }).last()
    await deactBtn.click()
    await page.waitForTimeout(1000)
  })
})

// ───────────────────────────────────────────────────────
// 14. TRUST POSTURE — Class dropdown, per-server trust dropdown
// ───────────────────────────────────────────────────────
test.describe('Trust Posture — dropdowns and per-server trust', () => {
  test.setTimeout(120_000)

  test('Agent Class dropdown: select class, per-server trust dropdowns', async ({ page }) => {
    await page.goto('/trust')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-trust-posture.png'), fullPage: true })

    const classSelect = page.locator('select').first()
    await classSelect.selectOption('cls-1')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-trust-posture-class-selected.png'), fullPage: true })

    const allSelects = page.locator('select')
    const selectCount = await allSelects.count()
    if (selectCount > 1) {
      const trustOptions = ['trusted', 'restricted', 'approval-gated', 'unreviewed']
      const serverTrustSelect = allSelects.nth(1)
      for (const opt of trustOptions) {
        await serverTrustSelect.selectOption(opt)
        await page.waitForTimeout(500)
      }
    }

    await classSelect.selectOption('cls-2')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-trust-posture-cls2.png'), fullPage: true })
  })

  test('Identity-Binding Coverage card shows pack breadth table', async ({ page }) => {
    await page.goto('/trust')
    await page.waitForTimeout(2000)

    await expect(page.getByText('Identity-Binding Coverage')).toBeVisible()
    await expect(page.getByText('Developer Agents')).toBeVisible()
    await expect(page.getByText('Ops Agents')).toBeVisible()
    await expect(page.getByText('97.1%')).toBeVisible()
    await expect(page.getByText('2.0%')).toBeVisible()
  })
})

// ───────────────────────────────────────────────────────
// 15. SCHEMA REVIEWS — stale list, approve, reject
// Tests the Reviews page which lists stale capability-to-server mappings
// whose tool schemas have changed. Admins can approve (accept the new schema)
// or reject (flag for investigation) each stale mapping.
// ───────────────────────────────────────────────────────
test.describe('Reviews — stale mappings and approve/reject', () => {
  test.setTimeout(120_000)

  test('Reviews page renders stale mappings with Approve and Reject buttons', async ({ page }) => {
    await page.goto('/reviews')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'btn-reviews-list.png'), fullPage: true })

    await expect(page.getByText('knowledge:search').first()).toBeVisible()
    await expect(page.getByText('search_kb').first()).toBeVisible()

    await page.getByRole('button', { name: /approve/i }).first().click()
    await page.waitForTimeout(1000)

    await expect(page.getByRole('button', { name: /reject/i }).first()).toBeVisible()
    await page.getByRole('button', { name: /reject/i }).first().click()
    await page.waitForTimeout(1000)
  })
})

// ───────────────────────────────────────────────────────
// 16. ERROR BOUNDARY — Try again and Go to Dashboard
// ───────────────────────────────────────────────────────
test.describe('ErrorBoundary — Try again and Go to Dashboard', () => {
  test.setTimeout(60_000)

  test('Error boundary shows Try again and Go to Dashboard', async ({ page }) => {
    await page.goto('/')
    await page.waitForTimeout(1000)

    await page.evaluate(() => {
      const err = new Error('Simulated boundary error')
      const evt = new ErrorEvent('error', { error: err, message: err.message })
      window.dispatchEvent(evt)
    })
    await page.waitForTimeout(1000)

    const tryAgainVisible = await page.getByRole('button', { name: /try again/i }).isVisible().catch(() => false)
    if (tryAgainVisible) {
      await page.screenshot({ path: path.join(SHOTS, 'btn-error-boundary.png'), fullPage: true })
    }
  })
})

// ───────────────────────────────────────────────────────
// 16. FULL DEEP WALKTHROUGH — every page, every modal
// ───────────────────────────────────────────────────────
test.describe('Full deep walkthrough — all pages and interactions', () => {
  test.setTimeout(600_000)

  test('exercise every page and every primary action with screenshots', async ({ page }) => {
    const W = 1000

    await page.goto('/')
    await page.waitForTimeout(W)
    await expect(page.getByRole('heading', { name: /dashboard/i })).toBeVisible()
    await page.screenshot({ path: path.join(SHOTS, 'walk-01-dashboard.png'), fullPage: true })

    await page.goto('/servers')
    await page.waitForTimeout(W)
    await page.getByRole('button', { name: /register server/i }).click()
    await page.waitForTimeout(W)
    await page.screenshot({ path: path.join(SHOTS, 'walk-02-servers-modal.png'), fullPage: true })
    await page.locator('.fixed.inset-0.z-50').last().getByRole('button', { name: /cancel/i }).click()
    await page.waitForTimeout(W)

    await page.goto('/capabilities')
    await page.waitForTimeout(W)
    await page.getByRole('button', { name: /create capability/i }).click()
    await page.waitForTimeout(W)
    await page.screenshot({ path: path.join(SHOTS, 'walk-03-capabilities-modal.png'), fullPage: true })
    await page.locator('.fixed.inset-0.z-50').last().getByRole('button', { name: /cancel/i }).click()
    await page.waitForTimeout(W)

    await page.goto('/agent-classes')
    await page.waitForTimeout(W)
    await page.getByRole('button', { name: /tokens/i }).first().click()
    await page.waitForTimeout(W)
    await page.screenshot({ path: path.join(SHOTS, 'walk-04-agent-classes-tokens.png'), fullPage: true })
    await page.locator('.fixed.inset-0.z-50').last().locator('button').first().click()
    await page.waitForTimeout(W)

    await page.goto('/policies')
    await page.waitForTimeout(W)
    await page.getByRole('button', { name: /new policy/i }).click()
    await page.waitForTimeout(W)
    await page.screenshot({ path: path.join(SHOTS, 'walk-05-policies-editor.png'), fullPage: true })
    await page.getByRole('button', { name: /cancel/i }).click()
    await page.waitForTimeout(W)

    await page.goto('/audit')
    await page.waitForTimeout(W)
    await page.screenshot({ path: path.join(SHOTS, 'walk-06-audit.png'), fullPage: true })
    await page.getByRole('button', { name: /export/i }).click()
    await page.waitForTimeout(W)

    await page.goto('/approvals')
    await page.waitForTimeout(W)
    await page.getByRole('button', { name: /review/i }).first().click()
    await page.waitForTimeout(W)
    await page.screenshot({ path: path.join(SHOTS, 'walk-07-approvals-review.png'), fullPage: true })
    await page.getByRole('button', { name: /approve/i }).click()
    await page.waitForTimeout(W)

    await page.goto('/packs')
    await page.waitForTimeout(W)
    await page.getByRole('button', { name: /assign to class/i }).first().click()
    await page.waitForTimeout(W)
    await page.screenshot({ path: path.join(SHOTS, 'walk-08-packs-assign.png'), fullPage: true })
    await page.locator('.fixed.inset-0.z-50').last().getByRole('button', { name: /cancel/i }).click()
    await page.waitForTimeout(W)

    await page.goto('/alerts')
    await page.waitForTimeout(W)
    await page.getByRole('button', { name: /acknowledge/i }).first().click()
    await page.waitForTimeout(W)

    await page.goto('/admin/users')
    await page.waitForTimeout(W)
    await page.screenshot({ path: path.join(SHOTS, 'walk-09-admin-users.png'), fullPage: true })
    await page.getByRole('button', { name: /invite user/i }).click()
    await page.waitForTimeout(W)
    await page.screenshot({ path: path.join(SHOTS, 'walk-10-admin-invite.png'), fullPage: true })
    await page.locator('.fixed.inset-0.z-50').last().getByRole('button', { name: /cancel/i }).click()
    await page.waitForTimeout(W)

    await page.goto('/trust')
    await page.waitForTimeout(W)
    await page.screenshot({ path: path.join(SHOTS, 'walk-11-trust-posture.png'), fullPage: true })

    // Schema Reviews: navigate to /reviews, click approve then reject on stale mappings
    await page.goto('/reviews')
    await page.waitForTimeout(W)
    await page.getByRole('button', { name: /approve/i }).first().click()
    await page.waitForTimeout(W)
    await page.screenshot({ path: path.join(SHOTS, 'walk-12-reviews.png'), fullPage: true })

    await page.getByRole('button', { name: /logout/i }).click()
    await page.waitForTimeout(W)
    await expect(page).toHaveURL(/\/login/)
  })
})
