import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url))
const EVIDENCE_DIR = process.env.E2E_EVIDENCE_DIR
  ? path.resolve(TEST_DIR, process.env.E2E_EVIDENCE_DIR)
  : path.resolve(TEST_DIR, '../../docs/evidence/issue-127')
const BASE_URL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173'

if (!fs.existsSync(EVIDENCE_DIR)) {
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true })
}

async function mockLearningApis(page) {
  let graphCallCount = 0
  await page.route('**/api/**', async (route) => {
    const url = route.request().url()
    const method = route.request().method()

    if (method === 'POST' && /\/api\/courses\/\d+\/start$/.test(url)) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: 101,
          teacher_persona: 'UI Persona',
          course: 'UI Course',
          relationship_stage: 'stranger',
          relationship: {
            dimensions: { trust: 0, familiarity: 0, respect: 0, comfort: 0 },
            stage: 'stranger',
            history: [],
          },
          greeting: '准备好开始学习了吗？',
          scenes: { default: '/scenes/academy.png' },
          sage_sprites: { default: '/sprites/sage.png' },
          traveler_sprites: { default: '/sprites/traveler.png' },
        }),
      })
      return
    }

    if (method === 'GET' && /\/api\/sessions\/101\/history$/.test(url)) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
      return
    }

    if (method === 'GET' && /\/api\/worlds\/1\/knowledge-graph/.test(url)) {
      graphCallCount += 1
      const payload = {
        nodes: [
          { id: 'recursion', name: '递归', mastery: 0.7, status: 'learning', type: 'knowledge' },
          { id: 'base_case', name: '终止条件', mastery: 0.6, status: 'learning', type: 'knowledge' },
        ],
        edges: [
          { source: 'recursion', target: 'base_case', type: graphCallCount > 1 ? 'prerequisite' : 'related_to' },
        ],
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(payload),
      })
      return
    }

    if (method === 'GET' && /\/api\/courses\/\d+$/.test(url)) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 1, world_id: 1, name: 'UI Course' }),
      })
      return
    }

    if (method === 'POST' && /\/api\/courses\/\d+\/chat$/.test(url)) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          type: 'text',
          reply: '我们继续思考：终止条件为什么重要？',
          emotion: { emotion_type: 'curiosity' },
          relationship_stage: 'acquaintance',
          relationship_events: [],
          expression_hint: 'thinking',
        }),
      })
      return
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({}),
    })
  })
}

test('knowledge graph renders and node click reveals detail', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'mock-token')
  })
  await mockLearningApis(page)

  await page.goto(`${BASE_URL}/learning/1?worldId=1`)
  await page.getByRole('button', { name: '📊 图谱' }).click()
  await expect(page.locator('.graph-svg')).toBeVisible()
  await expect(page.locator('.graph-svg circle').first()).toBeVisible()
  await page.locator('.graph-svg circle').first().click()
  await expect(page.locator('.node-detail')).toContainText('递归')
  await page.locator('input[type="datetime-local"]').fill('2026-04-05T00:00')
  await page.getByRole('button', { name: '刷新图谱' }).click()
  await expect(page.locator('.legend')).toContainText('prerequisite')
  await page.screenshot({ path: `${EVIDENCE_DIR}/03-knowledge-graph-node-click.png`, fullPage: true })
})

test.describe('mobile viewport adaptation', () => {
  test.use({ viewport: { width: 390, height: 844 } })

  test('learning page applies mobile layout for dual-role scene', async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('token', 'mock-token')
    })
    await mockLearningApis(page)

    await page.goto(`${BASE_URL}/learning/1?worldId=1`)
    await expect(page.locator('.character-layer')).toBeVisible()
    const transform = await page.locator('.character-layer').evaluate((el) => getComputedStyle(el).transform)
    expect(transform).not.toBe('none')
    await expect(page.locator('.dialog-layer')).toBeVisible()
    await page.screenshot({ path: `${EVIDENCE_DIR}/04-learning-mobile-layout.png`, fullPage: true })
  })
})
