# Phase A 涉及源码汇总（含文件与行号范围）

> 说明：以下为本次 Phase A 涉及的**全部源码文件**，并标注了文件路径与行号范围。  
> 行内前缀 `N.` 即对应源文件第 N 行内容。

---

## 1) `frontend/e2e/shared-style-foundation.spec.mjs`（行 1-85）

```text
1. import fs from 'node:fs'
2. import path from 'node:path'
3. import { fileURLToPath } from 'node:url'
4. import { expect, test } from '@playwright/test'
5. 
6. const TEST_DIR = path.dirname(fileURLToPath(import.meta.url))
7. const EVIDENCE_DIR = process.env.E2E_EVIDENCE_DIR
8.   ? path.resolve(TEST_DIR, process.env.E2E_EVIDENCE_DIR)
9.   : path.resolve(TEST_DIR, '../../docs/evidence/issue-163')
10. const BASE_URL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:5173'
11. 
12. if (!fs.existsSync(EVIDENCE_DIR)) {
13.   fs.mkdirSync(EVIDENCE_DIR, { recursive: true })
14. }
15. 
16. test('shared style baseline for dialog/hud/backlog/checkpoint', async ({ page }) => {
17.   await page.addInitScript(() => {
18.     localStorage.setItem('token', 'mock-token')
19.   })
20. 
21.   await page.route('**/api/**', async (route) => {
22.     const request = route.request()
23.     const method = request.method()
24.     const pathname = new URL(request.url()).pathname
25. 
26.     if (method === 'POST' && pathname === '/api/courses/1/start') {
27.       await route.fulfill({
28.         status: 200,
29.         contentType: 'application/json',
30.         body: JSON.stringify({
31.           session_id: 101,
32.           teacher_persona: 'Shared Style Mentor',
33.           relationship_stage: 'friend',
34.           relationship: { stage: 'friend', dimensions: { trust: 0.5, familiarity: 0.5, respect: 0.5, comfort: 0.5 } },
35.           greeting: '让我们先回顾这个概念。',
36.           scenes: { default: '/scenes/academy.png' },
37.           sage_sprites: { default: '/sprites/sage.png' },
38.           traveler_sprites: { default: '/sprites/traveler.png' },
39.         }),
40.       })
41.       return
42.     }
43. 
44.     if (method === 'GET' && pathname === '/api/sessions/101/history') {
45.       await route.fulfill({
46.         status: 200,
47.         contentType: 'application/json',
48.         body: JSON.stringify([
49.           { id: 1, sender_type: 'teacher', content: '欢迎来到共享样式验收。' },
50.           { id: 2, sender_type: 'user', content: '好的，继续。' },
51.         ]),
52.       })
53.       return
54.     }
55. 
56.     if (method === 'GET' && pathname === '/api/worlds/1/checkpoints') {
57.       await route.fulfill({
58.         status: 200,
59.         contentType: 'application/json',
60.         body: JSON.stringify([
61.           { id: 11, world_id: 1, session_id: 101, save_name: '主线存档', message_index: 4, created_at: '2026-04-05T08:00:00Z' },
62.           { id: 12, world_id: 1, session_id: 101, save_name: '分叉前节点', message_index: 8, created_at: '2026-04-05T08:30:00Z' },
63.         ]),
64.       })
65.       return
66.     }
67. 
68.     await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
69.   })
70. 
71.   await page.goto(`${BASE_URL}/learning/1?worldId=1`)
72.   await expect(page.locator('.dialog-box')).toBeVisible()
73.   await expect(page.locator('.hud-bar')).toBeVisible()
74.   await page.screenshot({ path: `${EVIDENCE_DIR}/02-shared-components-dialog-hud.png`, fullPage: true })
75. 
76.   await page.getByRole('button', { name: /回忆/ }).click()
77.   await expect(page.locator('.backlog-panel')).toBeVisible()
78.   await page.screenshot({ path: `${EVIDENCE_DIR}/02-shared-components-backlog-panel.png`, fullPage: true })
79. 
80.   await page.locator('.backlog-overlay').click({ position: { x: 10, y: 10 } })
81.   await page.getByRole('button', { name: /存档/ }).click()
82.   await expect(page.locator('.checkpoint-panel')).toBeVisible()
83.   await page.screenshot({ path: `${EVIDENCE_DIR}/02-shared-components-checkpoint-panel.png`, fullPage: true })
84. })
85. 
```

---

## 2) `frontend/src/App.vue`（行 1-26）

```text
1. <template>
2.   <RouterView v-slot="{ Component }">
3.     <Transition name="page-fade" mode="out-in">
4.       <component :is="Component" />
5.     </Transition>
6.   </RouterView>
7. </template>
8. 
9. <script setup lang="ts">
10. </script>
11. 
12. <style>
13. .page-fade-enter-from,
14. .page-fade-leave-to {
15.   opacity: 0;
16. }
17. 
18. .page-fade-enter-active {
19.   transition: opacity var(--transition-page, 0.4s ease);
20. }
21. 
22. .page-fade-leave-active {
23.   transition: opacity 0.3s ease;
24. }
25. </style>
26. 
```

---

## 3) `frontend/src/assets/main.css`（行 1-371）

```text
1. /* === Galgame style foundation === */
2. /* Fonts are loaded via <link> in index.html for non-blocking rendering. */
3. 
4. :root {
5.   /* Background */
6.   --bg-primary: #0a0a1e;
7.   --bg-secondary: #1a1a2e;
8.   --bg-panel: rgba(0, 0, 0, 0.85);
9.   --panel-bg-soft: rgba(12, 14, 30, 0.72);
10.   --panel-bg-strong: rgba(8, 10, 20, 0.84);
11. 
12.   /* Text */
13.   --text-primary: #ffffff;
14.   --text-secondary: #aaaaaa;
15.   --text-muted: #666666;
16. 
17.   /* Accent */
18.   --accent-gold: #ffd700;
19.   --accent-orange: #ff8c00;
20. 
21.   /* Emotion */
22.   --emotion-positive: #4adf6a;
23.   --emotion-negative: #df4a4a;
24.   --emotion-thinking: #60a5fa;
25.   --emotion-neutral: #888888;
26. 
27.   /* Border */
28.   --border-subtle: #4a4a8a;
29.   --border-accent: #ffd700;
30. 
31.   /* Radius baseline (from UI迁移书) */
32.   --radius-none: 0;
33.   --radius-panel: 14px;
34.   --radius-hud-btn: 5px;
35.   --radius-world-card: 12px;
36.   --radius-modal: 16px;
37. 
38.   /* Blur baseline (from UI迁移书) */
39.   --blur-dialog: 20px;
40.   --blur-panel: 22px;
41.   --blur-hud: 12px;
42.   --blur-login-panel: 22px;
43. 
44.   /* Shadow */
45.   --shadow-soft: 0 6px 20px rgba(0, 0, 0, 0.28);
46.   --shadow-panel: 0 10px 36px rgba(0, 0, 0, 0.35);
47.   --shadow-gold: 0 0 18px rgba(255, 215, 0, 0.32);
48. 
49.   /* Fonts */
50.   --font-dialogue: 'Noto Serif SC', 'Noto Serif CJK SC', serif;
51.   --font-ui: 'Noto Sans SC', 'Noto Sans CJK SC', sans-serif;
52.   --font-code: 'JetBrains Mono', monospace;
53. 
54.   /* Transitions */
55.   --transition-fast: 0.2s ease;
56.   --transition-normal: 0.3s ease;
57.   --transition-slow: 0.5s ease;
58.   --transition-page: 0.4s ease;
59.   --transition-transform: transform var(--transition-normal);
60. }
61. 
62. /* Global reset */
63. *,
64. *::before,
65. *::after {
66.   margin: 0;
67.   padding: 0;
68.   box-sizing: border-box;
69. }
70. 
71. body {
72.   font-family: var(--font-ui);
73.   background: var(--bg-primary);
74.   color: var(--text-primary);
75. }
76. 
77. .galgame-panel,
78. .galgame-dialog,
79. .galgame-dialog-box,
80. .galgame-hud {
81.   /* Keep blur layers transform-driven to avoid backdrop-filter flicker. */
82.   transform: translateZ(0);
83.   will-change: transform;
84.   transition: transform var(--transition-normal), border-color var(--transition-fast), box-shadow var(--transition-fast);
85. }
86. 
87. .galgame-panel {
88.   background: var(--panel-bg-strong);
89.   border: 1px solid var(--border-subtle);
90.   border-radius: var(--radius-panel);
91.   box-shadow: var(--shadow-panel);
92.   backdrop-filter: blur(var(--blur-panel));
93.   -webkit-backdrop-filter: blur(var(--blur-panel));
94. }
95. 
96. .galgame-login-panel {
97.   background: rgba(8, 10, 20, 0.72);
98.   border: 1px solid var(--border-subtle);
99.   border-radius: var(--radius-panel);
100.   box-shadow: var(--shadow-panel);
101.   backdrop-filter: blur(var(--blur-login-panel));
102.   -webkit-backdrop-filter: blur(var(--blur-login-panel));
103.   transform: translateZ(0);
104.   will-change: transform;
105. }
106. 
107. .galgame-dialog,
108. .galgame-dialog-box {
109.   padding: 20px 24px;
110.   border: 1px solid var(--border-accent);
111.   border-radius: 10px;
112.   background: var(--panel-bg-soft);
113.   box-shadow: 0 -4px 30px rgba(0, 0, 0, 0.5);
114.   backdrop-filter: blur(var(--blur-dialog)) saturate(1.5);
115.   -webkit-backdrop-filter: blur(var(--blur-dialog)) saturate(1.5);
116. }
117. 
118. .galgame-name-tag {
119.   background: linear-gradient(135deg, var(--accent-gold), var(--accent-orange));
120.   color: var(--bg-primary);
121.   border-radius: var(--radius-none);
122.   border: 1px solid rgba(0, 0, 0, 0.22);
123.   clip-path: polygon(8% 0, 100% 0, 92% 100%, 0 100%);
124.   font-family: var(--font-ui);
125.   font-weight: 700;
126.   font-size: 14px;
127.   transform: skewX(-8deg);
128. }
129. 
130. .galgame-hud {
131.   background: rgba(0, 0, 0, 0.75);
132.   border-top: 1px solid var(--border-subtle);
133.   backdrop-filter: blur(var(--blur-hud));
134.   -webkit-backdrop-filter: blur(var(--blur-hud));
135. }
136. 
137. .galgame-btn {
138.   border: 1px solid var(--border-subtle);
139.   border-radius: 8px;
140.   color: var(--text-primary);
141.   background: rgba(26, 26, 46, 0.88);
142.   cursor: pointer;
143.   transition: border-color var(--transition-fast), color var(--transition-fast), transform var(--transition-fast), box-shadow var(--transition-fast);
144. }
145. 
146. .galgame-btn:hover:not(:disabled) {
147.   border-color: var(--accent-gold);
148.   color: var(--accent-gold);
149.   transform: translateY(-1px);
150. }
151. 
152. .galgame-btn-primary {
153.   border-color: #4a8a4a;
154.   background: #2f6f2f;
155.   color: #fff;
156. }
157. 
158. .galgame-btn-primary:hover:not(:disabled) {
159.   border-color: #6fcf97;
160.   color: #fff;
161.   box-shadow: 0 0 12px rgba(111, 207, 151, 0.32);
162. }
163. 
164. .galgame-input {
165.   border: 1px solid var(--border-subtle);
166.   border-radius: 8px;
167.   background: rgba(255, 255, 255, 0.05);
168.   color: var(--text-primary);
169.   font-family: var(--font-dialogue);
170.   transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
171. }
172. 
173. .galgame-input:focus {
174.   border-color: var(--accent-gold);
175.   box-shadow: var(--shadow-gold);
176.   outline: none;
177. }
178. 
179. .galgame-menu-item {
180.   padding: 10px 12px;
181.   text-align: left;
182.   font-size: 14px;
183. }
184. 
185. .galgame-world-card {
186.   display: flex;
187.   flex-direction: column;
188.   gap: 4px;
189.   padding: 10px 12px;
190.   border: 1px solid var(--border-subtle);
191.   border-radius: var(--radius-world-card);
192.   color: var(--text-primary);
193.   background: rgba(24, 24, 38, 0.9);
194.   cursor: pointer;
195.   transition: transform var(--transition-fast), border-color var(--transition-fast), box-shadow var(--transition-fast);
196. }
197. 
198. .galgame-world-card:hover {
199.   border-color: var(--accent-gold);
200.   box-shadow: var(--shadow-soft);
201.   transform: translateY(-1px);
202. }
203. 
204. .galgame-choice-item {
205.   animation: choiceStagger var(--transition-normal) both;
206. }
207. 
208. .galgame-hud-btn {
209.   display: inline-flex;
210.   align-items: center;
211.   justify-content: center;
212.   gap: 4px;
213.   border: 1px solid rgba(255, 255, 255, 0.18);
214.   background: rgba(17, 24, 39, 0.72);
215.   border-radius: var(--radius-hud-btn);
216.   color: rgba(255, 255, 255, 0.72);
217.   font-size: 12px;
218.   line-height: 1;
219.   padding: 5px 10px;
220.   transition: border-color var(--transition-fast), color var(--transition-fast), background var(--transition-fast);
221. }
222. 
223. .galgame-hud-btn:hover {
224.   border-color: rgba(255, 215, 0, 0.65);
225.   color: rgba(255, 215, 0, 0.95);
226.   background: rgba(255, 215, 0, 0.08);
227. }
228. 
229. .galgame-hud-btn.active {
230.   border-color: rgba(74, 223, 106, 0.65);
231.   color: rgba(74, 223, 106, 0.95);
232.   background: rgba(74, 223, 106, 0.12);
233. }
234. 
235. .galgame-scrollbar {
236.   scrollbar-width: thin;
237.   scrollbar-color: rgba(255, 215, 0, 0.35) rgba(255, 255, 255, 0.05);
238. }
239. 
240. .galgame-scrollbar::-webkit-scrollbar {
241.   width: 8px;
242.   height: 8px;
243. }
244. 
245. .galgame-scrollbar::-webkit-scrollbar-track {
246.   background: rgba(255, 255, 255, 0.04);
247.   border-radius: 999px;
248. }
249. 
250. .galgame-scrollbar::-webkit-scrollbar-thumb {
251.   background: linear-gradient(180deg, rgba(255, 215, 0, 0.7), rgba(255, 140, 0, 0.45));
252.   border-radius: 999px;
253. }
254. 
255. .dialog-slide-enter-from,
256. .dialog-slide-leave-to {
257.   transform: translateY(14px);
258. }
259. 
260. .dialog-slide-enter-active {
261.   transition: transform var(--transition-normal);
262. }
263. 
264. .dialog-slide-leave-active {
265.   transition: transform 0.24s ease;
266. }
267. 
268. /* Global animations */
269. @keyframes blink {
270.   0%,
271.   50% {
272.     opacity: 1;
273.   }
274.   51%,
275.   100% {
276.     opacity: 0;
277.   }
278. }
279. 
280. @keyframes slideInRight {
281.   from {
282.     transform: translateX(100%);
283.   }
284.   to {
285.     transform: translateX(0);
286.   }
287. }
288. 
289. @keyframes fadeSlideIn {
290.   from {
291.     opacity: 0;
292.     transform: translateX(-30px);
293.   }
294.   to {
295.     opacity: 1;
296.     transform: translateX(0);
297.   }
298. }
299. 
300. @keyframes flash {
301.   0% {
302.     background-color: var(--accent-gold);
303.   }
304.   100% {
305.     background-color: transparent;
306.   }
307. }
308. 
309. @keyframes breathe {
310.   0%,
311.   100% {
312.     opacity: 0.6;
313.   }
314.   50% {
315.     opacity: 1;
316.   }
317. }
318. 
319. @keyframes breatheGlow {
320.   0%,
321.   100% {
322.     box-shadow: 0 0 0 rgba(255, 215, 0, 0);
323.   }
324.   50% {
325.     box-shadow: 0 0 18px rgba(255, 215, 0, 0.3);
326.   }
327. }
328. 
329. @keyframes floatParticle {
330.   0% {
331.     transform: translateY(0) scale(1);
332.   }
333.   50% {
334.     transform: translateY(-8px) scale(1.03);
335.   }
336.   100% {
337.     transform: translateY(0) scale(1);
338.   }
339. }
340. 
341. @keyframes dotFlash {
342.   0%,
343.   80%,
344.   100% {
345.     opacity: 0.2;
346.   }
347.   40% {
348.     opacity: 1;
349.   }
350. }
351. 
352. @keyframes panelIn {
353.   from {
354.     transform: translateY(16px);
355.   }
356.   to {
357.     transform: translateY(0);
358.   }
359. }
360. 
361. @keyframes choiceStagger {
362.   from {
363.     transform: translateX(12px);
364.     opacity: 0;
365.   }
366.   to {
367.     transform: translateX(0);
368.     opacity: 1;
369.   }
370. }
371. 
```

---

## 4) `frontend/src/components/galgame/BacklogPanel.vue`（行 1-158）

```text
1. <template>
2.   <Transition name="backlog-slide">
3.     <div v-if="visible" class="backlog-overlay" @click="$emit('close')">
4.       <div class="backlog-panel galgame-panel" @click.stop>
5.         <h3 class="backlog-title">📖 回忆录</h3>
6.         <div class="backlog-list galgame-scrollbar" ref="listRef">
7.           <div
8.             v-for="msg in messages"
9.             :key="msg.id"
10.             :class="['backlog-entry', msg.sender_type]"
11.           >
12.             <span class="backlog-sender">
13.               {{ msg.sender_type === 'teacher' ? teacherName : '我' }}
14.             </span>
15.             <p class="backlog-text">{{ msg.content }}</p>
16.           </div>
17.           <div v-if="messages.length === 0" class="backlog-empty">
18.             暂无对话记录
19.           </div>
20.         </div>
21.       </div>
22.     </div>
23.   </Transition>
24. </template>
25. 
26. <script setup lang="ts">
27. import { ref, watch, nextTick } from 'vue'
28. 
29. interface Message {
30.   id: number
31.   sender_type: 'user' | 'teacher'
32.   content: string
33. }
34. 
35. const props = defineProps<{
36.   visible: boolean
37.   messages: Message[]
38.   teacherName: string
39. }>()
40. 
41. defineEmits<{ close: [] }>()
42. 
43. const listRef = ref<HTMLElement | null>(null)
44. 
45. // Scroll to bottom when opened
46. watch(() => props.visible, (v) => {
47.   if (v) {
48.     nextTick(() => {
49.       if (listRef.value) {
50.         listRef.value.scrollTop = listRef.value.scrollHeight
51.       }
52.     })
53.   }
54. })
55. </script>
56. 
57. <style scoped>
58. .backlog-overlay {
59.   position: fixed;
60.   inset: 0;
61.   background: rgba(0, 0, 0, 0.5);
62.   z-index: 50;
63.   display: flex;
64.   justify-content: flex-end;
65. }
66. 
67. .backlog-panel {
68.   width: min(360px, 90vw);
69.   height: 100%;
70.   display: flex;
71.   flex-direction: column;
72.   border-radius: 0;
73.   border-right: none;
74.   padding: 20px;
75. }
76. 
77. .backlog-title {
78.   color: var(--accent-gold);
79.   font-family: var(--font-ui);
80.   font-size: 18px;
81.   margin-bottom: 16px;
82.   padding-bottom: 10px;
83.   border-bottom: 1px solid var(--border-subtle);
84. }
85. 
86. .backlog-list {
87.   flex: 1;
88.   overflow-y: auto;
89.   display: flex;
90.   flex-direction: column;
91.   gap: 14px;
92. }
93. 
94. .backlog-entry {
95.   padding: 10px 14px;
96.   border-radius: 4px;
97. }
98. 
99. .backlog-entry.teacher {
100.   background: rgba(255, 215, 0, 0.05);
101.   border-left: 3px solid var(--accent-gold);
102. }
103. 
104. .backlog-entry.user {
105.   background: rgba(74, 138, 74, 0.08);
106.   border-left: 3px solid var(--emotion-positive);
107. }
108. 
109. .backlog-sender {
110.   display: block;
111.   font-family: var(--font-ui);
112.   font-size: 12px;
113.   color: var(--text-muted);
114.   margin-bottom: 4px;
115. }
116. 
117. .backlog-entry.teacher .backlog-sender {
118.   color: var(--accent-gold);
119. }
120. 
121. .backlog-text {
122.   font-family: var(--font-dialogue);
123.   font-size: 14px;
124.   color: var(--text-primary);
125.   line-height: 1.7;
126.   white-space: pre-wrap;
127. }
128. 
129. .backlog-empty {
130.   color: var(--text-muted);
131.   text-align: center;
132.   padding: 40px 0;
133. }
134. 
135. /* Transition */
136. .backlog-slide-enter-from .backlog-panel {
137.   transform: translateX(100%);
138. }
139. 
140. .backlog-slide-enter-active .backlog-panel {
141.   transition: transform var(--transition-normal);
142. }
143. 
144. .backlog-slide-leave-to .backlog-panel {
145.   transform: translateX(100%);
146. }
147. 
148. .backlog-slide-leave-active .backlog-panel {
149.   transition: transform 0.24s ease;
150. }
151. 
152. @media (max-width: 768px) {
153.   .backlog-panel {
154.     width: 85%;
155.   }
156. }
157. </style>
158. 
```

---

## 5) `frontend/src/components/galgame/CheckpointPanel.vue`（行 1-275）

```text
1. <template>
2.   <div class="checkpoint-overlay" @click.self="$emit('close')">
3.     <div class="checkpoint-panel galgame-panel">
4.       <div class="header">
5.         <h3>Checkpoint</h3>
6.         <button class="close-btn" @click="$emit('close')">✕</button>
7.       </div>
8. 
9.       <div class="tabs">
10.           <button class="galgame-hud-btn" :class="{ active: mode === 'commit' }" @click="mode = 'commit'">COMMIT</button>
11.           <button class="galgame-hud-btn" :class="{ active: mode === 'branch' }" @click="mode = 'branch'">BRANCH</button>
12.       </div>
13. 
14.       <div v-if="errorMessage" class="error">{{ errorMessage }}</div>
15. 
16.       <div class="list galgame-scrollbar">
17.         <button
18.           v-for="checkpoint in checkpoints"
19.           :key="checkpoint.id"
20.           class="checkpoint-item galgame-world-card"
21.           :class="{ selected: selectedCheckpointId === checkpoint.id }"
22.           @click="selectedCheckpointId = checkpoint.id"
23.         >
24.           <span>{{ checkpoint.save_name }}</span>
25.           <small>{{ formatDate(checkpoint.created_at) }}</small>
26.         </button>
27.         <div v-if="checkpoints.length === 0" class="empty">暂无 checkpoint</div>
28.       </div>
29. 
30.       <div class="actions">
31.         <template v-if="mode === 'commit'">
32.           <input v-model="saveName" class="galgame-input" placeholder="checkpoint 名称" />
33.           <button class="primary galgame-btn galgame-btn-primary" :disabled="!saveName.trim() || pending" @click="commitCheckpoint">
34.             {{ pending ? '提交中...' : '创建 Checkpoint' }}
35.           </button>
36.         </template>
37.         <template v-else>
38.           <input v-model="branchName" class="galgame-input" placeholder="分支名称（可选）" />
39.           <button class="primary galgame-btn galgame-btn-primary" :disabled="!selectedCheckpointId || pending" @click="branchFromCheckpoint">
40.             {{ pending ? '分叉中...' : '从选中 Checkpoint 分叉' }}
41.           </button>
42.         </template>
43.       </div>
44.     </div>
45.   </div>
46. </template>
47. 
48. <script setup lang="ts">
49. import { onMounted, ref, watch } from 'vue'
50. import axios from 'axios'
51. import { useAuthStore } from '@/stores/auth'
52. import { parseApiError } from '@/utils/error'
53. 
54. interface CheckpointItem {
55.   id: number
56.   world_id: number
57.   session_id: number | null
58.   save_name: string
59.   message_index: number
60.   created_at: string
61. }
62. 
63. interface BranchResult {
64.   session_id: number
65.   course_id: number
66.   world_id: number
67.   parent_checkpoint_id: number
68.   branch_name: string
69. }
70. 
71. const props = defineProps<{
72.   worldId: number
73.   sessionId?: number
74.   initialMode?: 'commit' | 'branch'
75. }>()
76. 
77. const emit = defineEmits<{
78.   close: []
79.   branched: [payload: BranchResult]
80.   committed: [payload: CheckpointItem]
81. }>()
82. 
83. const authStore = useAuthStore()
84. const mode = ref<'commit' | 'branch'>(props.initialMode ?? 'commit')
85. const checkpoints = ref<CheckpointItem[]>([])
86. const selectedCheckpointId = ref<number | null>(null)
87. const saveName = ref('')
88. const branchName = ref('')
89. const pending = ref(false)
90. const errorMessage = ref('')
91. 
92. const headers = () => ({ Authorization: `Bearer ${authStore.token}` })
93. 
94. const fetchCheckpoints = async () => {
95.   try {
96.     const response = await axios.get(`/api/worlds/${props.worldId}/checkpoints`, { headers: headers() })
97.     checkpoints.value = Array.isArray(response.data) ? response.data : []
98.     if (checkpoints.value.length > 0 && selectedCheckpointId.value == null) {
99.       selectedCheckpointId.value = checkpoints.value[0].id
100.     }
101.   } catch (error) {
102.     errorMessage.value = parseApiError(error)
103.   }
104. }
105. 
106. const commitCheckpoint = async () => {
107.   pending.value = true
108.   errorMessage.value = ''
109.   try {
110.     const response = await axios.post(
111.       '/api/checkpoints',
112.       {
113.         world_id: props.worldId,
114.         session_id: props.sessionId,
115.         save_name: saveName.value.trim(),
116.       },
117.       { headers: headers() },
118.     )
119.     saveName.value = ''
120.     await fetchCheckpoints()
121.     emit('committed', response.data as CheckpointItem)
122.   } catch (error) {
123.     errorMessage.value = parseApiError(error)
124.   } finally {
125.     pending.value = false
126.   }
127. }
128. 
129. const branchFromCheckpoint = async () => {
130.   if (!selectedCheckpointId.value) return
131.   pending.value = true
132.   errorMessage.value = ''
133.   try {
134.     const response = await axios.post(
135.       `/api/checkpoints/${selectedCheckpointId.value}/branch`,
136.       { branch_name: branchName.value.trim() || undefined },
137.       { headers: headers() },
138.     )
139.     emit('branched', response.data as BranchResult)
140.   } catch (error) {
141.     errorMessage.value = parseApiError(error)
142.   } finally {
143.     pending.value = false
144.   }
145. }
146. 
147. const formatDate = (value: string): string => {
148.   const date = new Date(value)
149.   if (Number.isNaN(date.getTime())) return value
150.   return date.toLocaleString('zh-CN')
151. }
152. 
153. onMounted(() => {
154.   void fetchCheckpoints()
155. })
156. 
157. watch(
158.   () => props.initialMode,
159.   (nextMode) => {
160.     if (nextMode) mode.value = nextMode
161.   },
162. )
163. </script>
164. 
165. <style scoped>
166. .checkpoint-overlay {
167.   position: fixed;
168.   inset: 0;
169.   background: rgba(0, 0, 0, 0.66);
170.   backdrop-filter: blur(2px);
171.   display: flex;
172.   justify-content: center;
173.   align-items: center;
174.   z-index: 1000;
175. }
176. 
177. .checkpoint-panel {
178.   width: min(560px, 92vw);
179.   padding: 14px;
180.   border-radius: var(--radius-modal);
181.   animation: panelIn var(--transition-normal);
182. }
183. 
184. .header {
185.   display: flex;
186.   justify-content: space-between;
187.   align-items: center;
188.   margin-bottom: 10px;
189. }
190. 
191. .header h3 {
192.   color: var(--accent-gold);
193. }
194. 
195. .close-btn {
196.   border: 1px solid rgba(255, 255, 255, 0.14);
197.   background: rgba(17, 24, 39, 0.6);
198.   color: var(--text-secondary);
199.   border-radius: 8px;
200.   width: 28px;
201.   height: 28px;
202.   cursor: pointer;
203. }
204. 
205. .tabs {
206.   display: flex;
207.   gap: 8px;
208.   margin-bottom: 10px;
209. }
210. 
211. .tabs button {
212.   padding: 6px 10px;
213. }
214. 
215. .tabs button.active {
216.   border-color: rgba(74, 223, 106, 0.65);
217.   color: var(--emotion-positive);
218. }
219. 
220. .list {
221.   display: flex;
222.   flex-direction: column;
223.   gap: 6px;
224.   max-height: 250px;
225.   overflow-y: auto;
226. }
227. 
228. .checkpoint-item {
229.   display: flex;
230.   justify-content: space-between;
231. }
232. 
233. .checkpoint-item small {
234.   color: var(--text-muted);
235.   font-size: 12px;
236. }
237. 
238. .checkpoint-item.selected {
239.   border-color: var(--accent-gold);
240. }
241. 
242. .actions {
243.   margin-top: 12px;
244.   display: flex;
245.   gap: 8px;
246. }
247. 
248. .actions input {
249.   flex: 1;
250.   padding: 8px 10px;
251. }
252. 
253. .primary {
254.   padding: 8px 12px;
255.   white-space: nowrap;
256. }
257. 
258. .primary:disabled {
259.   opacity: 0.6;
260.   cursor: not-allowed;
261. }
262. 
263. .error {
264.   color: #ff8b8b;
265.   font-size: 13px;
266.   margin-bottom: 8px;
267. }
268. 
269. .empty {
270.   color: var(--text-muted);
271.   font-size: 13px;
272.   padding: 8px 0;
273. }
274. </style>
275. 
```

---

## 6) `frontend/src/components/galgame/DialogBox.vue`（行 1-233）

```text
1. <template>
2.   <div class="dialog-box galgame-dialog galgame-dialog-box galgame-scrollbar" @click="handleClick">
3.     <!-- Name tag -->
4.     <div class="name-tag galgame-name-tag" :class="{ 'name-tag-user': mode === 'USER_INPUT' }">
5.       {{ mode === 'USER_INPUT' ? '我' : characterName }}
6.     </div>
7. 
8.     <!-- Mode: TEACHER_SPEAKING -->
9.     <div v-if="mode === 'TEACHER_SPEAKING'" class="dialog-content">
10.       <div class="dialog-text" style="font-family: var(--font-dialogue);">
11.         <span v-html="displayContent"></span>
12.         <span v-if="isTyping" class="cursor">▊</span>
13.       </div>
14.       <div v-if="!isTyping && displayContent" class="next-indicator">
15.         {{ hasMoreSegments ? '▼ 下一段' : '▶ 点击继续' }}
16.       </div>
17.     </div>
18. 
19.     <!-- Mode: USER_INPUT -->
20.     <div v-else-if="mode === 'USER_INPUT'" class="dialog-content input-mode">
21.       <textarea
22.         ref="inputRef"
23.         v-model="inputValue"
24.         class="dialog-input galgame-input"
25.         placeholder="输入你的想法..."
26.         rows="2"
27.         @keydown.enter.exact.prevent="handleSend"
28.         @click.stop
29.       ></textarea>
30.       <button class="send-btn galgame-btn" @click.stop="handleSend" :disabled="!inputValue.trim()">→</button>
31.     </div>
32. 
33.     <!-- Mode: CHOICES -->
34.     <div v-else-if="mode === 'CHOICES'" class="dialog-content">
35.       <div class="dialog-text" style="font-family: var(--font-dialogue);">
36.         <span v-html="displayContent"></span>
37.       </div>
38.       <div class="choices-list">
39.         <button
40.           v-for="(choice, i) in choices"
41.           :key="i"
42.           class="choice-item galgame-choice-item"
43.           :style="{ animationDelay: `${i * 0.1}s` }"
44.           @click.stop="$emit('select-choice', choice)"
45.         >
46.           ▸ {{ choice }}
47.         </button>
48.       </div>
49.     </div>
50. 
51.     <!-- Mode: WAITING -->
52.     <div v-else-if="mode === 'WAITING'" class="dialog-content">
53.       <div class="dialog-text waiting-text" style="font-family: var(--font-dialogue);">
54.         ……
55.       </div>
56.     </div>
57.   </div>
58. </template>
59. 
60. <script setup lang="ts">
61. import { ref, nextTick, watch } from 'vue'
62. 
63. const props = defineProps<{
64.   mode: 'TEACHER_SPEAKING' | 'USER_INPUT' | 'CHOICES' | 'WAITING'
65.   characterName: string
66.   hasMoreSegments?: boolean
67.   displayContent?: string
68.   isTyping?: boolean
69.   choices?: string[]
70. }>()
71. 
72. const emit = defineEmits<{
73.   'click-next': []
74.   'send-message': [message: string]
75.   'select-choice': [choice: string]
76.   'skip-typing': []
77. }>()
78. 
79. const inputValue = ref('')
80. const inputRef = ref<HTMLTextAreaElement | null>(null)
81. 
82. // Auto-focus input when switching to USER_INPUT mode
83. watch(() => props.mode, (newMode) => {
84.   if (newMode === 'USER_INPUT') {
85.     nextTick(() => inputRef.value?.focus())
86.   }
87. })
88. 
89. const handleClick = () => {
90.   if (props.mode === 'TEACHER_SPEAKING') {
91.     if (props.isTyping) {
92.       emit('skip-typing')
93.     } else {
94.       emit('click-next')
95.     }
96.   }
97. }
98. 
99. const handleSend = () => {
100.   if (!inputValue.value.trim()) return
101.   emit('send-message', inputValue.value.trim())
102.   inputValue.value = ''
103. }
104. </script>
105. 
106. <style scoped>
107. .dialog-box {
108.   min-height: 160px;
109.   max-height: 240px;
110.   position: relative;
111.   cursor: pointer;
112.   overflow-y: auto;
113. }
114. 
115. /* Name tag */
116. .name-tag {
117.   position: absolute;
118.   top: -14px;
119.   left: 20px;
120.   padding: 3px 16px;
121. }
122. 
123. .name-tag-user {
124.   background: linear-gradient(135deg, var(--emotion-positive), #6aba6a);
125.   color: var(--text-primary);
126. }
127. 
128. /* Dialog text */
129. .dialog-text {
130.   color: var(--text-primary);
131.   font-size: 19px;
132.   line-height: 1.9;
133.   white-space: pre-wrap;
134.   margin-top: 4px;
135. }
136. 
137. .waiting-text {
138.   color: var(--text-muted);
139.   animation: breathe 2s ease-in-out infinite;
140. }
141. 
142. .cursor {
143.   animation: blink 1s infinite;
144.   color: var(--accent-gold);
145.   margin-left: 2px;
146. }
147. 
148. .next-indicator {
149.   text-align: right;
150.   color: var(--text-muted);
151.   font-size: 12px;
152.   font-family: var(--font-ui);
153.   margin-top: 8px;
154.   animation: breathe 2s ease-in-out infinite;
155.   letter-spacing: 1px;
156. }
157. 
158. /* User input mode */
159. .input-mode {
160.   display: flex;
161.   align-items: flex-end;
162.   gap: 12px;
163. }
164. 
165. .dialog-input {
166.   flex: 1;
167.   font-size: 16px;
168.   line-height: 1.8;
169.   padding: 10px 14px;
170.   resize: none;
171. }
172. 
173. .dialog-input::placeholder {
174.   color: var(--text-muted);
175. }
176. 
177. .send-btn {
178.   width: 44px;
179.   height: 44px;
180.   background: var(--accent-gold);
181.   color: var(--bg-primary);
182.   border-color: rgba(0, 0, 0, 0.15);
183.   border-radius: 8px;
184.   font-size: 20px;
185.   font-weight: bold;
186.   flex-shrink: 0;
187. }
188. 
189. .send-btn:hover:not(:disabled) {
190.   color: var(--bg-primary);
191.   transform: scale(1.1);
192.   box-shadow: 0 0 12px rgba(255, 215, 0, 0.4);
193. }
194. 
195. .send-btn:disabled {
196.   opacity: 0.3;
197.   cursor: not-allowed;
198. }
199. 
200. /* Choices */
201. .choices-list {
202.   display: flex;
203.   flex-direction: column;
204.   gap: 8px;
205.   margin-top: 14px;
206. }
207. 
208. .choice-item {
209.   font-family: var(--font-ui);
210.   font-size: 15px;
211.   padding: 10px 16px;
212.   text-align: left;
213.   border-radius: 8px;
214. }
215. 
216. .choice-item:hover {
217.   border-color: var(--accent-gold);
218.   transform: translateX(6px);
219.   background: rgba(255, 215, 0, 0.08);
220. }
221. 
222. /* Mobile */
223. @media (max-width: 768px) {
224.   .dialog-box {
225.     padding: 16px 18px;
226.     min-height: 140px;
227.   }
228.   .dialog-text {
229.     font-size: 16px;
230.   }
231. }
232. </style>
233. 
```

---

## 7) `frontend/src/components/galgame/HudBar.vue`（行 1-117）

```text
1. <template>
2.   <div class="hud-bar galgame-hud">
3.     <div class="hud-left">
4.       <button class="hud-btn galgame-hud-btn" @click="$emit('save')">💾 存档</button>
5.       <button class="hud-btn galgame-hud-btn" @click="$emit('load')">📂 读档</button>
6.       <button class="hud-btn galgame-hud-btn" @click="$emit('skip')">⏩ 跳过</button>
7.       <button
8.         class="hud-btn galgame-hud-btn"
9.         :class="{ 'hud-btn-active': isAuto, active: isAuto }"
10.         @click="$emit('toggle-auto')"
11.       >▶ 自动</button>
12.       <button class="hud-btn galgame-hud-btn" @click="$emit('backlog')">📖 回忆</button>
13.       <button class="hud-btn galgame-hud-btn" @click="$emit('knowledge-graph')">📊 图谱</button>
14.       <button class="hud-btn galgame-hud-btn" @click="$emit('toggle-ui')">🙈 隐藏UI</button>
15.       <button class="hud-btn galgame-hud-btn" @click="$emit('settings')">⚙ 设置</button>
16.       <button class="hud-btn galgame-hud-btn" @click="$emit('exit')">🏠 主页</button>
17.     </div>
18.     <div class="hud-right">
19.       <slot name="status">
20.         <span class="hud-status">{{ emotionLabel }} │ {{ stageLabel }} │ {{ mastery }}%</span>
21.       </slot>
22.     </div>
23.   </div>
24. </template>
25. 
26. <script setup lang="ts">
27. import { computed } from 'vue'
28. 
29. const props = defineProps<{
30.   emotion?: string
31.   stage?: string
32.   mastery?: number
33.   isAuto?: boolean
34. }>()
35. 
36. defineEmits<{
37.   save: []
38.   load: []
39.   skip: []
40.   'toggle-auto': []
41.   backlog: []
42.   'knowledge-graph': []
43.   'toggle-ui': []
44.   settings: []
45.   exit: []
46. }>()
47. 
48. const EMOTION_LABELS: Record<string, string> = {
49.   curiosity: '好奇', confusion: '困惑', frustration: '沮丧',
50.   excitement: '兴奋', satisfaction: '满足', boredom: '无聊',
51.   anxiety: '焦虑', neutral: '平静',
52. }
53. 
54. const STAGE_LABELS: Record<string, string> = {
55.   stranger: '陌生人', acquaintance: '熟人', friend: '朋友',
56.   mentor: '导师', partner: '伙伴',
57. }
58. 
59. const emotionLabel = computed(() => EMOTION_LABELS[props.emotion || 'neutral'] || '平静')
60. const stageLabel = computed(() => STAGE_LABELS[props.stage || 'stranger'] || '陌生人')
61. const mastery = computed(() => props.mastery ?? 0)
62. </script>
63. 
64. <style scoped>
65. .hud-bar {
66.   position: fixed;
67.   bottom: 0;
68.   left: 0;
69.   right: 0;
70.   height: 40px;
71.   display: flex;
72.   justify-content: space-between;
73.   align-items: center;
74.   padding: 0 12px;
75.   z-index: 30;
76.   font-family: var(--font-ui);
77. }
78. 
79. .hud-left, .hud-right {
80.   display: flex;
81.   align-items: center;
82.   gap: 4px;
83. }
84. 
85. .hud-btn {
86.   font-size: 11px;
87.   padding: 4px 8px;
88.   border-radius: var(--radius-hud-btn);
89.   transition: color var(--transition-fast), border-color var(--transition-fast);
90.   white-space: nowrap;
91. }
92. 
93. .hud-btn:hover {
94.   color: var(--accent-gold);
95. }
96. 
97. .hud-btn-active {
98.   color: var(--emotion-positive);
99. }
100. 
101. .hud-status {
102.   color: var(--text-muted);
103.   font-size: 12px;
104.   white-space: nowrap;
105. }
106. 
107. @media (max-width: 768px) {
108.   .hud-btn {
109.     font-size: 11px;
110.     padding: 4px 6px;
111.   }
112.   .hud-status {
113.     font-size: 11px;
114.   }
115. }
116. </style>
117. 
```

---

## 8) `frontend/src/views/Learning.vue`（行 1-451）

```text
1. <template>
2.   <div class="learning-page">
3.     <div class="scene-bg" :style="sceneStyle" @click="handleSceneClick"></div>
4.     <div class="scene-overlay"></div>
5. 
6.     <div class="character-layer">
7.       <CharacterDisplay :name="teacherName" :sprites="sageSprites" :expression="currentExpression" position="left" />
8.       <CharacterDisplay name="旅者" :sprites="travelerSprites" expression="default" position="right" />
9.     </div>
10. 
11.     <Transition name="dialog-slide">
12.       <div v-if="!uiHidden" class="dialog-layer" @click.stop>
13.         <DialogBox
14.           :mode="dialogMode"
15.           :character-name="teacherName"
16.           :display-content="displayContent"
17.           :is-typing="isTyping"
18.           :has-more-segments="false"
19.           :choices="currentChoices"
20.           @click-next="handleDialogContinue"
21.           @skip-typing="skipTyping"
22.           @send-message="sendMessage"
23.           @select-choice="handleChoice"
24.         />
25.       </div>
26.     </Transition>
27. 
28.     <div v-if="!uiHidden" class="hud-layer" @click.stop>
29.       <HudBar
30.         :emotion="currentEmotion"
31.         :stage="relationshipStage"
32.         :mastery="0"
33.         :is-auto="autoMode"
34.         @save="openCheckpointPanel('commit')"
35.         @load="openCheckpointPanel('branch')"
36.         @skip="handleSkip"
37.         @toggle-auto="toggleAutoMode"
38.         @backlog="showBacklog = true"
39.         @knowledge-graph="showKnowledgeGraph = true"
40.         @toggle-ui="uiHidden = true"
41.         @settings="router.push('/settings')"
42.         @exit="router.push('/home')"
43.       />
44.     </div>
45. 
46.     <button v-if="uiHidden" class="restore-ui" @click="uiHidden = false">🙈 UI已隐藏（点击恢复）</button>
47. 
48.     <div v-if="stageOverlay" class="stage-overlay">{{ stageOverlay }}</div>
49.     <div v-if="narration" class="narration">{{ narration }}</div>
50. 
51.     <BacklogPanel :visible="showBacklog" :messages="messages" :teacher-name="teacherName" @close="showBacklog = false" />
52. 
53.     <CheckpointPanel
54.       v-if="showCheckpointPanel"
55.       :world-id="worldId"
56.       :session-id="sessionId"
57.       :initial-mode="checkpointMode"
58.       @close="showCheckpointPanel = false"
59.       @branched="handleBranched"
60.     />
61. 
62.     <div v-if="showKnowledgeGraph" class="modal" @click.self="showKnowledgeGraph = false">
63.       <div class="modal-panel galgame-panel">
64.         <button class="close" @click="showKnowledgeGraph = false">✕</button>
65.         <KnowledgeGraph :world-id="worldId" :session-id="sessionId" />
66.       </div>
67.     </div>
68.   </div>
69. </template>
70. 
71. <script setup lang="ts">
72. import { computed, onBeforeUnmount, ref, watch } from 'vue'
73. import { useRoute, useRouter } from 'vue-router'
74. import axios from 'axios'
75. import CharacterDisplay from '@/components/galgame/CharacterDisplay.vue'
76. import DialogBox from '@/components/galgame/DialogBox.vue'
77. import HudBar from '@/components/galgame/HudBar.vue'
78. import BacklogPanel from '@/components/galgame/BacklogPanel.vue'
79. import CheckpointPanel from '@/components/galgame/CheckpointPanel.vue'
80. import KnowledgeGraph from '@/components/KnowledgeGraph.vue'
81. import { parseApiError } from '@/utils/error'
82. import { useAuthStore } from '@/stores/auth'
83. import { buildLearningRoute, parseQueryNumber } from '@/utils/navigation'
84. 
85. interface Message {
86.   id: number
87.   sender_type: 'user' | 'teacher'
88.   content: string
89. }
90. 
91. interface LearningStartResponse {
92.   session_id?: number
93.   teacher_persona?: string | null
94.   relationship_stage?: string | null
95.   relationship?: { stage?: string | null } | null
96.   greeting?: string | null
97.   scenes?: Record<string, string> | null
98.   sage_sprites?: Record<string, string> | null
99.   traveler_sprites?: Record<string, string> | null
100.   character_sprites?: Record<string, string> | null
101. }
102. 
103. interface HistoryMessage {
104.   id?: number
105.   sender_type?: string
106.   content?: string
107. }
108. 
109. interface RelationshipEvent {
110.   type?: string
111.   event_type?: string
112.   message?: string
113.   description?: string
114. }
115. 
116. interface ChatResponsePayload {
117.   type?: string
118.   reply?: string
119.   choices?: string[]
120.   emotion?: { emotion_type?: string } | null
121.   relationship_stage?: string | null
122.   relationship?: { stage?: string | null } | null
123.   relationship_events?: RelationshipEvent[] | null
124.   expression_hint?: string | null
125. }
126. 
127. interface BranchPayload {
128.   session_id: number
129.   course_id: number
130.   world_id?: number
131. }
132. 
133. type DialogMode = 'TEACHER_SPEAKING' | 'USER_INPUT' | 'CHOICES' | 'WAITING'
134. type CheckpointMode = 'commit' | 'branch'
135. 
136. const route = useRoute()
137. const router = useRouter()
138. const authStore = useAuthStore()
139. 
140. const courseId = computed(() => Number(route.params.courseId))
141. const worldId = ref(parseQueryNumber(route.query.worldId) ?? 0)
142. const sessionId = ref<number | undefined>(parseQueryNumber(route.query.sessionId))
143. const teacherName = ref('知者')
144. const sageSprites = ref<Record<string, string>>({})
145. const travelerSprites = ref<Record<string, string>>({})
146. const scenes = ref<Record<string, string>>({})
147. const currentExpression = ref('default')
148. const currentEmotion = ref('neutral')
149. const relationshipStage = ref('stranger')
150. const fullTeacherReply = ref('……')
151. const typedTeacherReply = ref('……')
152. const isTyping = ref(false)
153. const currentChoices = ref<string[]>([])
154. const dialogMode = ref<DialogMode>('WAITING')
155. const messages = ref<Message[]>([])
156. const uiHidden = ref(false)
157. const autoMode = ref(false)
158. const showBacklog = ref(false)
159. const showCheckpointPanel = ref(false)
160. const checkpointMode = ref<CheckpointMode>('commit')
161. const showKnowledgeGraph = ref(false)
162. const stageOverlay = ref('')
163. const narration = ref('')
164. 
165. let typingTimer: ReturnType<typeof window.setInterval> | null = null
166. let autoAdvanceTimer: ReturnType<typeof window.setTimeout> | null = null
167. 
168. const headers = () => ({ Authorization: `Bearer ${authStore.token}` })
169. const anyPanelOpen = computed(() => showBacklog.value || showCheckpointPanel.value || showKnowledgeGraph.value)
170. 
171. const sceneStyle = computed(() => {
172.   const stageScene = scenes.value[relationshipStage.value]
173.   const fallback = scenes.value.default || Object.values(scenes.value)[0]
174.   const url = stageScene || fallback
175.   return url
176.     ? { backgroundImage: `url(${url})`, backgroundSize: 'cover', backgroundPosition: 'center' }
177.     : { background: 'radial-gradient(ellipse at bottom, var(--bg-secondary) 0%, var(--bg-primary) 100%)' }
178. })
179. 
180. const displayContent = computed(() => typedTeacherReply.value)
181. 
182. const clearTypingTimer = () => {
183.   if (typingTimer) {
184.     window.clearInterval(typingTimer)
185.     typingTimer = null
186.   }
187. }
188. 
189. const clearAutoAdvanceTimer = () => {
190.   if (autoAdvanceTimer) {
191.     window.clearTimeout(autoAdvanceTimer)
192.     autoAdvanceTimer = null
193.   }
194. }
195. 
196. const startTypewriter = (text: string) => {
197.   clearTypingTimer()
198.   fullTeacherReply.value = text || '……'
199.   typedTeacherReply.value = ''
200.   isTyping.value = true
201. 
202.   if (!fullTeacherReply.value) {
203.     isTyping.value = false
204.     return
205.   }
206. 
207.   let index = 0
208.   typingTimer = window.setInterval(() => {
209.     index += 1
210.     typedTeacherReply.value = fullTeacherReply.value.slice(0, index)
211.     if (index >= fullTeacherReply.value.length) {
212.       clearTypingTimer()
213.       isTyping.value = false
214.     }
215.   }, 38)
216. }
217. 
218. const skipTyping = () => {
219.   if (!isTyping.value) return
220.   clearTypingTimer()
221.   typedTeacherReply.value = fullTeacherReply.value
222.   isTyping.value = false
223. }
224. 
225. const showEvent = (text: string, type: 'stage' | 'narration') => {
226.   if (type === 'stage') {
227.     stageOverlay.value = text
228.     setTimeout(() => (stageOverlay.value = ''), 2000)
229.   } else {
230.     narration.value = text
231.     setTimeout(() => (narration.value = ''), 2800)
232.   }
233. }
234. 
235. const applyRelationship = (data: ChatResponsePayload) => {
236.   if (data.relationship?.stage) relationshipStage.value = data.relationship.stage
237.   if (data.relationship_stage) relationshipStage.value = data.relationship_stage
238.   if (Array.isArray(data.relationship_events)) {
239.     data.relationship_events.forEach((event) => {
240.       const eventType = event.event_type || event.type || ''
241.       const message = event.message || event.description || JSON.stringify(event)
242.       showEvent(message, eventType.includes('stage') ? 'stage' : 'narration')
243.     })
244.   }
245. }
246. 
247. const presentTeacherReply = (reply: string, appendToHistory = true) => {
248.   const normalizedReply = reply || '……'
249.   startTypewriter(normalizedReply)
250.   if (appendToHistory) {
251.     messages.value.push({ id: Date.now(), sender_type: 'teacher', content: normalizedReply })
252.   }
253. }
254. 
255. const resetLearningState = () => {
256.   clearTypingTimer()
257.   clearAutoAdvanceTimer()
258.   messages.value = []
259.   currentChoices.value = []
260.   dialogMode.value = 'WAITING'
261.   fullTeacherReply.value = '……'
262.   typedTeacherReply.value = '……'
263.   isTyping.value = false
264.   currentExpression.value = 'default'
265.   currentEmotion.value = 'neutral'
266. }
267. 
268. const startLearning = async () => {
269.   const startRes = await axios.post<LearningStartResponse>(`/api/courses/${courseId.value}/start`, {}, { headers: headers() })
270.   const data = startRes.data
271.   sessionId.value = data.session_id
272.   teacherName.value = data.teacher_persona || '知者'
273.   sageSprites.value = data.sage_sprites || data.character_sprites || {}
274.   travelerSprites.value = data.traveler_sprites || {}
275.   scenes.value = data.scenes || {}
276.   if (data.relationship?.stage) relationshipStage.value = data.relationship.stage
277.   if (data.relationship_stage) relationshipStage.value = data.relationship_stage
278. 
279.   if (sessionId.value) {
280.     const historyRes = await axios.get<HistoryMessage[]>(`/api/sessions/${sessionId.value}/history`, { headers: headers() })
281.     const history = Array.isArray(historyRes.data) ? historyRes.data : []
282.     if (history.length > 0) {
283.       messages.value = history.map((msg) => ({
284.         id: msg.id || Date.now(),
285.         sender_type: msg.sender_type === 'user' ? 'user' : 'teacher',
286.         content: msg.content || '',
287.       }))
288.       const lastTeacher = [...messages.value].reverse().find((msg) => msg.sender_type === 'teacher')
289.       presentTeacherReply(lastTeacher?.content || data.greeting || '准备好开始学习了吗？', false)
290.       dialogMode.value = 'TEACHER_SPEAKING'
291.       return
292.     }
293.   }
294. 
295.   presentTeacherReply(data.greeting || '准备好开始学习了吗？')
296.   dialogMode.value = 'TEACHER_SPEAKING'
297. }
298. 
299. const fetchCourse = async () => {
300.   if (worldId.value) return
301.   const res = await axios.get(`/api/courses/${courseId.value}`, { headers: headers() })
302.   worldId.value = res.data.world_id
303. }
304. 
305. const sendMessage = async (message: string) => {
306.   if (!message.trim()) return
307.   messages.value.push({ id: Date.now(), sender_type: 'user', content: message })
308.   currentChoices.value = []
309.   dialogMode.value = 'WAITING'
310. 
311.   try {
312.     const res = await axios.post<ChatResponsePayload>(`/api/courses/${courseId.value}/chat`, { message }, { headers: headers() })
313.     const data = res.data
314.     currentEmotion.value = data.emotion?.emotion_type || currentEmotion.value
315.     currentExpression.value = data.expression_hint || 'default'
316.     applyRelationship(data)
317. 
318.     const isChoiceReply = data.type === 'choice' || (Array.isArray(data.choices) && data.choices.length > 0)
319.     if (isChoiceReply) {
320.       currentChoices.value = data.choices || []
321.       presentTeacherReply(data.reply || '')
322.       dialogMode.value = 'CHOICES'
323.       return
324.     }
325. 
326.     presentTeacherReply(data.reply || '')
327.     dialogMode.value = 'TEACHER_SPEAKING'
328.   } catch (error) {
329.     presentTeacherReply(parseApiError(error))
330.     dialogMode.value = 'TEACHER_SPEAKING'
331.   }
332. }
333. 
334. const handleChoice = (choice: string) => sendMessage(choice)
335. 
336. const openCheckpointPanel = (mode: CheckpointMode) => {
337.   checkpointMode.value = mode
338.   showCheckpointPanel.value = true
339. }
340. 
341. const handleDialogContinue = () => {
342.   if (dialogMode.value !== 'TEACHER_SPEAKING') return
343.   if (isTyping.value) {
344.     skipTyping()
345.     return
346.   }
347.   dialogMode.value = 'USER_INPUT'
348. }
349. 
350. const handleSkip = () => {
351.   if (dialogMode.value !== 'TEACHER_SPEAKING') return
352.   if (isTyping.value) {
353.     skipTyping()
354.     return
355.   }
356.   dialogMode.value = 'USER_INPUT'
357. }
358. 
359. const toggleAutoMode = () => {
360.   autoMode.value = !autoMode.value
361. }
362. 
363. const handleSceneClick = () => {
364.   if (uiHidden.value) {
365.     uiHidden.value = false
366.     return
367.   }
368.   if (!anyPanelOpen.value) uiHidden.value = true
369. }
370. 
371. const handleBranched = (payload: BranchPayload) => {
372.   showCheckpointPanel.value = false
373.   sessionId.value = payload.session_id
374.   const nextWorldId = payload.world_id || worldId.value
375.   if (payload.course_id !== courseId.value) {
376.     router.push(buildLearningRoute(payload.course_id, {
377.       worldId: nextWorldId,
378.       sessionId: payload.session_id,
379.     }))
380.     return
381.   }
382.   void router.replace(buildLearningRoute(payload.course_id, {
383.     worldId: nextWorldId,
384.     sessionId: payload.session_id,
385.   }))
386. }
387. 
388. const bootstrapLearning = async () => {
389.   worldId.value = parseQueryNumber(route.query.worldId) ?? 0
390.   sessionId.value = parseQueryNumber(route.query.sessionId)
391.   resetLearningState()
392.   try {
393.     await fetchCourse()
394.     await startLearning()
395.   } catch (error) {
396.     showEvent(parseApiError(error), 'narration')
397.     void router.push('/home')
398.   }
399. }
400. 
401. watch(
402.   () => route.fullPath,
403.   () => {
404.     void bootstrapLearning()
405.   },
406.   { immediate: true },
407. )
408. 
409. watch(
410.   () => [autoMode.value, dialogMode.value, isTyping.value, anyPanelOpen.value, uiHidden.value] as const,
411.   ([auto, mode, typing, panelOpen, hidden]) => {
412.     clearAutoAdvanceTimer()
413.     if (!auto || mode !== 'TEACHER_SPEAKING' || typing || panelOpen || hidden) return
414.     autoAdvanceTimer = window.setTimeout(() => {
415.       dialogMode.value = 'USER_INPUT'
416.     }, 2800)
417.   },
418. )
419. 
420. onBeforeUnmount(() => {
421.   clearTypingTimer()
422.   clearAutoAdvanceTimer()
423. })
424. </script>
425. 
426. <style scoped>
427. .learning-page { width: 100vw; height: 100vh; position: relative; overflow: hidden; }
428. .scene-bg { position: absolute; inset: 0; z-index: 0; filter: brightness(.58); }
429. .scene-overlay {
430.   position: absolute;
431.   inset: 0;
432.   z-index: 1;
433.   background: linear-gradient(to bottom, rgba(6, 8, 18, 0.2), rgba(0, 0, 0, 0.35));
434. }
435. .character-layer { position: absolute; left: 0; right: 0; bottom: 220px; z-index: 10; display: flex; justify-content: space-between; padding: 0 5%; pointer-events: none; }
436. .dialog-layer { position: absolute; left: 5%; right: 5%; bottom: 44px; z-index: 20; }
437. .hud-layer { position: fixed; inset: 0; pointer-events: none; z-index: 30; }
438. .hud-layer :deep(.hud-bar) { pointer-events: auto; }
439. .restore-ui { position: fixed; right: 14px; bottom: 56px; z-index: 40; background: rgba(0,0,0,.75); color: #fff; border: 1px solid #4a4a8a; border-radius: var(--radius-hud-btn); padding: 8px 10px; cursor: pointer; }
440. .stage-overlay { position: fixed; inset: 0; z-index: 50; display: flex; align-items: center; justify-content: center; font-size: 36px; color: #ffd700; background: rgba(0,0,0,.65); font-family: var(--font-dialogue); }
441. .narration { position: fixed; right: 5%; bottom: 240px; z-index: 45; background: rgba(0,0,0,.72); border: 1px solid #4a4a8a; border-radius: 10px; padding: 12px 14px; max-width: 360px; }
442. .modal { position: fixed; inset: 0; z-index: 1100; background: rgba(0,0,0,.65); display: flex; align-items: center; justify-content: center; }
443. .modal-panel { width: min(92vw, 980px); max-height: 88vh; overflow: auto; border-radius: var(--radius-modal); padding: 16px; position: relative; }
444. .close { position: absolute; right: 12px; top: 10px; background: none; border: none; color: #aaa; cursor: pointer; font-size: 18px; }
445. @media (max-width: 768px) {
446.   .character-layer { bottom: 180px; transform: scale(.7); transform-origin: bottom center; }
447.   .dialog-layer { left: 2%; right: 2%; }
448.   .narration { right: 2%; max-width: 76vw; }
449. }
450. </style>
451. 
```

