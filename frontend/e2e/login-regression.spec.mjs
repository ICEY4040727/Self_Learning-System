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

test('login page visual baseline', async ({ page }) => {
  await page.goto(`${BASE_URL}/login`)
  await expect(page.getByRole('heading', { name: '苏 格 拉 底 学 习 系 统' })).toBeVisible()
  await expect(page.getByRole('button', { name: '登录' })).toBeVisible()
  await page.screenshot({ path: `${EVIDENCE_DIR}/01-login-page.png`, fullPage: true })
})
