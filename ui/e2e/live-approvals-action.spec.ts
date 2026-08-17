import { test, expect } from '@playwright/test'

async function login(page: import('@playwright/test').Page) {
  await page.goto('/login')
  const textboxes = page.getByRole('textbox')
  await textboxes.nth(0).fill('admin')
  await textboxes.nth(1).fill('Admin123!')
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page).toHaveURL('/')
}

test('approvals review action does not 404', async ({ page }) => {
  await login(page)
  await page.goto('/approvals')

  await expect(page.getByRole('heading', { name: 'Approvals' })).toBeVisible()

  const reviewBtn = page.getByRole('button', { name: 'Review' })
  if ((await reviewBtn.count()) === 0) {
    test.skip(true, 'No pending approvals to review')
    return
  }

  await reviewBtn.first().click()

  const responsePromise = page.waitForResponse(
    response => response.url().includes('/v1/approvals/') && response.request().method() === 'POST',
  )

  await page.getByRole('button', { name: 'Approve' }).click()
  const response = await responsePromise

  expect(response.status()).not.toBe(404)
})
