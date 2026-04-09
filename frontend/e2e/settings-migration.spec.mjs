import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url))
const EVIDENCE_DIR = process.env.E2E_EVIDENCE_DIR
  ? path.resolve(TEST_DIR, process.env.E2E_EVIDENCE_DIR)
  : path.resolve(TEST_DIR, '../../docs/evidence/issue-148')
const BASE_URL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173'

if (!fs.existsSync(EVIDENCE_DIR)) {
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true })
}

async function openSettingsPage(page) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'mock-token')
  })
  await page.goto(`${BASE_URL}/settings`)
  await expect(page.getByRole('heading', { name: '设置', exact: true })).toBeVisible()
}

test('settings page only persists backend fields via /api/settings', async ({ page }) => {
  let putPayload = null

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const method = request.method()
    const pathname = new URL(request.url()).pathname

    if (method === 'GET' && pathname === '/api/settings') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ default_provider: 'claude' }),
      })
      return
    }

    if (method === 'PUT' && pathname === '/api/settings') {
      putPayload = JSON.parse(request.postData() ?? '{}')
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Settings updated' }),
      })
      return
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })

  await openSettingsPage(page)

  await page.getByTestId('provider-openai').check()
  await page.getByPlaceholder('输入你的 API Key（留空则不更新）').fill('sk-test-148')
  await page.getByTestId('pref-typewriter').uncheck()
  await page.getByTestId('save-backend-settings').click()

  await expect(page.getByText('后端设置保存成功。')).toBeVisible()
  expect(putPayload).not.toBeNull()
  expect(Object.keys(putPayload).sort()).toEqual(['api_key', 'default_provider'])
  expect(putPayload.default_provider).toBe('openai')
  expect(putPayload.api_key).toBe('sk-test-148')
  await page.screenshot({ path: `${EVIDENCE_DIR}/01-settings-backend-save.png`, fullPage: true })
})

test('local preference toggles persist via localStorage without backend PUT', async ({ page }) => {
  let putCount = 0

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const method = request.method()
    const pathname = new URL(request.url()).pathname

    if (method === 'GET' && pathname === '/api/settings') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ default_provider: 'claude' }),
      })
      return
    }

    if (method === 'PUT' && pathname === '/api/settings') {
      putCount += 1
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Settings updated' }),
      })
      return
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })

  await openSettingsPage(page)

  const typewriterToggle = page.getByTestId('pref-typewriter')
  const autoScrollToggle = page.getByTestId('pref-autoscroll')
  await typewriterToggle.uncheck()
  await autoScrollToggle.uncheck()
  await page.reload()

  await expect(typewriterToggle).not.toBeChecked()
  await expect(autoScrollToggle).not.toBeChecked()
  expect(putCount).toBe(0)
  await page.screenshot({ path: `${EVIDENCE_DIR}/02-settings-local-prefs-persist.png`, fullPage: true })
})
