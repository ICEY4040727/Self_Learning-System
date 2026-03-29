<template>
  <div class="home-scene">
    <!-- 背景星空粒子 -->
    <div class="scene-particles">
      <span v-for="i in 20" :key="i" class="particle" :style="particleStyle(i)" />
    </div>

    <!-- Phase 1: 主菜单 -->
    <Transition name="fade">
      <div v-if="phase === 'menu'" class="menu-phase">
        <h1 class="game-title">苏 格 拉 底 学 习 系 统</h1>
        <nav class="menu-list">
          <a class="menu-item" @click="enterCharacterSelect">开 始 学 习</a>
          <a class="menu-item" @click="router.push('/archive')">档 案 管 理</a>
          <a class="menu-item" @click="router.push('/character')">角 色 设 定</a>
          <a class="menu-item" @click="router.push('/settings')">系 统 设 置</a>
          <a class="menu-item menu-item-muted" @click="handleLogout">退 出 登 录</a>
        </nav>
      </div>
    </Transition>

    <!-- Phase 2: 角色选择 -->
    <Transition name="fade">
      <div v-if="phase === 'character'" class="character-phase">
        <!-- 角色立绘区 -->
        <div class="characters-stage">
          <div
            v-for="char in characters"
            :key="char.id"
            class="stage-character"
            :class="{ selected: selectedCharacter?.id === char.id }"
            @click="selectCharacter(char)"
          >
            <div class="char-sprite">
              {{ char.name?.[0] || '?' }}
            </div>
            <span class="char-label">{{ char.name }}</span>
          </div>
          <div class="stage-character add-character" @click="router.push('/character')">
            <div class="char-sprite char-sprite-add">＋</div>
            <span class="char-label">新 建</span>
          </div>
        </div>

        <!-- 对话框 -->
        <div class="dialog-bar">
          <template v-if="!selectedCharacter">
            <span class="dialog-name">系统</span>
            <p class="dialog-text">选择你今天的学习伙伴</p>
          </template>
          <template v-else>
            <span class="dialog-name">{{ selectedCharacter.name }}</span>
            <div v-if="subjects.length > 0" class="dialog-choices">
              <p class="dialog-text">「今天想学什么呢？」</p>
              <div
                v-for="subj in subjects"
                :key="subj.id"
                class="choice-item"
                @click="startLearning(subj.id)"
              >
                <span class="choice-arrow">▸</span>
                {{ subj.name }}
                <span v-if="subj.description" class="choice-desc">— {{ subj.description }}</span>
              </div>
              <div class="choice-item choice-new" @click="router.push('/character')">
                <span class="choice-arrow">▸</span>
                ＋ 新科目
              </div>
            </div>
            <div v-else class="dialog-choices">
              <p class="dialog-text">「还没有科目呢，去创建一个吧！」</p>
              <div class="choice-item choice-new" @click="router.push('/character')">
                <span class="choice-arrow">▸</span>
                前往角色设定创建科目
              </div>
            </div>
          </template>
        </div>

        <!-- 返回按钮 -->
        <button class="back-btn" @click="phase = 'menu'">← 返回</button>
      </div>
    </Transition>

    <!-- 空白时引导 -->
    <Transition name="fade">
      <div v-if="phase === 'character' && characters.length === 0 && !loadingCharacters" class="empty-guide">
        <p>还没有角色，创建你的第一个 AI 教师吧！</p>
      </div>
    </Transition>

    <!-- 错误提示 -->
    <Transition name="fade">
      <div v-if="errorMessage" class="toast-error">{{ errorMessage }}</div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { parseApiError } from '@/utils/error'
import axios from 'axios'

const router = useRouter()
const authStore = useAuthStore()
const errorMessage = ref('')

const showError = (e: any) => {
  errorMessage.value = parseApiError(e)
  setTimeout(() => { errorMessage.value = '' }, 5000)
}

interface Character {
  id: number
  name: string
  personality?: string
}

interface Subject {
  id: number
  name: string
  description?: string
  target_level?: string
}

const phase = ref<'menu' | 'character'>('menu')
const characters = ref<Character[]>([])
const subjects = ref<Subject[]>([])
const selectedCharacter = ref<Character | null>(null)
const loadingCharacters = ref(false)

const fetchCharacters = async () => {
  loadingCharacters.value = true
  try {
    const response = await axios.get('/api/character')
    characters.value = response.data
  } catch (error) {
    showError(error)
  } finally {
    loadingCharacters.value = false
  }
}

const fetchSubjects = async (characterId: number) => {
  try {
    const response = await axios.get('/api/subjects', {
      params: { character_id: characterId }
    })
    subjects.value = response.data
  } catch (error) {
    showError(error)
  }
}

const enterCharacterSelect = () => {
  phase.value = 'character'
  fetchCharacters()
}

const selectCharacter = (char: Character) => {
  selectedCharacter.value = char
  fetchSubjects(char.id)
}

const startLearning = (subjectId: number) => {
  router.push(`/learning/${subjectId}`)
}

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

const particleStyle = (i: number) => ({
  left: `${(i * 37 + 13) % 100}%`,
  top: `${(i * 53 + 7) % 100}%`,
  animationDelay: `${(i * 0.7) % 5}s`,
  animationDuration: `${3 + (i % 4)}s`,
})

onMounted(() => {
  fetchCharacters()
})
</script>

<style scoped>
.home-scene {
  min-height: 100vh;
  width: 100%;
  position: relative;
  overflow: hidden;
  background: radial-gradient(ellipse at 50% 30%, #1a1a3e 0%, #0a0a1e 70%);
}

/* === 星空粒子 === */
.scene-particles {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.particle {
  position: absolute;
  width: 3px;
  height: 3px;
  background: rgba(255, 215, 0, 0.4);
  border-radius: 50%;
  animation: twinkle 4s ease-in-out infinite;
}

@keyframes twinkle {
  0%, 100% { opacity: 0.2; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.5); }
}

/* === 页面过渡 === */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.4s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* === Phase 1: 主菜单 === */
.menu-phase {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1;
}

.game-title {
  font-family: var(--font-dialogue);
  font-size: 32px;
  color: #ffd700;
  letter-spacing: 8px;
  margin-bottom: 60px;
  animation: titleGlow 3s ease-in-out infinite;
}

@keyframes titleGlow {
  0%, 100% { text-shadow: 0 0 10px rgba(255, 215, 0, 0.3); }
  50% { text-shadow: 0 0 30px rgba(255, 215, 0, 0.6), 0 0 60px rgba(255, 215, 0, 0.2); }
}

.menu-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.menu-item {
  font-family: var(--font-dialogue);
  font-size: 18px;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 6px;
  cursor: pointer;
  transition: all var(--transition-normal);
  text-decoration: none;
  position: relative;
  padding: 4px 0;
}

.menu-item:hover {
  color: #ffd700;
  text-shadow: 0 0 15px rgba(255, 215, 0, 0.5);
  transform: scale(1.05);
}

.menu-item-muted {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.35);
  margin-top: 20px;
}

.menu-item-muted:hover {
  color: rgba(255, 255, 255, 0.7);
  text-shadow: none;
}

/* === Phase 2: 角色选择 === */
.character-phase {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  z-index: 1;
}

.characters-stage {
  flex: 1;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 48px;
  padding-bottom: 40px;
}

.stage-character {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  transition: all var(--transition-normal);
}

.stage-character:hover {
  transform: translateY(-8px);
}

.stage-character.selected {
  transform: translateY(-12px) scale(1.05);
}

.char-sprite {
  width: 100px;
  height: 140px;
  background: linear-gradient(180deg, rgba(74, 74, 138, 0.4) 0%, rgba(42, 42, 74, 0.6) 100%);
  border: 2px solid rgba(74, 74, 138, 0.5);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  color: #ffd700;
  font-family: var(--font-dialogue);
  transition: all var(--transition-normal);
}

.stage-character.selected .char-sprite {
  border-color: #ffd700;
  box-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
}

.stage-character:hover .char-sprite {
  border-color: rgba(255, 215, 0, 0.5);
}

.char-sprite-add {
  border-style: dashed;
  color: rgba(74, 74, 138, 0.8);
  font-size: 28px;
}

.char-sprite-add:hover {
  color: #ffd700;
}

.char-label {
  margin-top: 10px;
  font-family: var(--font-dialogue);
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  letter-spacing: 2px;
}

.stage-character.selected .char-label {
  color: #ffd700;
}

/* === 对话框 (底部横跨式) === */
.dialog-bar {
  position: relative;
  min-height: 160px;
  max-height: 280px;
  background: rgba(0, 0, 0, 0.8);
  border-top: 1px solid rgba(255, 215, 0, 0.2);
  padding: 20px 40px;
  animation: slideUp 0.3s ease-out;
}

.dialog-name {
  display: inline-block;
  font-family: var(--font-dialogue);
  font-size: 15px;
  color: #ffd700;
  margin-bottom: 12px;
  padding: 2px 12px;
  background: linear-gradient(90deg, rgba(255, 215, 0, 0.15), transparent);
  border-left: 2px solid #ffd700;
}

.dialog-text {
  font-family: var(--font-dialogue);
  font-size: 16px;
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.8;
  margin-bottom: 12px;
}

.dialog-choices {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.choice-item {
  font-family: var(--font-dialogue);
  font-size: 15px;
  color: rgba(255, 255, 255, 0.75);
  padding: 10px 16px;
  cursor: pointer;
  transition: all var(--transition-fast);
  border-radius: 4px;
}

.choice-item:hover {
  color: #ffd700;
  background: rgba(255, 215, 0, 0.08);
  padding-left: 24px;
}

.choice-arrow {
  color: rgba(255, 215, 0, 0.6);
  margin-right: 8px;
}

.choice-item:hover .choice-arrow {
  color: #ffd700;
}

.choice-desc {
  color: rgba(255, 255, 255, 0.4);
  font-size: 13px;
  margin-left: 4px;
}

.choice-new {
  color: rgba(255, 255, 255, 0.4);
}

/* === 返回按钮 === */
.back-btn {
  position: absolute;
  top: 20px;
  left: 24px;
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  font-family: var(--font-ui);
  font-size: 14px;
  cursor: pointer;
  z-index: 2;
  transition: color var(--transition-fast);
}

.back-btn:hover {
  color: #ffd700;
}

/* === 空白引导 === */
.empty-guide {
  position: absolute;
  top: 40%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
  font-family: var(--font-dialogue);
  color: rgba(255, 255, 255, 0.5);
  font-size: 16px;
  text-align: center;
}

/* === 错误 toast === */
.toast-error {
  position: fixed;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(223, 74, 74, 0.9);
  color: #fff;
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  z-index: 100;
}

/* === 响应式 === */
@media (max-width: 768px) {
  .game-title {
    font-size: 22px;
    letter-spacing: 4px;
    margin-bottom: 40px;
  }

  .menu-item {
    font-size: 16px;
    letter-spacing: 4px;
  }

  .characters-stage {
    gap: 24px;
  }

  .char-sprite {
    width: 72px;
    height: 100px;
    font-size: 28px;
  }

  .dialog-bar {
    padding: 16px 20px;
  }
}
</style>
