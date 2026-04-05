import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

const TEST_DIR = path.dirname(fileURLToPath(import.meta.url))
const EVIDENCE_DIR = path.resolve(TEST_DIR, '../../docs/evidence/issue-146')
const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173'

if (!fs.existsSync(EVIDENCE_DIR)) {
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true })
}

function parseBody(route) {
  const raw = route.request().postData()
  if (!raw) return {}
  try {
    return JSON.parse(raw)
  } catch {
    return {}
  }
}

function createMockState() {
  return {
    user: { id: 1, username: 'archive-e2e', role: 'owner' },
    nextDiaryId: 99,
    courses: [
      { id: 1, name: '哲学导论' },
      { id: 2, name: '逻辑学基础' },
    ],
    diaries: [
      { id: 11, course_id: 1, date: '2026-04-05T04:00:00Z', content: '今天梳理了苏格拉底提问链路。', reflection: '要多追问前提。' },
      { id: 12, course_id: 2, date: '2026-04-04T10:30:00Z', content: '完成了命题逻辑练习。', reflection: '' },
    ],
    progress: [
      { id: 21, course_id: 1, topic: '反诘法', mastery_level: 74, next_review: '2026-04-08T03:00:00Z' },
      { id: 22, course_id: 2, topic: '命题演算', mastery_level: 61, next_review: '2026-04-09T06:00:00Z' },
    ],
    saves: [
      { id: 31, save_name: '归纳法-阶段A', created_at: '2026-04-05T03:20:00Z' },
      { id: 32, save_name: '演绎法-阶段B', created_at: '2026-04-04T09:10:00Z' },
    ],
    sessions: [
      { id: 301, started_at: '2026-04-05T03:00:00Z', course_name: '哲学导论' },
      { id: 302, started_at: '2026-04-04T09:00:00Z', course_name: '逻辑学基础' },
    ],
    trajectories: {
      301: [
        { index: 1, timestamp: '2026-04-05T03:00:00Z', emotion_type: 'curiosity', valence: 0.62, arousal: 0.53, confidence: 0.8 },
        { index: 2, timestamp: '2026-04-05T03:02:00Z', emotion_type: 'satisfaction', valence: 0.79, arousal: 0.45, confidence: 0.81 },
        { index: 3, timestamp: '2026-04-05T03:05:00Z', emotion_type: 'confusion', valence: 0.37, arousal: 0.66, confidence: 0.77 },
      ],
      302: [
        { index: 1, timestamp: '2026-04-04T09:00:00Z', emotion_type: 'neutral', valence: 0.5, arousal: 0.4, confidence: 0.7 },
      ],
    },
  }
}

async function mockArchiveApis(page, state) {
  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const method = request.method()
    const url = new URL(request.url())
    const pathname = url.pathname

    if (method === 'GET' && pathname === '/api/auth/me') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.user) })
      return
    }

    if (method === 'GET' && pathname === '/api/courses') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.courses) })
      return
    }

    if (method === 'GET' && pathname === '/api/learning_diary') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.diaries) })
      return
    }

    if (method === 'POST' && pathname === '/api/learning_diary') {
      const payload = parseBody(route)
      const entry = {
        id: state.nextDiaryId++,
        course_id: Number(payload.course_id),
        date: payload.date,
        content: payload.content,
        reflection: payload.reflection ?? '',
      }
      state.diaries.unshift(entry)
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(entry) })
      return
    }

    if (method === 'GET' && pathname === '/api/progress') {
      const courseId = Number(url.searchParams.get('course_id'))
      const list = Number.isInteger(courseId) && courseId > 0
        ? state.progress.filter((item) => item.course_id === courseId)
        : state.progress
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(list) })
      return
    }

    if (method === 'GET' && pathname === '/api/save') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.saves) })
      return
    }

    const saveDeleteMatch = pathname.match(/^\/api\/save\/(\d+)$/)
    if (method === 'DELETE' && saveDeleteMatch) {
      const saveId = Number(saveDeleteMatch[1])
      state.saves = state.saves.filter((item) => item.id !== saveId)
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ message: 'ok' }) })
      return
    }

    const branchMatch = pathname.match(/^\/api\/checkpoints\/(\d+)\/branch$/)
    if (method === 'POST' && branchMatch) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          session_id: 701,
          course_id: 2,
          world_id: 9,
          parent_checkpoint_id: Number(branchMatch[1]),
          branch_name: 'archive-e2e-branch',
        }),
      })
      return
    }

    if (method === 'GET' && pathname === '/api/sessions') {
      const courseId = Number(url.searchParams.get('course_id'))
      const list = Number.isInteger(courseId) && courseId > 0
        ? state.sessions.filter((session) => session.course_name === state.courses.find((course) => course.id === courseId)?.name)
        : state.sessions
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(list) })
      return
    }

    const trajectoryMatch = pathname.match(/^\/api\/sessions\/(\d+)\/emotion_trajectory$/)
    if (method === 'GET' && trajectoryMatch) {
      const sessionId = Number(trajectoryMatch[1])
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(state.trajectories[sessionId] ?? []),
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

test('archive page renders migrated layout and charts', async ({ page }) => {
  const state = createMockState()
  await page.addInitScript(() => localStorage.setItem('token', 'mock-token'))
  await mockArchiveApis(page, state)

  await page.goto(`${BASE_URL}/archive`)
  await expect(page.getByRole('heading', { name: '档 案 管 理' })).toBeVisible()
  await expect(page.locator('.archive-panel')).toHaveCount(4)
  await expect(page.locator('.chart-container').first()).toBeVisible()
  await expect(page.locator('.record-card').first()).toBeVisible()
  await page.screenshot({ path: `${EVIDENCE_DIR}/01-archive-overview.png`, fullPage: true })
})

test('archive diary modal and save branch flow work', async ({ page }) => {
  const state = createMockState()
  await page.addInitScript(() => localStorage.setItem('token', 'mock-token'))
  await mockArchiveApis(page, state)

  await page.goto(`${BASE_URL}/archive`)
  await page.getByRole('button', { name: '写日记' }).click()
  await expect(page.locator('.dialog-panel')).toBeVisible()
  await page.screenshot({ path: `${EVIDENCE_DIR}/02-archive-diary-dialog.png`, fullPage: true })

  await page.locator('.dialog-panel textarea').first().fill('今天补完了 Archive 迁移。')
  await page.locator('.dialog-panel textarea').nth(1).fill('下一步继续优化筛选体验。')
  await page.getByRole('button', { name: '保存日记' }).click()
  await expect(page.locator('.dialog-panel')).toHaveCount(0)
  await expect(page.getByText('今天补完了 Archive 迁移。')).toBeVisible()

  await page.locator('.save-card').first().getByRole('button', { name: '读档分叉' }).click()
  await expect(page).toHaveURL(/\/learning\/2\?worldId=9&sessionId=701/)
})
