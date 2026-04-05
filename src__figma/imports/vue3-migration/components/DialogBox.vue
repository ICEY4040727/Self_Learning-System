<script setup lang="ts">
/**
 * DialogBox.vue
 * ─────────────────────────────────────────────────────────────
 * ⚠️ backdrop-filter 规则：
 *   父层（.galgame-dialog）永远保持 opacity:1。
 *   Transition 只驱动 translateY，绝不对此组件的父层使用 opacity。
 *   进入/离开动画由调用方的 <Transition name="dialog-slide"> 控制。
 * ─────────────────────────────────────────────────────────────
 */
import {
  ref, watch, onBeforeUnmount, computed, nextTick,
} from 'vue'

// ── Props & Emits ────────────────────────────────────────────
const props = defineProps<{
  mode: 'speaking' | 'input' | 'choices' | 'waiting'
  speakerName: string
  fullText: string
  choices?: string[]
  placeholder?: string
  skipSignal: number          // increment externally to skip typewriter
  typewriterEnabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'continue'): void
  (e: 'choiceSelect', index: number): void
  (e: 'inputSend', text: string): void
}>()

// ── Typewriter state ─────────────────────────────────────────
const displayedText = ref('')
const isTyping      = ref(false)
const inputValue    = ref('')
let   typingTimer: ReturnType<typeof setInterval> | null = null

const TYPEWRITER_INTERVAL = 38  // ms per character

function startTyping(text: string) {
  stopTyping()
  if (!props.typewriterEnabled && props.typewriterEnabled !== undefined) {
    displayedText.value = text
    isTyping.value = false
    return
  }
  displayedText.value = ''
  isTyping.value = true
  let i = 0
  typingTimer = setInterval(() => {
    if (i >= text.length) {
      stopTyping()
      return
    }
    displayedText.value += text[i++]
  }, TYPEWRITER_INTERVAL)
}

function stopTyping() {
  if (typingTimer) { clearInterval(typingTimer); typingTimer = null }
  isTyping.value = false
}

function skipTyping() {
  if (isTyping.value) {
    stopTyping()
    displayedText.value = props.fullText
  }
}

onBeforeUnmount(() => stopTyping())

// ── Watch triggers ────────────────────────────────────────────
watch(
  () => props.fullText,
  (val) => {
    if (props.mode === 'speaking' || props.mode === 'choices') {
      startTyping(val)
    }
  },
  { immediate: true },
)

watch(() => props.mode, (m) => {
  if (m === 'input') {
    stopTyping()
    displayedText.value = ''
    inputValue.value = ''
    nextTick(() => {
      const ta = document.querySelector<HTMLTextAreaElement>('.dialog-textarea')
      ta?.focus()
    })
  }
  if (m === 'waiting') {
    stopTyping()
    displayedText.value = ''
  }
})

watch(() => props.skipSignal, skipTyping)

// ── Click / keyboard handling ─────────────────────────────────
function handleDialogClick() {
  if (props.mode !== 'speaking') return
  if (isTyping.value) {
    skipTyping()
  } else {
    emit('continue')
  }
}

function handleSend() {
  const text = inputValue.value.trim()
  if (!text) return
  emit('inputSend', text)
  inputValue.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

// ── Choice stagger delay ──────────────────────────────────────
function choiceDelay(i: number) {
  return `${i * 0.09}s`
}

const canSend = computed(() => inputValue.value.trim().length > 0)
const isHint  = (c: string) => c.startsWith('💡')
</script>

<template>
  <!--
    .galgame-dialog handles backdrop-filter.
    Parent must NOT transition opacity — only translateY is safe.
  -->
  <div
    class="galgame-dialog"
    style="position:relative;"
    :style="mode === 'speaking' ? { cursor: 'pointer' } : {}"
    @click="handleDialogClick"
  >
    <!-- Name tag (skewed parallelogram) -->
    <div
      class="galgame-name-tag font-ui"
      style="
        position:absolute; top:-34px; left:28px;
        padding:4px 18px 4px 14px;
        clip-path:polygon(0 0,100% 0,calc(100% - 10px) 100%,0 100%);
        font-size:14px; font-weight:600; letter-spacing:3px;
        color:#0a0a1e; user-select:none;
      "
    >
      {{ mode === 'input' ? '我' : speakerName }}
    </div>

    <!-- ── Body ─────────────────────────────────────────────── -->
    <div style="padding:16px 28px 20px;">

      <!-- SPEAKING mode -->
      <template v-if="mode === 'speaking'">
        <p
          class="font-dialogue"
          style="font-size:19px;line-height:1.9;color:#f0f0ff;min-height:60px;"
        >{{ displayedText }}<span
          v-if="isTyping"
          class="bounce-indicator"
          style="margin-left:2px;color:rgba(255,215,0,0.7);"
        >▊</span></p>
        <div
          v-if="!isTyping"
          class="bounce-indicator"
          style="
            position:absolute; bottom:14px; right:20px;
            color:rgba(255,215,0,0.55); font-size:12px;
            font-family:'Noto Sans SC',sans-serif;
          "
        >▼ 点击继续</div>
      </template>

      <!-- CHOICES mode -->
      <template v-else-if="mode === 'choices'">
        <p
          class="font-dialogue"
          style="font-size:18px;line-height:1.85;color:#f0f0ff;margin-bottom:14px;"
        >{{ displayedText }}</p>
        <div class="flex flex-col gap-2" @click.stop>
          <button
            v-for="(choice, i) in choices"
            :key="i"
            class="galgame-choice font-ui text-left"
            :style="{
              animation: `choiceStagger 0.3s ease-out both`,
              animationDelay: choiceDelay(i),
              color: isHint(choice) ? '#60a5fa' : '#f0f0ff',
              fontSize: '15px',
            }"
            @click="emit('choiceSelect', i)"
          >
            <span style="color:rgba(255,215,0,0.6);margin-right:8px;">▸</span>{{ choice }}
          </button>
        </div>
      </template>

      <!-- INPUT mode -->
      <template v-else-if="mode === 'input'">
        <div class="flex flex-col gap-3" @click.stop>
          <textarea
            v-model="inputValue"
            class="galgame-input dialog-textarea font-dialogue w-full"
            :placeholder="placeholder ?? '输入你的想法…'"
            rows="3"
            style="font-size:17px;line-height:1.8;padding:10px 14px;"
            @keydown="handleKeydown"
          />
          <div class="flex justify-end">
            <button
              class="galgame-send-btn font-ui"
              :disabled="!canSend"
              @click="handleSend"
            >→ 发送</button>
          </div>
        </div>
      </template>

      <!-- WAITING mode -->
      <template v-else-if="mode === 'waiting'">
        <div class="flex items-center gap-3" style="min-height:60px;">
          <span class="font-dialogue" style="font-size:24px;letter-spacing:8px;color:rgba(255,215,0,0.6);">
            <span
              v-for="i in 5" :key="i"
              :style="{
                animation: `dotFlash 1.5s ease-in-out ${(i-1)*0.25}s infinite`,
                display: 'inline-block',
              }"
            >·</span>
          </span>
        </div>
      </template>
    </div>
  </div>
</template>
