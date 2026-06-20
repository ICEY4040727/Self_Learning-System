<template>
  <div class="traveler-flow">
    <!-- Header -->
    <div class="flow-header">
      <div class="flow-subtitle">YOUR AVATAR</div>
      <div class="flow-title">创 建 旅 者</div>
      <p class="flow-desc">这是你在学习世界中的化身</p>
      <div class="gold-line"></div>
    </div>

    <!-- Name + Avatar row -->
    <div class="section">
      <label class="field-label">名 称 <span class="required">*</span></label>
      <input
        v-model="form.name"
        type="text"
        class="galgame-input"
        placeholder="你想叫自己什么？"
        maxlength="20"
      />
    </div>

    <div class="section">
      <label class="field-label">头 像</label>
      <div class="avatar-grid">
        <button
          v-for="avatar in TRAVELER_AVATARS"
          :key="avatar.key"
          type="button"
          class="avatar-btn"
          :class="{ selected: form.avatarKey === avatar.key }"
          @click="form.avatarKey = avatar.key"
        >
          <span class="avatar-emoji">{{ avatar.emoji }}</span>
          <span class="avatar-label">{{ avatar.label }}</span>
        </button>
      </div>
    </div>

    <div class="divider"></div>

    <!-- Personality section -->
    <div class="section">
      <label class="field-label">学 习 风 格</label>
      <div class="trait-grid">
        <button
          v-for="trait in TRAVELER_TRAITS"
          :key="trait"
          type="button"
          class="trait-chip"
          :class="{ selected: form.traits.includes(trait) }"
          @click="toggleTrait(trait)"
        >
          {{ trait }}
        </button>
      </div>
    </div>

    <!-- Title + Background side by side -->
    <div class="two-col">
      <div class="section">
        <label class="field-label">头 衔</label>
        <input
          v-model="form.title"
          type="text"
          class="galgame-input"
          placeholder="如：初级探索者"
          maxlength="20"
        />
      </div>
      <div class="section">
        <label class="field-label">见 面 台 词</label>
        <input
          v-model="form.greeting"
          type="text"
          class="galgame-input"
          placeholder="如：你好，请多指教！"
          maxlength="50"
        />
      </div>
    </div>

    <div class="section">
      <label class="field-label">背 景（想让老师知道你的什么？）</label>
      <textarea
        v-model="form.background"
        class="galgame-input"
        rows="2"
        placeholder="是一名设计师，三十岁开始学编程……"
        maxlength="120"
      ></textarea>
      <div class="char-count">{{ form.background.length }}/120</div>
    </div>

    <!-- Submit -->
    <div class="btn-row">
      <button
        class="submit-btn"
        :disabled="!form.name.trim() || submitting"
        @click="handleSubmit"
      >
        {{ submitting ? '创建中…' : '开始旅程' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { TRAVELER_AVATARS, TRAVELER_TRAITS } from '@/characters/constants/characterPresets'

interface Emits {
  (e: 'create', data: any): void
}

const emit = defineEmits<Emits>()
const submitting = ref(false)

const form = reactive({
  name: '',
  avatarKey: 'traveler1',
  traits: [] as string[],
  background: '',
  title: '',
  greeting: '',
})

const toggleTrait = (trait: string) => {
  const idx = form.traits.indexOf(trait)
  if (idx === -1) {
    if (form.traits.length < 4) form.traits.push(trait)
  } else {
    form.traits.splice(idx, 1)
  }
}

const handleSubmit = async () => {
  if (!form.name.trim()) return
  submitting.value = true
  try {
    const avatar = TRAVELER_AVATARS.find(a => a.key === form.avatarKey)
    emit('create', {
      type: 'traveler',
      name: form.name.trim(),
      avatar: avatar?.emoji,
      tags: [...form.traits],
      background: form.background.trim() || undefined,
      title: form.title.trim() || undefined,
      greeting: form.greeting.trim() || undefined,
      personality: form.traits.length > 0
        ? `学习风格：${form.traits.join('、')}`
        : undefined,
    })
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.traveler-flow {
  padding: 12px 0;
}

.flow-header {
  text-align: center;
  margin-bottom: 16px;
}

.flow-subtitle {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  letter-spacing: 4px;
  color: rgba(255, 255, 255, 0.25);
  margin-bottom: 4px;
}

.flow-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 18px;
  letter-spacing: 6px;
  color: #ffd700;
  margin-bottom: 4px;
}

.flow-desc {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
  margin: 0 0 8px;
}

.gold-line {
  width: 80px;
  height: 1px;
  background: linear-gradient(to right, transparent, rgba(255, 215, 0, 0.4), transparent);
  margin: 0 auto;
}

.divider {
  height: 1px;
  background: rgba(255, 215, 0, 0.1);
  margin: 8px 0;
}

.section {
  margin-bottom: 14px;
}

.field-label {
  display: block;
  font-family: "Noto Sans SC", sans-serif;
  color: rgba(255, 255, 255, 0.5);
  font-size: 11px;
  letter-spacing: 3px;
  margin-bottom: 8px;
}

.required {
  color: #ef4444;
}

.galgame-input {
  width: 100%;
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.4);
  border: 2px solid rgba(255, 215, 0, 0.3);
  border-radius: 8px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
  outline: none;
  transition: border-color 0.2s ease;
}

.galgame-input:focus {
  border-color: rgba(255, 215, 0, 0.7);
}

.galgame-input::placeholder {
  color: rgba(255, 255, 255, 0.25);
}

.char-count {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.3);
  text-align: right;
  margin-top: 4px;
}

.avatar-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.avatar-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 6px;
  background: rgba(0, 0, 0, 0.3);
  border: 2px solid rgba(255, 215, 0, 0.15);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
}

.avatar-btn:hover {
  border-color: rgba(255, 215, 0, 0.4);
  transform: translateY(-2px);
}

.avatar-btn.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.1);
  box-shadow: 0 0 12px rgba(255, 215, 0, 0.1);
}

.avatar-emoji {
  font-size: 28px;
}

.avatar-label {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
}

.avatar-btn.selected .avatar-label {
  color: #ffd700;
}

.trait-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.trait-chip {
  padding: 6px 12px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 16px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.2s ease;
}

.trait-chip:hover {
  border-color: rgba(255, 215, 0, 0.4);
}

.trait-chip.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.12);
  color: #ffd700;
}

.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.btn-row {
  margin-top: 16px;
}

.submit-btn {
  width: 100%;
  padding: 14px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  letter-spacing: 6px;
  font-weight: 600;
  color: #0a0a1e;
  background: linear-gradient(135deg, #ffd700, #f0c000);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.submit-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #ffe033, #ffd700);
  box-shadow: 0 4px 20px rgba(255, 215, 0, 0.35);
  transform: translateY(-1px);
}

.submit-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
