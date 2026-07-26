import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const D = path.resolve(__dirname, '../../docs/ui-test/findings/screenshots')

async function login(page: import('@playwright/test').Page) {
  await page.goto('/login')
  const textboxes = page.getByRole('textbox')
  await textboxes.nth(0).fill('admin')
  await textboxes.nth(1).fill('Admin123!')
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page).toHaveURL('/')
}

test('exercise all UI controls on every page', async ({ page }) => {
  await login(page)

  // ── 1. DASHBOARD ──────────────────────────────────────────────
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  // Click "View all" links
  await page.getByRole('link', { name: 'View all' }).first().click()
  await expect(page).toHaveURL(/\/servers/)
  await page.screenshot({ path: path.join(D, 'ctrl-01-dashboard.png'), fullPage: true })

  // ── 2. SERVERS ────────────────────────────────────────────────
  await page.goto('/servers')
  // Register modal: open, fill, cancel
  await page.getByRole('button', { name: /register server/i }).click()
  await page.locator('input').first().fill('test-server')
  await page.locator('input').nth(1).fill('http://test.example:3000')
  await page.screenshot({ path: path.join(D, 'ctrl-02-servers-register.png'), fullPage: true })
  await page.getByRole('button', { name: 'Cancel' }).click()
  // Filter dropdowns
  const selects = page.locator('select')
  if (await selects.count() >= 2) {
    await selects.nth(0).selectOption('healthy')
    await page.waitForTimeout(300)
    await page.screenshot({ path: path.join(D, 'ctrl-02b-servers-filter.png'), fullPage: true })
    const clearBtn = page.getByRole('button', { name: /clear all/i })
    if (await clearBtn.isVisible()) await clearBtn.click()
  }
  // Search
  await page.getByPlaceholder('Search servers...').fill('demo')
  await page.waitForTimeout(300)
  await page.getByPlaceholder('Search servers...').fill('')

  // ── 3. CAPABILITIES ───────────────────────────────────────────
  await page.goto('/capabilities')
  // Create modal: open, fill name, fill domain, cancel
  await page.getByRole('button', { name: /create capability/i }).click()
  await page.waitForTimeout(200)
  await page.getByRole('button', { name: 'Cancel' }).click()
  // Deprecate button
  const deprecateBtns = page.getByRole('button', { name: 'Deprecate' })
  if (await deprecateBtns.count() > 0) {
    await deprecateBtns.first().click()
    await page.waitForTimeout(200)
    await page.getByRole('button', { name: 'Cancel' }).click()
  }
  // Filter
  const capSelects = page.locator('select')
  if (await capSelects.count() > 0) {
    await capSelects.first().selectOption('knowledge')
    await page.waitForTimeout(300)
  }
  await page.screenshot({ path: path.join(D, 'ctrl-03-capabilities.png'), fullPage: true })

  // ── 4. AGENT CLASSES ──────────────────────────────────────────
  await page.goto('/agent-classes')
  await page.screenshot({ path: path.join(D, 'ctrl-04-agent-classes.png'), fullPage: true })

  // ── 5. POLICIES ───────────────────────────────────────────────
  await page.goto('/policies')
  await page.getByRole('button', { name: /new policy/i }).click()
  await page.waitForTimeout(200)
  const textarea = page.getByRole('textbox')
  if (await textarea.count() > 0) {
    await textarea.fill('package fabric.policy\ndefault allow := true')
    await page.waitForTimeout(200)
    await page.screenshot({ path: path.join(D, 'ctrl-05-policies-edit.png'), fullPage: true })
    await page.getByRole('button', { name: 'Deploy' }).click()
    await page.waitForTimeout(1000)
  } else {
    await page.getByRole('button', { name: 'Cancel' }).click()
  }

  // ── 6. AUDIT LOG ──────────────────────────────────────────────
  await page.goto('/audit')
  await page.waitForTimeout(500)
  await page.screenshot({ path: path.join(D, 'ctrl-06-audit.png'), fullPage: true })

  // ── 7. APPROVALS ──────────────────────────────────────────────
  await page.goto('/approvals')
  await page.waitForTimeout(500)
  await page.screenshot({ path: path.join(D, 'ctrl-07-approvals.png'), fullPage: true })

  // ── 8. CAPABILITY PACKS ───────────────────────────────────────
  await page.goto('/packs')
  await page.getByRole('button', { name: /create pack/i }).click()
  await page.waitForTimeout(200)
  await page.getByRole('button', { name: 'Cancel' }).click()
  // Assign button
  const assignBtns = page.getByRole('button', { name: /assign/i })
  if (await assignBtns.count() > 0) {
    await assignBtns.first().click()
    await page.waitForTimeout(200)
    await page.getByRole('button', { name: 'Cancel' }).click()
  }
  await page.screenshot({ path: path.join(D, 'ctrl-08-packs.png'), fullPage: true })

  // ── 9. ALERTS ─────────────────────────────────────────────────
  await page.goto('/alerts')
  // Acknowledge
  const ackBtns = page.getByRole('button', { name: 'Acknowledge' })
  if (await ackBtns.count() > 0) {
    await ackBtns.first().click()
    await page.waitForTimeout(500)
  }
  await page.screenshot({ path: path.join(D, 'ctrl-09-alerts.png'), fullPage: true })

  // ── 10. ADMIN USERS ───────────────────────────────────────────
  await page.goto('/admin/users')
  // Invite: open, fill, cancel
  await page.getByRole('button', { name: /invite user/i }).click()
  await page.waitForTimeout(200)
  await page.screenshot({ path: path.join(D, 'ctrl-10-admin-invite.png'), fullPage: true })
  await page.getByRole('button', { name: 'Cancel' }).click()
  // Deactivate
  const deactBtns = page.getByRole('button', { name: /deactivate/i })
  if (await deactBtns.count() > 0) {
    await deactBtns.first().click()
    await page.waitForTimeout(300)
  }

  // ── 11. TRUST POSTURE ─────────────────────────────────────────
  await page.goto('/trust')
  await page.waitForTimeout(500)
  await page.screenshot({ path: path.join(D, 'ctrl-11-trust.png'), fullPage: true })

  // ── 12. SCHEMA REVIEWS ──────────────────────────────────────
  // Navigate to /reviews, click the first approve button on a stale mapping,
  // then capture the post-approval state.
  await page.goto('/reviews')
  await page.waitForTimeout(500)
  const approveBtn = page.getByRole('button', { name: /approve/i })
  if (await approveBtn.first().isVisible().catch(() => false)) {
    await approveBtn.first().click()
    await page.waitForTimeout(300)
  }
  await page.screenshot({ path: path.join(D, 'ctrl-12-reviews.png'), fullPage: true })

  // ── LOGOUT ────────────────────────────────────────────────────
  await page.getByRole('button', { name: /logout/i }).click()
  await expect(page).toHaveURL(/\/login/)
})
