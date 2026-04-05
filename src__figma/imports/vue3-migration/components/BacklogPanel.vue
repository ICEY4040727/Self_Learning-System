<script setup lang="ts">
import { X } from 'lucide-vue-next'
import type { Message } from '@/types'

const props = defineProps<{
  isOpen: boolean
  messages: Message[]
}>()

const emit = defineEmits<{ (e: 'close'): void }>()
</script>

<template>
  <Teleport to="body">
    <Transition name="backlog-slide">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-30"
        style="background:rgba(0,0,0,0.5);"
        @click="emit('close')"
      >
        <!-- Panel slides in from right -->
        <div
          class="galgame-panel absolute top-0 right-0 bottom-0 flex flex-col"
          style="width:340px;max-width:90vw;"
          @click.stop
        >
          <!-- Header -->
          <div
            class="flex items-center justify-between font-ui flex-shrink-0"
            style="padding:16px 20px;border-bottom:1px solid rgba(255,215,0,0.15);"
          >
            <span style="color:#ffd700;font-size:14px;letter-spacing:3px;">📖 回 忆 录</span>
            <button
              style="color:rgba(255,255,255,0.5);cursor:pointer;"
              @click="emit('close')"
            ><X :size="18" /></button>
          </div>

          <!-- Messages -->
          <div
            class="flex-1 overflow-y-auto galgame-scrollbar"
            style="padding:16px 20px;"
          >
            <template v-if="messages.length === 0">
              <div style="color:rgba(255,255,255,0.3);font-size:13px;text-align:center;margin-top:40px;">
                暂无对话记录
              </div>
            </template>
            <div
              v-for="msg in messages"
              :key="msg.id"
              style="margin-bottom:16px;"
            >
              <div
                class="font-ui"
                :style="{
                  fontSize: '11px',
                  letterSpacing: '1px',
                  marginBottom: '4px',
                  color: msg.sender_type === 'user'
                    ? 'rgba(255,215,0,0.7)'
                    : 'rgba(167,139,250,0.8)',
                }"
              >
                {{ msg.sender_type === 'user' ? '我' : '知者' }}
              </div>
              <div
                class="font-dialogue"
                style="font-size:14px;line-height:1.8;color:rgba(240,240,255,0.85);"
              >{{ msg.content }}</div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.backlog-slide-enter-from .galgame-panel { transform: translateX(100%); }
.backlog-slide-enter-active .galgame-panel { transition: transform 0.3s ease-out; }
.backlog-slide-leave-to .galgame-panel { transform: translateX(100%); }
.backlog-slide-leave-active .galgame-panel { transition: transform 0.25s ease-in; }
</style>
