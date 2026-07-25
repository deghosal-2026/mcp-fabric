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

test('capture sidebar with all options visible', async ({ page }) => {
  await login(page)
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()

  const sidebar = page.getByRole('complementary')

  // Verify all 11 nav links are present
  await expect(sidebar.getByRole('link', { name: /Dashboard/ })).toBeVisible()
  await expect(sidebar.getByRole('link', { name: /Servers/ })).toBeVisible()
  await expect(sidebar.getByRole('link', { name: /Capabilities/ })).toBeVisible()
  await expect(sidebar.getByRole('link', { name: /Agent Classes/ })).toBeVisible()
  await expect(sidebar.getByRole('link', { name: /Policies/ })).toBeVisible()
  await expect(sidebar.getByRole('link', { name: /Audit Log/ })).toBeVisible()
  await expect(sidebar.getByRole('link', { name: /Approvals/ })).toBeVisible()
  await expect(sidebar.getByRole('link', { name: /Capability Packs/ })).toBeVisible()
  await expect(sidebar.getByRole('link', { name: /Alerts/ })).toBeVisible()
  await expect(sidebar.getByRole('link', { name: /Admin Users/ })).toBeVisible()
  await expect(sidebar.getByRole('link', { name: /Trust Posture/ })).toBeVisible()

  // Screenshot just the sidebar area
  await sidebar.screenshot({ path: path.join(D, 'docker-sidebar-full.png') })

  // Full page with sidebar visible
  await page.screenshot({ path: path.join(D, 'docker-dashboard-with-sidebar.png'), fullPage: true })
})
