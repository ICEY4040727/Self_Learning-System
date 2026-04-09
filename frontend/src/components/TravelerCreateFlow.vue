<template>
  <div class="traveler-flow">
    <!-- Step Indicator -->
    <div class="step-indicator">
      <div v-for="step in 2" :key="step" class="step-item">
        <div 
          class="step-dot"
          :class="{ active: currentStep === step, completed: currentStep > step }"
        >
          <span v-if="currentStep > step">✓</span>
          <span v-else>{{ step }}</span>
        </div>
        <span class="step-name">{{ stepNames[step - 1] }}</span>
      </div>
    </div>

    <!-- Step 1: Name + Avatar -->
    <div v-if="currentStep === 1" class="step-content">
      <h3 class="step-title">你的化身</h3>
      <p class="step-desc">这是你在学习世界中的代表</p>

      <div class="field-group">
        <label class="field-label">名 称 <span class="required">*</span></label>
        <input 
          v-model="form.name" 
          type="text" 
          class="galgame-input" 
          placeholder="你想叫自己什么？" 
          maxlength="20" 
        />
      </div>

      <div class="field-group">
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
    </div>

    <!-- Step 2: Traits + Background -->
    <div v-else-if="currentStep === 2" class="step-content">
      <h3 class="step-title">性格标签</h3>
      <p class="step-desc">选择你的学习风格（可选）</p>

      <div class="field-group">
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

      <div class="field-group">
        <label class="field-label">背 景（想让老师知道你的什么？）</label>
        <textarea 
          v-model="form.background" 
          class="galgame-input" 
          rows="3"
          placeholder="是一名设计师，三十岁开始学编程……"
          maxlength="80"
        ></textarea>
        <div class="char-count">{{ form.background.length }}/80</div>
      </div>
    </div>

    <!-- Navigation -->
    <div class="nav-buttons">
      <button v-if="currentStep > 1" class="btn-back" @click="currentStep--">
        ← 上一步
      </button>
      <button 
        v-if="currentStep < 2" 
        class="btn-next" 
        :disabled="!form.name.trim()"
        @click="currentStep++"
      >
        下一步 →
      </button>
      <button 
        v-else 
        class="btn-submit"
        :disabled="!form.name.trim() || submitting"
        @click="handleSubmit"
      >
        {{ submitting ? '创建中…' : '创建旅者' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { TRAVELER_AVATARS, TRAVELER_TRAITS } from '@/constants/characterPresets'

interface Emits {
  (e: 'create', data: any): void
}

const emit = defineEmits<Emits>()

const currentStep = ref(1)
const stepNames = ['化身', '性格']
const submitting = ref(false)

const form = reactive({
  name: '',
  avatarKey: 'traveler1',
  traits: [] as string[],
  background: '',
})

const toggleTrait = (trait: string) => {
  const idx = form.traits.indexOf(trait)
  if (idx === -1) {
    if (form.traits.length < 4) {
      form.traits.push(trait)
    }
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
      background: form.background.trim(),
    })
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.traveler-flow {
  padding: 16px 0;
}

/* Step Indicator */
.step-indicator {
  display: flex;
  justify-content: center;
  gap: 48px;
  margin-bottom: 24px;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.step-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  border: 2px solid rgba(255, 215, 0, 0.2);
  color: rgba(255, 255, 255, 0.3);
  transition: all 0.3s ease;
}

.step-dot.active {
  border-color: #ffd700;
  color: #ffd700;
  background: rgba(255, 215, 0, 0.1);
}

.step-dot.completed {
  border-color: #10b981;
  background: #10b981;
  color: white;
}

.step-name {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

/* Step Content */
.step-content {
  animation: fadeIn 0.3s ease;
  min-height: 280px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.step-title {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 16px;
  color: #ffd700;
  text-align: center;
  margin-bottom: 8px;
}

.step-desc {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  text-align: center;
  margin-bottom: 24px;
}

/* Form Elements */
.field-group {
  margin-bottom: 20px;
}

.field-label {
  display: block;
  font-family: "Noto Sans SC", sans-serif;
  color: rgba(255, 255, 255, 0.55);
  font-size: 11px;
  letter-spacing: 3px;
  margin-bottom: 10px;
}

.required {
  color: #ef4444;
}

.galgame-input {
  width: 100%;
  padding: 12px 14px;
  background: rgba(0, 0, 0, 0.4);
  border: 2px solid rgba(255, 215, 0, 0.4);
  border-radius: 8px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: white;
  outline: none;
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

/* Avatar Grid */
.avatar-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.avatar-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 8px;
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
}

.avatar-emoji {
  font-size: 32px;
}

.avatar-label {
  font-family: "Noto Sans SC", sans-serif;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.6);
}

.avatar-btn.selected .avatar-label {
  color: #ffd700;
}

/* Trait Grid */
.trait-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.trait-chip {
  padding: 8px 14px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 20px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all 0.2s ease;
}

.trait-chip:hover {
  border-color: rgba(255, 215, 0, 0.4);
}

.trait-chip.selected {
  border-color: #ffd700;
  background: rgba(255, 215, 0, 0.15);
  color: #ffd700;
}

/* Navigation Buttons */
.nav-buttons {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.btn-back {
  flex: 1;
  padding: 14px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 215, 0, 0.2);
  border-radius: 8px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-back:hover {
  color: rgba(255, 255, 255, 0.8);
  border-color: rgba(255, 215, 0, 0.4);
}

.btn-next {
  flex: 2;
  padding: 14px;
  background: linear-gradient(135deg, #ffd700, #f0c000);
  border: none;
  border-radius: 8px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 2px;
  color: #0a0a1e;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-next:hover:not(:disabled) {
  box-shadow: 0 4px 20px rgba(255, 215, 0, 0.3);
}

.btn-next:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-submit {
  flex: 2;
  padding: 14px;
  background: linear-gradient(135deg, #ffd700, #f0c000);
  border: none;
  border-radius: 8px;
  font-family: "Noto Sans SC", sans-serif;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 2px;
  color: #0a0a1e;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-submit:hover:not(:disabled) {
  box-shadow: 0 4px 20px rgba(255, 215, 0, 0.35);
}

.btn-submit:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
