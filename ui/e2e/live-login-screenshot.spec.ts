import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const SCREENSHOT_PATH = path.resolve(__dirname, '../../docs/ui-test/findings/screenshots/live-login-dashboard.png')

test('login and capture live dashboard screenshot', async ({ page }) => {
  await page.goto('/login')

  const textboxes = page.getByRole('textbox')
  await textboxes.nth(0).fill('admin')
  await textboxes.nth(1).fill('Admin123!')

  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page).toHaveURL('/')
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()

  await page.screenshot({ path: SCREENSHOT_PATH, fullPage: true })
})
