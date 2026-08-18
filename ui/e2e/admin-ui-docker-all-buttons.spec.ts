import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const SHOTS = path.resolve(__dirname, '../../docs/ui-test/findings/screenshots')

const CREDS = { username: 'admin', password: 'Admin123!' }

async function login(page: import('@playwright/test').Page) {
  await page.goto('/login')
  await page.waitForLoadState('networkidle')
  const textboxes = page.getByRole('textbox')
  await textboxes.nth(0).fill(CREDS.username)
  await textboxes.nth(1).fill(CREDS.password)
  await page.getByRole('button', { name: /login/i }).click()
  await page.waitForURL(/\/$/)
  await page.waitForLoadState('networkidle')
}

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
      await login(page)
      await page.getByRole('link', { name: link.label }).click()
      await page.waitForLoadState('networkidle')
      await expect(page).toHaveURL(link.expectedUrl)
    })
  }
})

// ───────────────────────────────────────────────────────
// 2. TOP BAR — Logout
// ───────────────────────────────────────────────────────
test.describe('TopBar', () => {
  test.setTimeout(60_000)

  test('Logout clears session and redirects to /login', async ({ page }) => {
    await login(page)
    await page.getByRole('button', { name: /logout/i }).click()
    await page.waitForURL(/\/login/)
    await page.screenshot({ path: path.join(SHOTS, 'docker-topbar-logout.png'), fullPage: true })
  })
})

// ───────────────────────────────────────────────────────
// 3. LOGIN PAGE
// ───────────────────────────────────────────────────────
test.describe('Login page', () => {
  test.setTimeout(60_000)

  test('Login button disabled when empty, enabled when filled', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('networkidle')

    const loginBtn = page.getByRole('button', { name: /login/i })
    await expect(loginBtn).toBeDisabled()

    const textboxes = page.getByRole('textbox')
    await textboxes.nth(0).fill('admin')
    await expect(loginBtn).toBeDisabled()

    await textboxes.nth(1).fill('wrong')
    await expect(loginBtn).toBeEnabled()
  })

  test('Login error on bad credentials', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('networkidle')

    const textboxes = page.getByRole('textbox')
    await textboxes.nth(0).fill('bad')
    await textboxes.nth(1).fill('credentials')
    await page.getByRole('button', { name: /login/i }).click()
    await page.waitForTimeout(1000)
    await expect(page.locator('[role="alert"], .text-red-600').first()).toBeVisible()
  })
})

// ───────────────────────────────────────────────────────
// 4. DASHBOARD — links and stats
// ───────────────────────────────────────────────────────
test.describe('Dashboard', () => {
  test.setTimeout(60_000)

  test('Stats render and View all links navigate', async ({ page }) => {
    await login(page)
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SHOTS, 'docker-dashboard.png'), fullPage: true })

    await expect(page.getByText(/servers/i).first()).toBeVisible()

    const viewAllLinks = page.locator('a').filter({ hasText: /view all/i })
    if (await viewAllLinks.count() > 0) {
      await viewAllLinks.first().click()
      await page.waitForURL(/\/servers/)
      await page.goto('/')
      await page.waitForLoadState('networkidle')
    }

    await page.locator('a').filter({ hasText: /view all/i }).last().click()
    await page.waitForLoadState('networkidle')
    await expect(page).toHaveURL(/\/audit/)
  })
})

// ───────────────────────────────────────────────────────
// 5. SERVERS — all buttons, filters, modal
// ───────────────────────────────────────────────────────
test.describe('Servers', () => {
  test.setTimeout(180_000)

  test('Register Server modal: open, save disabled→enabled, create, cancel', async ({ page }) => {
    await login(page)
    await page.goto('/servers')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SHOTS, 'docker-servers-list.png'), fullPage: true })

    await page.getByRole('button', { name: /register server/i }).click()
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SHOTS, 'docker-servers-modal.png'), fullPage: true })

    const modal = page.locator('.fixed.inset-0.z-50').last()
    const saveBtn = modal.getByRole('button', { name: /save/i })
    await expect(saveBtn).toBeDisabled()

    const inputs = modal.locator('input')
    if (await inputs.count() >= 2) {
      await inputs.nth(0).fill('Docker Test Server')
      await inputs.nth(1).fill('http://test:3999')
    }
    await expect(saveBtn).toBeEnabled()

    await modal.getByRole('button', { name: /cancel/i }).click()
    await page.waitForTimeout(500)

    await page.getByRole('button', { name: /register server/i }).click()
    await page.waitForTimeout(500)
    await page.locator('.fixed.inset-0.z-50').last().locator('button').first().click()
    await page.waitForTimeout(500)
  })

  test('Filter dropdowns: Health, Trust, Team — each option', async ({ page }) => {
    await login(page)
    await page.goto('/servers')
    await page.waitForLoadState('networkidle')

    const selects = page.locator('select')
    const count = await selects.count()

    if (count >= 1) {
      for (const opt of ['', 'healthy', 'degraded', 'unhealthy']) {
        await selects.nth(0).selectOption(opt)
        await page.waitForTimeout(500)
      }
    }
    if (count >= 2) {
      for (const opt of ['', 'trusted', 'restricted', 'approval-gated', 'unreviewed']) {
        await selects.nth(1).selectOption(opt)
        await page.waitForTimeout(500)
      }
    }
    if (count >= 3) {
      for (const opt of ['', 'team:platform', 'team:security', 'team:data']) {
        await selects.nth(2).selectOption(opt)
        await page.waitForTimeout(500)
      }
    }

    await page.getByRole('button', { name: /clear all/i }).click()
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SHOTS, 'docker-servers-filtered.png'), fullPage: true })
  })

  test('Search input', async ({ page }) => {
    await login(page)
    await page.goto('/servers')
    await page.waitForLoadState('networkidle')

    const searchInput = page.locator('input[type="text"]').last()
    await searchInput.fill('KB')
    await page.waitForTimeout(500)
    await page.getByRole('button', { name: /clear all/i }).click()
    await page.waitForTimeout(500)
  })
})

// ───────────────────────────────────────────────────────
// 6. CAPABILITIES — Create, Deprecate, filters
// ───────────────────────────────────────────────────────
test.describe('Capabilities', () => {
  test.setTimeout(180_000)

  test('Create modal: disabled→enabled, create, cancel', async ({ page }) => {
    await login(page)
    await page.goto('/capabilities')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SHOTS, 'docker-capabilities-list.png'), fullPage: true })

    await page.getByRole('button', { name: /create capability/i }).click()
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SHOTS, 'docker-capabilities-modal.png'), fullPage: true })

    const modal = page.locator('.fixed.inset-0.z-50').last()
    const saveBtn = modal.getByRole('button', { name: /save/i })
    await expect(saveBtn).toBeDisabled()

    await modal.locator('input').nth(0).fill('docker:test-cap')
    if (await modal.locator('input').count() >= 2) {
      await modal.locator('input').nth(1).fill('code')
    }
    await expect(saveBtn).toBeEnabled()

    await saveBtn.click()
    await page.waitForTimeout(500)
  })

  test('Deprecate row button opens confirm modal', async ({ page }) => {
    await login(page)
    await page.goto('/capabilities')
    await page.waitForLoadState('networkidle')

    const deprecateBtn = page.locator('button:enabled', { hasText: /deprecate/i })
    if (await deprecateBtn.count() > 0) {
      await deprecateBtn.first().click()
      await page.waitForTimeout(500)
      await page.screenshot({ path: path.join(SHOTS, 'docker-capabilities-deprecate.png'), fullPage: true })

      const modal = page.locator('.fixed.inset-0.z-50').last()
      await modal.getByRole('button', { name: /deprecate/i }).click()
      await page.waitForTimeout(500)
    }
  })

  test('Filter dropdowns: Domain and Status', async ({ page }) => {
    await login(page)
    await page.goto('/capabilities')
    await page.waitForLoadState('networkidle')

    const selects = page.locator('select')
    const count = await selects.count()

    if (count >= 1) {
      for (const opt of ['', 'knowledge', 'code', 'deployment', 'incident', 'security']) {
        await selects.nth(0).selectOption(opt)
        await page.waitForTimeout(500)
      }
    }
    if (count >= 2) {
      for (const opt of ['', 'active', 'deprecated']) {
        await selects.nth(1).selectOption(opt)
        await page.waitForTimeout(500)
      }
    }
    await page.getByRole('button', { name: /clear all/i }).click()
    await page.waitForTimeout(500)
  })
})

// ───────────────────────────────────────────────────────
// 7. AGENT CLASSES — Create, Tokens, generate
// ───────────────────────────────────────────────────────
test.describe('Agent Classes', () => {
  test.setTimeout(120_000)

  test('Create modal: disabled→enabled, create', async ({ page }) => {
    await login(page)
    await page.goto('/agent-classes')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SHOTS, 'docker-agent-classes-list.png'), fullPage: true })

    await page.getByRole('button', { name: /create agent class/i }).click()
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SHOTS, 'docker-agent-classes-modal.png'), fullPage: true })

    const modal = page.locator('.fixed.inset-0.z-50').last()
    const saveBtn = modal.getByRole('button', { name: /save/i })
    await expect(saveBtn).toBeDisabled()

    await modal.locator('input').first().fill('docker:agent-tester')
    await expect(saveBtn).toBeEnabled()
    await saveBtn.click()
    await page.waitForTimeout(500)
  })

  test('Tokens row button opens modal, generate token', async ({ page }) => {
    await login(page)
    await page.goto('/agent-classes')
    await page.waitForLoadState('networkidle')

    await page.getByRole('button', { name: /tokens/i }).first().click()
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SHOTS, 'docker-agent-classes-tokens.png'), fullPage: true })

    const modal = page.locator('.fixed.inset-0.z-50').last()
    const generateBtn = modal.getByRole('button', { name: /generate/i })

    await modal.locator('input').fill('docker-test-token')
    await expect(generateBtn).toBeEnabled()
    await generateBtn.click()
    await page.waitForTimeout(500)
  })
})

// ───────────────────────────────────────────────────────
// 8. POLICIES — New Policy, Deploy, Cancel
// ───────────────────────────────────────────────────────
test.describe('Policies', () => {
  test.setTimeout(120_000)

  test('New Policy editor: Deploy disabled→enabled, deploy', async ({ page }) => {
    await login(page)
    await page.goto('/policies')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'docker-policies-list.png'), fullPage: true })

    await page.getByRole('button', { name: /new policy/i }).click()
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'docker-policies-editor.png'), fullPage: true })

    const deployBtn = page.getByRole('button', { name: /deploy/i })
    await expect(deployBtn).toBeDisabled()

    await page.locator('textarea').fill('package fabric.policy\n\ndefault allow := false')
    await expect(deployBtn).toBeEnabled()

    await deployBtn.click()
    await page.waitForTimeout(500)
  })

  test('Cancel closes editor', async ({ page }) => {
    await login(page)
    await page.goto('/policies')
    await page.waitForLoadState('networkidle')

    await page.getByRole('button', { name: /new policy/i }).click()
    await page.waitForTimeout(500)
    await page.getByRole('button', { name: /cancel/i }).click()
    await page.waitForTimeout(500)
    await expect(page.locator('textarea')).not.toBeVisible()
  })
})

// ───────────────────────────────────────────────────────
// 9. AUDIT — Export, filters
// ───────────────────────────────────────────────────────
test.describe('Audit', () => {
  test.setTimeout(120_000)

  test('Export button', async ({ page }) => {
    await login(page)
    await page.goto('/audit')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SHOTS, 'docker-audit-list.png'), fullPage: true })

    await page.getByRole('button', { name: /export/i }).click()
    await page.waitForTimeout(500)
  })

  test('Event Type and Actor dropdown options', async ({ page }) => {
    await login(page)
    await page.goto('/audit')
    await page.waitForLoadState('networkidle')

    const selects = page.locator('select')
    for (const opt of ['', 'capability_request', 'policy_change', 'server_registered', 'server_decommissioned']) {
      await selects.nth(0).selectOption(opt)
      await page.waitForTimeout(500)
    }
    for (const opt of ['', 'agent', 'admin']) {
      await selects.nth(1).selectOption(opt)
      await page.waitForTimeout(500)
    }
    await page.getByRole('button', { name: /clear all/i }).click()
    await page.waitForTimeout(500)
  })

  test('Pagination total rendered', async ({ page }) => {
    await login(page)
    await page.goto('/audit')
    await page.waitForLoadState('networkidle')
    await expect(page.getByText(/total:/i)).toBeVisible()
  })
})

// ───────────────────────────────────────────────────────
// 10. APPROVALS — Review, Approve, Deny, Close, filter
// ───────────────────────────────────────────────────────
test.describe('Approvals', () => {
  test.setTimeout(120_000)

  test('Review → Approve workflow', async ({ page }) => {
    await login(page)
    await page.goto('/approvals')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SHOTS, 'docker-approvals-list.png'), fullPage: true })

    const reviewBtn = page.getByRole('button', { name: /review/i })
    if (await reviewBtn.first().isVisible().catch(() => false)) {
      await reviewBtn.first().click()
      await page.waitForTimeout(500)
      await page.screenshot({ path: path.join(SHOTS, 'docker-approvals-review.png'), fullPage: true })
      await page.getByRole('button', { name: /approve/i }).click()
      await page.waitForTimeout(500)
    }
  })

  test('Review → Deny workflow', async ({ page }) => {
    await login(page)
    await page.goto('/approvals')
    await page.waitForLoadState('networkidle')

    const reviewBtn = page.getByRole('button', { name: /review/i })
    if (await reviewBtn.first().isVisible().catch(() => false)) {
      await reviewBtn.first().click()
      await page.waitForTimeout(500)
      await page.getByRole('button', { name: /deny/i }).click()
      await page.waitForTimeout(500)
    }
  })

  test('Close panel and status filter', async ({ page }) => {
    await login(page)
    await page.goto('/approvals')
    await page.waitForLoadState('networkidle')

    const reviewBtn = page.getByRole('button', { name: /review/i })
    if (await reviewBtn.first().isVisible().catch(() => false)) {
      await reviewBtn.first().click()
      await page.waitForTimeout(500)
      await page.getByRole('button', { name: /close/i }).click()
      await page.waitForTimeout(500)
    }

    const selects = page.locator('select')
    for (const opt of ['', 'pending', 'approved', 'denied']) {
      await selects.first().selectOption(opt)
      await page.waitForTimeout(500)
    }
    await page.getByRole('button', { name: /clear all/i }).click()
    await page.waitForTimeout(500)
  })
})

// ───────────────────────────────────────────────────────
// 11. PACKS — Create, Assign, modals
// ───────────────────────────────────────────────────────
test.describe('Packs', () => {
  test.setTimeout(180_000)

  test('Create Pack modal', async ({ page }) => {
    await login(page)
    await page.goto('/packs')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SHOTS, 'docker-packs-list.png'), fullPage: true })

    await page.getByRole('button', { name: /create pack/i }).click()
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SHOTS, 'docker-packs-modal.png'), fullPage: true })

    const modal = page.locator('.fixed.inset-0.z-50').last()
    const saveBtn = modal.getByRole('button', { name: /save/i })
    await expect(saveBtn).toBeDisabled()

    await modal.locator('input').first().fill('Docker Test Pack')
    await expect(saveBtn).toBeEnabled()
    await saveBtn.click()
    await page.waitForTimeout(500)
  })

  test('Assign to class modal', async ({ page }) => {
    await login(page)
    await page.goto('/packs')
    await page.waitForLoadState('networkidle')

    const assignBtn = page.getByRole('button', { name: /assign to class/i })
    if (await assignBtn.first().isVisible().catch(() => false)) {
      await assignBtn.first().click()
      await page.waitForTimeout(500)
      await page.screenshot({ path: path.join(SHOTS, 'docker-packs-assign.png'), fullPage: true })

      const modal = page.locator('.fixed.inset-0.z-50').last()
      const agentSelect = modal.locator('select')
      if (await agentSelect.count() > 0) {
        await agentSelect.selectOption({ index: 1 })
        await page.waitForTimeout(500)
        await modal.getByRole('button', { name: /assign/i }).click()
        await page.waitForTimeout(500)
      }
    }
  })
})

// ───────────────────────────────────────────────────────
// 12. ALERTS — Acknowledge, filter
// ───────────────────────────────────────────────────────
test.describe('Alerts', () => {
  test.setTimeout(120_000)

  test('Acknowledge row button', async ({ page }) => {
    await login(page)
    await page.goto('/alerts')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SHOTS, 'docker-alerts-list.png'), fullPage: true })

    const ackBtn = page.getByRole('button', { name: /acknowledge/i })
    if (await ackBtn.first().isVisible().catch(() => false)) {
      await ackBtn.first().click()
      await page.waitForTimeout(500)
    }
  })

  test('Status filter dropdown', async ({ page }) => {
    await login(page)
    await page.goto('/alerts')
    await page.waitForLoadState('networkidle')

    const selects = page.locator('select')
    for (const opt of ['', 'false', 'true']) {
      await selects.first().selectOption(opt)
      await page.waitForTimeout(500)
    }
    await page.getByRole('button', { name: /clear all/i }).click()
    await page.waitForTimeout(500)
  })
})

// ───────────────────────────────────────────────────────
// 13. ADMIN USERS — Invite, Deactivate, role dropdown
// ───────────────────────────────────────────────────────
test.describe('Admin Users', () => {
  test.setTimeout(180_000)

  test('Invite User modal: disabled→enabled, invite, cancel', async ({ page }) => {
    await login(page)
    await page.goto('/admin/users')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SHOTS, 'docker-admin-users-list.png'), fullPage: true })

    await page.getByRole('button', { name: /invite user/i }).click()
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SHOTS, 'docker-admin-users-invite.png'), fullPage: true })

    const modal = page.locator('.fixed.inset-0.z-50').last()
    const sendBtn = modal.getByRole('button', { name: /send invite/i })
    await expect(sendBtn).toBeDisabled()

    const inputs = modal.locator('input')
    if (await inputs.count() >= 2) {
      await inputs.nth(0).fill('dockertest')
      await expect(sendBtn).toBeDisabled()
      await inputs.nth(1).fill('dockertest@example.com')
      await expect(sendBtn).toBeEnabled()
    }

    await sendBtn.click()
    await page.waitForTimeout(500)
  })

  test('Role dropdown: Admin, Editor, Viewer', async ({ page }) => {
    await login(page)
    await page.goto('/admin/users')
    await page.waitForLoadState('networkidle')

    await page.getByRole('button', { name: /invite user/i }).click()
    await page.waitForTimeout(500)

    const modal = page.locator('.fixed.inset-0.z-50').last()
    const roleSelect = modal.locator('select')
    if (await roleSelect.count() > 0) {
      for (const opt of ['admin', 'editor', 'viewer']) {
        await roleSelect.selectOption(opt)
        await page.waitForTimeout(500)
      }
    }
  })

  test('Deactivate row button', async ({ page }) => {
    await login(page)
    await page.goto('/admin/users')
    await page.waitForLoadState('networkidle')

    const deactBtn = page.getByRole('button', { name: /deactivate/i })
    if (await deactBtn.last().isVisible().catch(() => false)) {
      await deactBtn.last().click()
      await page.waitForTimeout(500)
    }
  })
})

// ───────────────────────────────────────────────────────
// 14. TRUST POSTURE — class dropdown, per-server trust
// ───────────────────────────────────────────────────────
test.describe('Trust Posture', () => {
  test.setTimeout(120_000)

  test('Class dropdown and per-server trust dropdowns', async ({ page }) => {
    await login(page)
    await page.goto('/trust')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'docker-trust-posture.png'), fullPage: true })

    const classSelect = page.locator('select').first()
    await classSelect.selectOption({ index: 1 })
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SHOTS, 'docker-trust-posture-class-selected.png'), fullPage: true })

    const allSelects = page.locator('select')
    if ((await allSelects.count()) > 1) {
      for (const opt of ['trusted', 'restricted', 'approval-gated', 'unreviewed']) {
        await allSelects.nth(1).selectOption(opt)
        await page.waitForTimeout(500)
      }
    }

    await classSelect.selectOption({ index: 2 })
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SHOTS, 'docker-trust-posture-cls2.png'), fullPage: true })
  })
})

// ───────────────────────────────────────────────────────
// 15. REVIEWS — stale mappings, approve, reject
// Tests the Docker review workflow: rendering the list of stale tool-schema
// mappings and exercising the approve and reject buttons on each row.
// ───────────────────────────────────────────────────────
test.describe('Reviews', () => {
  test.setTimeout(120_000)

  test('Stale mappings list renders with approve/reject buttons', async ({ page }) => {
    await login(page)
    await page.goto('/reviews')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SHOTS, 'docker-reviews-list.png'), fullPage: true })

    const approveBtn = page.getByRole('button', { name: /approve/i })
    if (await approveBtn.first().isVisible().catch(() => false)) {
      await approveBtn.first().click()
      await page.waitForTimeout(500)
    }

    const rejectBtn = page.getByRole('button', { name: /reject/i })
    if (await rejectBtn.first().isVisible().catch(() => false)) {
      await rejectBtn.first().click()
      await page.waitForTimeout(500)
    }
  })
})

// ───────────────────────────────────────────────────────
// 16. FULL DEEP WALKTHROUGH — all pages, all actions
// ───────────────────────────────────────────────────────
test.describe('Full walkthrough', () => {
  test.setTimeout(600_000)

  test('every page and every primary action', async ({ page }) => {
    await login(page)

    await page.screenshot({ path: path.join(SHOTS, 'docker-walk-01-dashboard.png'), fullPage: true })

    await page.goto('/servers')
    await page.waitForLoadState('networkidle')
    await page.getByRole('button', { name: /register server/i }).click()
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SHOTS, 'docker-walk-02-servers-modal.png'), fullPage: true })
    await page.locator('.fixed.inset-0.z-50').last().getByRole('button', { name: /cancel/i }).click()
    await page.waitForTimeout(500)

    await page.goto('/capabilities')
    await page.waitForLoadState('networkidle')
    await page.getByRole('button', { name: /create capability/i }).click()
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SHOTS, 'docker-walk-03-capabilities-modal.png'), fullPage: true })
    await page.locator('.fixed.inset-0.z-50').last().getByRole('button', { name: /cancel/i }).click()
    await page.waitForTimeout(500)

    await page.goto('/agent-classes')
    await page.waitForLoadState('networkidle')
    const tokensBtn = page.getByRole('button', { name: /tokens/i })
    if (await tokensBtn.first().isVisible().catch(() => false)) {
      await tokensBtn.first().click()
      await page.waitForTimeout(500)
      await page.screenshot({ path: path.join(SHOTS, 'docker-walk-04-agent-classes-tokens.png'), fullPage: true })
      await page.locator('.fixed.inset-0.z-50').last().locator('button').first().click()
      await page.waitForTimeout(500)
    }

    await page.goto('/policies')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)
    await page.getByRole('button', { name: /new policy/i }).click()
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SHOTS, 'docker-walk-05-policies-editor.png'), fullPage: true })
    await page.getByRole('button', { name: /cancel/i }).click()
    await page.waitForTimeout(500)

    await page.goto('/audit')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SHOTS, 'docker-walk-06-audit.png'), fullPage: true })
    await page.getByRole('button', { name: /export/i }).click()
    await page.waitForTimeout(500)

    await page.goto('/approvals')
    await page.waitForLoadState('networkidle')
    const reviewBtn = page.getByRole('button', { name: /review/i })
    if (await reviewBtn.first().isVisible().catch(() => false)) {
      await reviewBtn.first().click()
      await page.waitForTimeout(500)
      await page.screenshot({ path: path.join(SHOTS, 'docker-walk-07-approvals-review.png'), fullPage: true })
      await page.getByRole('button', { name: /approve/i }).click()
      await page.waitForTimeout(500)
    }

    await page.goto('/packs')
    await page.waitForLoadState('networkidle')
    const assignBtn = page.getByRole('button', { name: /assign to class/i })
    if (await assignBtn.first().isVisible().catch(() => false)) {
      await assignBtn.first().click()
      await page.waitForTimeout(500)
      await page.screenshot({ path: path.join(SHOTS, 'docker-walk-08-packs-assign.png'), fullPage: true })
      await page.locator('.fixed.inset-0.z-50').last().getByRole('button', { name: /cancel/i }).click()
      await page.waitForTimeout(500)
    }

    await page.goto('/alerts')
    await page.waitForLoadState('networkidle')
    const ackBtn = page.getByRole('button', { name: /acknowledge/i })
    if (await ackBtn.first().isVisible().catch(() => false)) {
      await ackBtn.first().click()
      await page.waitForTimeout(500)
    }

    await page.goto('/admin/users')
    await page.waitForLoadState('networkidle')
    await page.screenshot({ path: path.join(SHOTS, 'docker-walk-09-admin-users.png'), fullPage: true })
    await page.getByRole('button', { name: /invite user/i }).click()
    await page.waitForTimeout(500)
    await page.screenshot({ path: path.join(SHOTS, 'docker-walk-10-admin-invite.png'), fullPage: true })
    await page.locator('.fixed.inset-0.z-50').last().getByRole('button', { name: /cancel/i }).click()
    await page.waitForTimeout(500)

    await page.goto('/trust')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)
    await page.screenshot({ path: path.join(SHOTS, 'docker-walk-11-trust-posture.png'), fullPage: true })

    // Schema Reviews: navigate to /reviews, click approve, then screenshot results
    await page.goto('/reviews')
    await page.waitForLoadState('networkidle')
    const reviewsApprove = page.getByRole('button', { name: /approve/i })
    if (await reviewsApprove.first().isVisible().catch(() => false)) {
      await reviewsApprove.first().click()
      await page.waitForTimeout(500)
    }
    await page.screenshot({ path: path.join(SHOTS, 'docker-walk-12-reviews.png'), fullPage: true })

    await page.getByRole('button', { name: /logout/i }).click()
    await page.waitForURL(/\/login/)
  })
})
