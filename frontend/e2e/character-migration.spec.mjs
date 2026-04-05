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

function deepCopy(value) {
  return JSON.parse(JSON.stringify(value))
}

function createMockState(seed) {
  return {
    user: { id: 1, username: 'e2e-user', role: 'owner' },
    characters: deepCopy(seed.characters ?? [{ id: 1, name: 'Aster', type: 'sage', personality: 'logic-first' }]),
    worlds: deepCopy(seed.worlds ?? []),
    worldCharacterLinks: deepCopy(seed.worldCharacterLinks ?? {}),
    coursesByWorld: deepCopy(seed.coursesByWorld ?? {}),
    nextWorldId: seed.nextWorldId ?? 100,
    nextCourseId: seed.nextCourseId ?? 1000,
    metrics: {
      createdWorlds: 0,
      createdBindings: 0,
      updatedCoursePayloads: [],
      deletedCourseIds: [],
    },
  }
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

function locateCourse(state, courseId) {
  for (const [worldIdRaw, courses] of Object.entries(state.coursesByWorld)) {
    const worldId = Number(worldIdRaw)
    const index = courses.findIndex((course) => course.id === courseId)
    if (index >= 0) {
      return { worldId, index, course: courses[index] }
    }
  }
  return null
}

async function mockCharacterApis(page, state) {
  await page.route('**/api/**', async (route) => {
    const request = route.request()
    const method = request.method()
    const pathname = new URL(request.url()).pathname

    if (method === 'GET' && pathname === '/api/auth/me') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.user) })
      return
    }

    if (method === 'GET' && pathname === '/api/character') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.characters) })
      return
    }

    if (method === 'GET' && pathname === '/api/teacher_persona') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
      return
    }

    if (method === 'GET' && pathname === '/api/worlds') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(state.worlds) })
      return
    }

    const worldCharactersMatch = pathname.match(/^\/api\/worlds\/(\d+)\/characters$/)
    if (method === 'GET' && worldCharactersMatch) {
      const worldId = Number(worldCharactersMatch[1])
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(state.worldCharacterLinks[worldId] ?? []),
      })
      return
    }

    const worldCoursesMatch = pathname.match(/^\/api\/worlds\/(\d+)\/courses$/)
    if (method === 'GET' && worldCoursesMatch) {
      const worldId = Number(worldCoursesMatch[1])
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(state.coursesByWorld[worldId] ?? []),
      })
      return
    }

    if (method === 'POST' && pathname === '/api/worlds') {
      const payload = parseBody(route)
      const world = {
        id: state.nextWorldId++,
        name: payload.name ?? `World-${state.nextWorldId}`,
      }
      state.worlds.push(world)
      state.worldCharacterLinks[world.id] = state.worldCharacterLinks[world.id] ?? []
      state.coursesByWorld[world.id] = state.coursesByWorld[world.id] ?? []
      state.metrics.createdWorlds += 1
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(world) })
      return
    }

    if (method === 'POST' && worldCharactersMatch) {
      const worldId = Number(worldCharactersMatch[1])
      const payload = parseBody(route)
      state.worldCharacterLinks[worldId] = state.worldCharacterLinks[worldId] ?? []
      state.worldCharacterLinks[worldId].push({ character_id: payload.character_id })
      state.metrics.createdBindings += 1
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(payload) })
      return
    }

    if (method === 'POST' && worldCoursesMatch) {
      const worldId = Number(worldCoursesMatch[1])
      const payload = parseBody(route)
      const course = {
        id: state.nextCourseId++,
        world_id: worldId,
        name: payload.name,
        description: payload.description ?? '',
        target_level: payload.target_level ?? '',
      }
      state.coursesByWorld[worldId] = state.coursesByWorld[worldId] ?? []
      state.coursesByWorld[worldId].push(course)
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(course) })
      return
    }

    const courseMatch = pathname.match(/^\/api\/courses\/(\d+)$/)
    if (method === 'PUT' && courseMatch) {
      const courseId = Number(courseMatch[1])
      const payload = parseBody(route)
      const located = locateCourse(state, courseId)
      if (!located) {
        await route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'not found' }) })
        return
      }
      const nextWorldId = Number(payload.world_id)
      const updatedCourse = {
        ...located.course,
        world_id: nextWorldId,
        name: payload.name,
        description: payload.description ?? '',
        target_level: payload.target_level ?? '',
      }
      state.coursesByWorld[located.worldId].splice(located.index, 1)
      state.coursesByWorld[nextWorldId] = state.coursesByWorld[nextWorldId] ?? []
      state.coursesByWorld[nextWorldId].push(updatedCourse)
      state.metrics.updatedCoursePayloads.push(payload)
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(updatedCourse) })
      return
    }

    if (method === 'DELETE' && courseMatch) {
      const courseId = Number(courseMatch[1])
      const located = locateCourse(state, courseId)
      if (located) {
        state.coursesByWorld[located.worldId].splice(located.index, 1)
      }
      state.metrics.deletedCourseIds.push(courseId)
      await route.fulfill({ status: 204, contentType: 'application/json', body: '' })
      return
    }

    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) })
  })
}

async function openCharacterPage(page) {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'mock-token')
  })
  await page.goto(`${BASE_URL}/character`)
  await expect(page.getByRole('heading', { name: '角色设定' })).toBeVisible()
}

async function selectCharacter(page, name) {
  await page.locator('.character-card', { hasText: name }).first().click()
  await expect(page.getByRole('heading', { name: '学习课程' })).toBeVisible()
}

test('character page creates world and binding when creating course without world', async ({ page }) => {
  const state = createMockState({
    worlds: [],
    worldCharacterLinks: {},
    coursesByWorld: {},
  })
  await mockCharacterApis(page, state)
  await openCharacterPage(page)
  await selectCharacter(page, 'Aster')

  await page.getByRole('button', { name: /新建课程/ }).click()
  await expect(page.getByText('保存时将自动创建角色默认世界')).toBeVisible()
  await page.locator('input[placeholder="如：数学、英语"]').fill('Algebra I')
  await page.locator('textarea[placeholder="科目描述"]').fill('auto world creation')
  await page.locator('input[placeholder="如：初级、中级、高级"]').fill('初级')
  await page.locator('.dialog-actions .primary').click()

  await expect(page.locator('.subject-card', { hasText: 'Algebra I' })).toBeVisible()
  expect(state.metrics.createdWorlds).toBe(1)
  expect(state.metrics.createdBindings).toBe(1)
  const createdWorld = state.worlds[0]
  expect(state.worldCharacterLinks[createdWorld.id]).toEqual([{ character_id: 1 }])
  expect((state.coursesByWorld[createdWorld.id] ?? []).map((course) => course.name)).toContain('Algebra I')
  await page.screenshot({ path: `${EVIDENCE_DIR}/08-character-auto-world-binding.png`, fullPage: true })
})

test('character page saves course world_id edit and refreshes listing', async ({ page }) => {
  const state = createMockState({
    worlds: [
      { id: 11, name: 'Alpha World' },
      { id: 12, name: 'Beta World' },
    ],
    worldCharacterLinks: {
      11: [{ character_id: 1 }],
      12: [{ character_id: 1 }],
    },
    coursesByWorld: {
      11: [{ id: 101, world_id: 11, name: 'Linear Algebra', description: 'matrices', target_level: '中级' }],
      12: [],
    },
  })
  await mockCharacterApis(page, state)
  await openCharacterPage(page)
  await selectCharacter(page, 'Aster')

  await page.locator('.subject-card', { hasText: 'Linear Algebra' }).getByRole('button', { name: '编辑' }).click()
  await page.locator('.dialog select').selectOption('12')
  await page.locator('input[placeholder="如：数学、英语"]').fill('Linear Algebra II')
  await page.locator('.dialog-actions .primary').click()

  await expect(page.locator('.subject-card', { hasText: 'Linear Algebra II' })).toBeVisible()
  const lastPayload = state.metrics.updatedCoursePayloads.at(-1)
  expect(lastPayload?.world_id).toBe(12)
  expect((state.coursesByWorld[11] ?? []).some((course) => course.id === 101)).toBe(false)
  expect((state.coursesByWorld[12] ?? []).some((course) => course.name === 'Linear Algebra II')).toBe(true)
  await page.screenshot({ path: `${EVIDENCE_DIR}/09-character-edit-world-course.png`, fullPage: true })
})

test('character page aggregates multi-world courses and updates after delete', async ({ page }) => {
  const state = createMockState({
    worlds: [
      { id: 21, name: 'World-A' },
      { id: 22, name: 'World-B' },
    ],
    worldCharacterLinks: {
      21: [{ character_id: 1 }],
      22: [{ character_id: 1 }],
    },
    coursesByWorld: {
      21: [{ id: 201, world_id: 21, name: 'Calculus', description: 'limits', target_level: '中级' }],
      22: [{ id: 202, world_id: 22, name: 'Physics', description: 'motion', target_level: '初级' }],
    },
  })
  await mockCharacterApis(page, state)
  await openCharacterPage(page)
  await selectCharacter(page, 'Aster')

  await expect(page.locator('.subject-card', { hasText: 'Calculus' })).toBeVisible()
  await expect(page.locator('.subject-card', { hasText: 'Physics' })).toBeVisible()

  page.on('dialog', (dialog) => dialog.accept())
  await page.locator('.subject-card', { hasText: 'Calculus' }).getByRole('button', { name: '删除' }).click()

  await expect(page.locator('.subject-card', { hasText: 'Calculus' })).toHaveCount(0)
  await expect(page.locator('.subject-card', { hasText: 'Physics' })).toBeVisible()
  expect(state.metrics.deletedCourseIds).toContain(201)
  await page.screenshot({ path: `${EVIDENCE_DIR}/10-character-multiworld-delete.png`, fullPage: true })
})
