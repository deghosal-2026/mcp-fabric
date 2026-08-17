import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const D = path.resolve(__dirname, '../../docs/ui-test/findings/screenshots')

test.beforeEach(async ({ page }) => {
  await page.route(/\/v1\/packs\/.+\/security-metrics$/, async route => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 'pck-1', name: 'Developer Tools', resource_count: 16, total_resources_in_domain: 512, implied_catch_rate: 0.97, warning_tier: 'strong' }) })
  })
  await page.route('**/v1/admin/trust-posture/pack-breadth', async route => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([
      { agent_class_id: 'cls-1', agent_class_name: 'Developer Agents', pack_count: 2, resources_covered: 16, total_resources_in_domain: 512, catch_rate: 0.9706 },
      { agent_class_id: 'cls-2', agent_class_name: 'Ops Agents', pack_count: 1, resources_covered: 500, total_resources_in_domain: 512, catch_rate: 0.02 },
    ]) })
  })
})

async function login(page: import('@playwright/test').Page) {
  await page.goto('/login')
  const textboxes = page.getByRole('textbox')
  await textboxes.nth(0).fill('admin')
  await textboxes.nth(1).fill('Admin123!')
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page).toHaveURL('/')
}

test('full UI exercise — every page, every action, approve/deny', async ({ page }) => {
  await login(page)

  // ── Dashboard ──────────────────────────────────────────────────
  await page.getByRole('link', { name: /Dashboard/ }).click()
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'ex-01-dashboard.png'), fullPage: true })

  // ── Servers ────────────────────────────────────────────────────
  await page.getByRole('link', { name: /Servers/ }).click()
  await expect(page.getByRole('heading', { name: 'Servers' })).toBeVisible()
  await page.getByRole('button', { name: /register server/i }).click()
  await page.waitForTimeout(300)
  await page.screenshot({ path: path.join(D, 'ex-02-servers-register.png'), fullPage: true })
  await page.getByRole('button', { name: 'Cancel' }).click()

  // ── Capabilities ───────────────────────────────────────────────
  await page.getByRole('link', { name: /Capabilities/ }).click()
  await expect(page.getByRole('heading', { name: 'Capability Catalog' })).toBeVisible()
  await page.getByRole('button', { name: /create capability/i }).click()
  await page.waitForTimeout(300)
  await page.screenshot({ path: path.join(D, 'ex-03-capabilities-modal.png'), fullPage: true })
  await page.getByRole('button', { name: 'Cancel' }).click()

  // ── Agent Classes ──────────────────────────────────────────────
  await page.getByRole('link', { name: /Agent Classes/ }).click()
  await expect(page.getByRole('heading', { name: 'Agent Classes' })).toBeVisible()
  await page.getByRole('button', { name: /create agent class/i }).click()
  await page.waitForTimeout(300)
  await page.screenshot({ path: path.join(D, 'ex-04-agent-classes.png'), fullPage: true })
  await page.getByRole('button', { name: 'Cancel' }).click()

  // ── Policies ───────────────────────────────────────────────────
  await page.getByRole('link', { name: /Policies/ }).click()
  await expect(page.getByRole('heading', { name: 'Policy Editor' })).toBeVisible()
  await page.getByRole('button', { name: /new policy/i }).click()
  await page.waitForTimeout(300)
  await page.screenshot({ path: path.join(D, 'ex-05-policies-editor.png'), fullPage: true })
  await page.getByRole('button', { name: 'Cancel' }).click()

  // ── Audit Log ──────────────────────────────────────────────────
  await page.getByRole('link', { name: /Audit Log/ }).click()
  await expect(page.getByRole('heading', { name: 'Audit Log' })).toBeVisible()
  await page.getByRole('button', { name: 'Export' }).click()
  await page.waitForTimeout(300)
  await page.screenshot({ path: path.join(D, 'ex-06-audit.png'), fullPage: true })

  // ── Approvals ──────────────────────────────────────────────────
  await page.getByRole('link', { name: /Approvals/ }).click()
  await expect(page.getByRole('heading', { name: 'Approvals' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'ex-07-approvals-list.png'), fullPage: true })

  const reviewBtns = page.getByRole('button', { name: 'Review' })
  if (await reviewBtns.count() > 0) {
    await reviewBtns.first().click()
    await page.waitForTimeout(300)
    await page.screenshot({ path: path.join(D, 'ex-07b-approvals-review.png'), fullPage: true })
    await page.getByRole('button', { name: 'Approve' }).click()
    await page.waitForTimeout(500)
  }

  // Reload to close the review panel before interacting with the next approval
  await page.reload()
  await page.waitForTimeout(1000)
  const reviewBtns2 = page.getByRole('button', { name: 'Review' })
  if (await reviewBtns2.count() > 0) {
    await reviewBtns2.first().click()
    await page.waitForTimeout(300)
    await page.getByRole('button', { name: 'Deny' }).click()
    await page.waitForTimeout(500)
  }
  await page.screenshot({ path: path.join(D, 'ex-07c-approvals-after.png'), fullPage: true })

  // ── Capability Packs ───────────────────────────────────────────
  await page.getByRole('link', { name: /Capability Packs/ }).click()
  await expect(page.getByRole('heading', { name: 'Capability Packs' })).toBeVisible()
  await page.getByRole('button', { name: /create pack/i }).click()
  await page.waitForTimeout(300)
  await page.screenshot({ path: path.join(D, 'ex-08-packs-modal.png'), fullPage: true })
  await page.getByRole('button', { name: 'Cancel' }).click()
  await page.getByRole('button', { name: /bindings/i }).first().click()
  await page.waitForTimeout(2000)
  // Verify a PackBreadthWarning tier label rendered (tier depends on pack data)
  const tierLabelRegex = /No resources — no risk|Full coverage|Strong coverage|Moderate coverage|Reduced coverage|Low coverage/
  await expect(page.getByText(tierLabelRegex)).toBeVisible()
  await expect(page.getByText('Pack granularity guide')).toBeVisible()

  // ── Alerts ─────────────────────────────────────────────────────
  // Navigate directly to avoid the bindings modal intercepting sidebar clicks
  await page.goto('/alerts')
  await expect(page.getByRole('heading', { name: 'Alerts' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'ex-09-alerts.png'), fullPage: true })

  // ── Admin Users ────────────────────────────────────────────────
  await page.getByRole('link', { name: /Admin Users/ }).click()
  await expect(page.getByRole('heading', { name: 'Admin Users' })).toBeVisible()
  await page.getByRole('button', { name: /invite user/i }).click()
  await page.waitForTimeout(300)
  await page.screenshot({ path: path.join(D, 'ex-10-admin-invite.png'), fullPage: true })
  await page.getByRole('button', { name: 'Cancel' }).click()

  // ── Trust Posture ──────────────────────────────────────────────
  await page.getByRole('link', { name: /Trust Posture/ }).click()
  await expect(page.getByRole('heading', { name: 'Trust Posture' })).toBeVisible()
  await expect(page.getByText('Identity-Binding Coverage')).toBeVisible()
  await expect(page.getByText('Developer Agents')).toBeVisible()
  await expect(page.getByText('Ops Agents')).toBeVisible()
  await expect(page.getByText('97.1%')).toBeVisible()
  await expect(page.getByText('2.0%')).toBeVisible()
  await page.screenshot({ path: path.join(D, 'ex-11-trust-posture.png'), fullPage: true })

  // ── Schema Reviews ───────────────────────────────────────────
  // Navigate to the stale mapping review page, click approve on the first
  // pending review, then capture the result.
  await page.goto('/reviews')
  await expect(page.getByText(/Pending Schema Reviews/i)).toBeVisible()
  const approveBtn = page.getByRole('button', { name: /approve/i })
  if (await approveBtn.first().isVisible().catch(() => false)) {
    await approveBtn.first().click()
    await page.waitForTimeout(300)
  }
  await page.screenshot({ path: path.join(D, 'ex-12-reviews.png'), fullPage: true })

  // ── Logout ─────────────────────────────────────────────────────
  await page.getByRole('button', { name: /logout/i }).click()
  await expect(page).toHaveURL(/\/login/)
})
