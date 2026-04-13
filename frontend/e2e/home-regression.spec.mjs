import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url))
const EVIDENCE_DIR = process.env.E2E_EVIDENCE_DIR
  ? path.resolve(TEST_DIR, process.env.E2E_EVIDENCE_DIR)
  : path.resolve(TEST_DIR, '../../docs/evidence/issue-149')
const BASE_URL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173'

if (!fs.existsSync(EVIDENCE_DIR)) {
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true })
}

test('home page menu and world-first entry', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'mock-token')
  })

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const method = request.method()
    const pathname = new URL(request.url()).pathname

    if (method === 'GET' && pathname === '/api/worlds') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 1, name: '回归世界', description: 'world-first baseline' },
        ]),
      })
      return
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })

  await page.goto(`${BASE_URL}/home`)
  await expect(page.getByText('知遇')).toBeVisible()
  await page.screenshot({ path: `${EVIDENCE_DIR}/05-home-menu.png`, fullPage: true })

  await page.getByText('开 始 学习').click()
  await expect(page.getByText('界选择', { exact: true })).toBeVisible()
  await expect(page.getByText('回归世界')).toBeVisible()
  await page.screenshot({ path: `${EVIDENCE_DIR}/06-home-world-selection.png`, fullPage: true })
})
