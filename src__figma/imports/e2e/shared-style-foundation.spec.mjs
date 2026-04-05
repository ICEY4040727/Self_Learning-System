/**
 * shared-style-foundation.spec.mjs
 * ──────────────────────────────────────────────────────────────
 * Phase A E2E 视觉验收测试
 *
 * 验证目标：
 *   1. .dialog-box    → DialogBox 可见（transform-only 动画，无 opacity）
 *   2. .hud-bar       → HudBar 可见（同上）
 *   3. .backlog-panel → 点击「回忆」后侧栏滑入（transform-only）
 *   4. .backlog-overlay → 点击暗幕关闭侧栏
 *   5. .checkpoint-panel → 点击「存档」后弹窗出现（panelIn，transform-only）
 *
 * 运行：
 *   E2E_BASE_URL=http://localhost:5173 npx playwright test shared-style-foundation
 *
 * 证据输出：
 *   docs/evidence/issue-163/02-shared-components-dialog-hud.png
 *   docs/evidence/issue-163/02-shared-components-backlog-panel.png
 *   docs/evidence/issue-163/02-shared-components-checkpoint-panel.png
 * ──────────────────────────────────────────────────────────────
 */
import fs   from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

const TEST_DIR    = path.dirname(fileURLToPath(import.meta.url))
const EVIDENCE_DIR = process.env.E2E_EVIDENCE_DIR
  ? path.resolve(TEST_DIR, process.env.E2E_EVIDENCE_DIR)
  : path.resolve(TEST_DIR, '../../docs/evidence/issue-163')
const BASE_URL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173'

if (!fs.existsSync(EVIDENCE_DIR)) {
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true })
}

test('shared style baseline — dialog / hud / backlog / checkpoint', async ({ page }) => {
  // ── 1. 导航到学习页面 ──────────────────────────────────────────
  // 学习页面以模拟数据驱动，不需要真实登录
  await page.goto(`${BASE_URL}/learning`)

  // ── 2. dialog-box 可见 ────────────────────────────────────────
  await expect(page.locator('.dialog-box')).toBeVisible({ timeout: 8000 })

  // ── 3. hud-bar 可见 ───────────────────────────────────────────
  await expect(page.locator('.hud-bar')).toBeVisible({ timeout: 4000 })

  // 截图 #1：dialog + hud
  await page.screenshot({
    path: `${EVIDENCE_DIR}/02-shared-components-dialog-hud.png`,
    fullPage: true,
  })

  // ── 4. 点击「回忆」按钮，backlog 侧栏滑入 ─────────────────────
  await page.getByRole('button', { name: /回忆/ }).click()

  await expect(page.locator('.backlog-panel')).toBeVisible({ timeout: 2000 })

  // 验证没有 opacity 过渡（transform-only 约束）
  // 通过检查 computed style — backlog-panel 不应有 opacity < 1
  const backlogOpacity = await page.locator('.backlog-panel').evaluate(
    el => parseFloat(getComputedStyle(el).opacity)
  )
  expect(backlogOpacity).toBe(1)

  // 截图 #2：backlog panel
  await page.screenshot({
    path: `${EVIDENCE_DIR}/02-shared-components-backlog-panel.png`,
    fullPage: true,
  })

  // ── 5. 点击 backlog-overlay 暗幕，侧栏关闭 ────────────────────
  // 点击暗幕左上角（非面板区域）
  await page.locator('.backlog-overlay').click({ position: { x: 10, y: 10 } })

  // 等待滑出动画完成（260ms）
  await page.waitForTimeout(320)
  await expect(page.locator('.backlog-panel')).not.toBeVisible()

  // ── 6. 点击「存档」按钮，checkpoint-panel 弹窗出现 ────────────
  await page.getByRole('button', { name: /存档/ }).click()

  await expect(page.locator('.checkpoint-panel')).toBeVisible({ timeout: 2000 })

  // 验证 checkpoint-panel 没有 opacity 过渡（panelIn 是纯 transform）
  const cpOpacity = await page.locator('.checkpoint-panel').evaluate(
    el => parseFloat(getComputedStyle(el).opacity)
  )
  expect(cpOpacity).toBe(1)

  // 截图 #3：checkpoint panel
  await page.screenshot({
    path: `${EVIDENCE_DIR}/02-shared-components-checkpoint-panel.png`,
    fullPage: true,
  })
})
