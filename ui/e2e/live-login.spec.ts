import { test, expect } from '@playwright/test'

test('live login through docker UI', async ({ page }) => {
  await page.goto('/login')

  const textboxes = page.getByRole('textbox')
  await textboxes.nth(0).fill('admin')
  await textboxes.nth(1).fill('Admin123!')

  const loginResponsePromise = page.waitForResponse(
    response => response.url().includes('/v1/auth/login') && response.request().method() === 'POST',
  )

  await page.getByRole('button', { name: 'Login' }).click()

  const loginResponse = await loginResponsePromise
  expect(loginResponse.status()).toBe(200)

  await expect(page).toHaveURL('/')
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
})
