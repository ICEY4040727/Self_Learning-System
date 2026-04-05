import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url))
const EVIDENCE_DIR = process.env.E2E_EVIDENCE_DIR
  ? path.resolve(TEST_DIR, process.env.E2E_EVIDENCE_DIR)
  : path.resolve(TEST_DIR, '../../docs/evidence/issue-163')
const BASE_URL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173'

if (!fs.existsSync(EVIDENCE_DIR)) {
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true })
}

test('shared style baseline for dialog/hud/backlog/checkpoint', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'mock-token')
  })

  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const method = request.method()
    const pathname = new URL(request.url()).pathname

    if (method === 'POST' && pathname === '/api/courses/1/start') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: 101,
          teacher_persona: 'Shared Style Mentor',
          relationship_stage: 'friend',
          relationship: { stage: 'friend', dimensions: { trust: 0.5, familiarity: 0.5, respect: 0.5, comfort: 0.5 } },
          greeting: '让我们先回顾这个概念。',
          scenes: { default: '/scenes/academy.png' },
          sage_sprites: { default: '/sprites/sage.png' },
          traveler_sprites: { default: '/sprites/traveler.png' },
        }),
      })
      return
    }

    if (method === 'GET' && pathname === '/api/sessions/101/history') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 1, sender_type: 'teacher', content: '欢迎来到共享样式验收。' },
          { id: 2, sender_type: 'user', content: '好的，继续。' },
        ]),
      })
      return
    }

    if (method === 'GET' && pathname === '/api/worlds/1/checkpoints') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 11, world_id: 1, session_id: 101, save_name: '主线存档', message_index: 4, created_at: '2026-04-05T08:00:00Z' },
          { id: 12, world_id: 1, session_id: 101, save_name: '分叉前节点', message_index: 8, created_at: '2026-04-05T08:30:00Z' },
        ]),
      })
      return
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
  })

  await page.goto(`${BASE_URL}/learning/1?worldId=1`)
  await expect(page.locator('.dialog-box')).toBeVisible()
  await expect(page.locator('.hud-bar')).toBeVisible()
  await page.screenshot({ path: `${EVIDENCE_DIR}/02-shared-components-dialog-hud.png`, fullPage: true })

  await page.getByRole('button', { name: /回忆/ }).click()
  await expect(page.locator('.backlog-panel')).toBeVisible()
  await page.screenshot({ path: `${EVIDENCE_DIR}/02-shared-components-backlog-panel.png`, fullPage: true })

  await page.locator('.backlog-overlay').click({ position: { x: 10, y: 10 } })
  await page.getByRole('button', { name: /存档/ }).click()
  await expect(page.locator('.checkpoint-panel')).toBeVisible()
  await page.screenshot({ path: `${EVIDENCE_DIR}/02-shared-components-checkpoint-panel.png`, fullPage: true })
})
