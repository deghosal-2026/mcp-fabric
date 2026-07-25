import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const SCREENSHOT_DIR = path.resolve(__dirname, '../../docs/ui-test/findings/screenshots')

const MOCK_TOKEN = 'fcp_test_admin_token_1234567890abcdef'

const MOCK_SERVERS = {
  items: [
    { id: 'srv-1', name: 'KB Server', endpoint: 'http://kb.internal:3001', owner_team: 'platform', labels: ['knowledge', 'internal'], trust_level: 'trusted', health_status: 'healthy', team_namespace: 'team:platform', decommissioned_at: null, created_at: '2026-07-01T00:00:00Z' },
    { id: 'srv-2', name: 'Code Search', endpoint: 'http://codesearch.internal:3002', owner_team: 'platform', labels: ['code', 'search'], trust_level: 'trusted', health_status: 'healthy', team_namespace: 'team:platform', decommissioned_at: null, created_at: '2026-07-02T00:00:00Z' },
    { id: 'srv-3', name: 'Vuln Scanner', endpoint: 'http://security.internal:3003', owner_team: 'security', labels: ['security', 'scanning'], trust_level: 'restricted', health_status: 'degraded', team_namespace: 'team:security', decommissioned_at: null, created_at: '2026-07-03T00:00:00Z' },
    { id: 'srv-4', name: 'Deployment Server', endpoint: 'http://deploy.internal:3004', owner_team: 'platform', labels: ['deployment', 'production'], trust_level: 'approval-gated', health_status: 'healthy', team_namespace: 'team:platform', decommissioned_at: null, created_at: '2026-07-04T00:00:00Z' },
    { id: 'srv-5', name: 'New Unreviewed', endpoint: 'http://new.internal:3005', owner_team: 'data', labels: ['data', 'new'], trust_level: 'unreviewed', health_status: 'unhealthy', team_namespace: 'team:data', decommissioned_at: null, created_at: '2026-07-05T00:00:00Z' },
    { id: 'srv-6', name: 'Git History', endpoint: 'http://git.internal:3006', owner_team: 'platform', labels: ['git', 'history'], trust_level: 'trusted', health_status: 'healthy', team_namespace: 'team:platform', decommissioned_at: null, created_at: '2026-07-06T00:00:00Z' },
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
  ],
  pagination: { total: 2, has_more: false, per_page: 50 },
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

const MOCK_DASHBOARD = {
  server_count: 6,
  healthy_servers: 4,
  pending_approvals: 2,
  recent_audit_events: 42,
  degraded_servers: 1,
}

const MOCK_USER = {
  id: 'usr-1',
  username: 'priya',
  role: 'admin',
  team_namespace: 'team:platform',
  mfa_enabled: true,
}

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
    if (path.match(/^\/v1\/approvals\/.+\/resolve$/)) {
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

    route.continue()
  })
})

test.describe('Admin UI — Page Screenshots', () => {
  test('Login page', async ({ page }) => {
    await page.addInitScript(() => { localStorage.clear() })
    await page.goto('/login')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01-login.png'), fullPage: true })
  })

  test('Dashboard', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02-dashboard.png'), fullPage: true })
  })

  test('Servers list', async ({ page }) => {
    await page.goto('/servers')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03-servers.png'), fullPage: true })
  })

  test('Servers — Register modal open', async ({ page }) => {
    await page.goto('/servers')
    await page.waitForLoadState('networkidle')
    await page.getByRole('button', { name: /register server/i }).click()
    await page.waitForTimeout(300)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04-servers-register-modal.png'), fullPage: true })
  })

  test('Capabilities catalog', async ({ page }) => {
    await page.goto('/capabilities')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05-capabilities.png'), fullPage: true })
  })

  test('Capabilities — Create modal', async ({ page }) => {
    await page.goto('/capabilities')
    await page.waitForLoadState('networkidle')
    await page.getByRole('button', { name: /create capability/i }).click()
    await page.waitForTimeout(300)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06-capabilities-create-modal.png'), fullPage: true })
  })

  test('Agent classes', async ({ page }) => {
    await page.goto('/agent-classes')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07-agent-classes.png'), fullPage: true })
  })

  test('Policies', async ({ page }) => {
    await page.goto('/policies')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '08-policies.png'), fullPage: true })
  })

  test('Policies — Editor modal', async ({ page }) => {
    await page.goto('/policies')
    await page.waitForLoadState('networkidle')
    await page.getByRole('button', { name: /new policy/i }).click()
    await page.waitForTimeout(300)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '09-policies-editor.png'), fullPage: true })
  })

  test('Audit log', async ({ page }) => {
    await page.goto('/audit')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '10-audit.png'), fullPage: true })
  })

  test('Approvals', async ({ page }) => {
    await page.goto('/approvals')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '11-approvals.png'), fullPage: true })
  })

  test('Approvals — Review panel', async ({ page }) => {
    await page.goto('/approvals')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)
    await page.locator('button', { hasText: 'Review' }).first().click()
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '12-approvals-review.png'), fullPage: true })
  })

  test('Capability packs', async ({ page }) => {
    await page.goto('/packs')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '13-packs.png'), fullPage: true })
  })

  test('Alerts', async ({ page }) => {
    await page.goto('/alerts')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '14-alerts.png'), fullPage: true })
  })

  test('Admin users', async ({ page }) => {
    await page.goto('/admin/users')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '15-admin-users.png'), fullPage: true })
  })

  test('Admin users — Invite modal', async ({ page }) => {
    await page.goto('/admin/users')
    await page.waitForLoadState('networkidle')
    await page.getByRole('button', { name: /invite user/i }).click()
    await page.waitForTimeout(300)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '16-admin-users-invite.png'), fullPage: true })
  })

  test('Trust posture', async ({ page }) => {
    await page.goto('/trust')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '17-trust-posture.png'), fullPage: true })
  })

  test('Trust posture — agent class selected', async ({ page }) => {
    await page.goto('/trust')
    await page.waitForLoadState('networkidle')
    const classSelect = page.locator('select').first()
    await classSelect.selectOption('cls-1')
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '18-trust-posture-class-selected.png'), fullPage: true })
  })
})

test.describe('Admin UI — Interaction Flows', () => {
  test('Full navigation tour through all pages', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const pages = [
      { label: 'Dashboard', url: '/' },
      { label: 'Servers', url: '/servers' },
      { label: 'Capabilities', url: '/capabilities' },
      { label: 'Agent Classes', url: '/agent-classes' },
      { label: 'Policies', url: '/policies' },
      { label: 'Audit Log', url: '/audit' },
      { label: 'Approvals', url: '/approvals' },
      { label: 'Capability Packs', url: '/packs' },
      { label: 'Alerts', url: '/alerts' },
      { label: 'Admin Users', url: '/admin/users' },
      { label: 'Trust Posture', url: '/trust' },
    ]

    for (const p of pages) {
      await page.goto(p.url)
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(300)
      await expect(page.locator('h1').first()).toBeVisible()
    }
  })

  test('Logout clears session', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.getByRole('button', { name: /logout/i }).click()
    await expect(page).toHaveURL(/\/login/)
  })

  test('Filter servers by health status', async ({ page }) => {
    await page.goto('/servers')
    await page.waitForLoadState('networkidle')
    const filterSelect = page.locator('select').first()
    await filterSelect.selectOption('healthy')
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '19-servers-filtered.png'), fullPage: true })
  })
})
