<template>
  <div class="char-section">
    <!-- Section Header -->
    <div 
      class="section-header-row"
      v-motion
      :initial="{ opacity: 0, x: -20 }"
      :enter="{ opacity: 1, x: 0 }"
    >
      <div class="section-label">
        <span class="font-ui label-cn">{{ label }}</span>
        <span class="font-ui label-en">{{ labelEn }}</span>
      </div>
      <div class="section-accent" :style="{ background: accentColor }"></div>
    </div>

    <!-- Character Grid -->
    <div class="char-grid">
      <TransitionGroup name="char-list">
        <div
          v-for="char in characters"
          :key="char.id"
          class="char-card"
          :style="{ '--accent': accentColor }"
          v-motion
          :initial="{ opacity: 0, scale: 0.9 }"
          :enter="{ opacity: 1, scale: 1 }"
        >
          <!-- Avatar -->
          <div class="char-avatar" :style="{ background: char.color || accentColor }">
            <span class="char-symbol">{{ char.symbol || '?' }}</span>
          </div>

          <!-- Info -->
          <div class="char-info">
            <div class="char-name font-ui">{{ char.name }}</div>
            <div class="char-title font-ui">{{ char.title || '' }}</div>
          </div>

          <!-- Actions -->
          <div class="char-actions" v-if="showDelete || showEdit">
            <button 
              v-if="showEdit"
              class="char-action-btn"
              @click="$emit('edit', char)"
              :title="'编辑'"
            >
              <Settings :size="12" />
            </button>
            <button 
              v-if="showDelete"
              class="char-action-btn delete"
              @click="confirmDelete(char)"
              :title="'删除'"
            >
              <Trash2 :size="12" />
            </button>
          </div>
        </div>
      </TransitionGroup>

      <!-- Empty State -->
      <div v-if="characters.length === 0" class="char-empty">
        <span class="font-ui">暂无{{ labelCn || label }}</span>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <Transition name="modal">
      <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
        <div class="modal-content font-ui">
          <div class="modal-title">确认删除</div>
          <div class="modal-body">
            确定要删除角色 <strong>{{ deleteTarget.name }}</strong> 吗？
          </div>
          <div class="modal-actions">
            <button class="btn-cancel" @click="deleteTarget = null">取消</button>
            <button class="btn-confirm delete" @click="doDelete">确认删除</button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Settings, Trash2 } from 'lucide-vue-next'

interface Character {
  id: number
  name: string
  title?: string
  symbol?: string
  color?: string
  type: string
}

withDefaults(defineProps<{
  label: string
  labelEn: string
  labelCn?: string
  characters: Character[]
  accentColor?: string
  showDelete?: boolean
  showEdit?: boolean
}>(), {
  accentColor: '#ffd700',
  showDelete: false,
  showEdit: false,
})

const emit = defineEmits<{
  delete: [character: Character]
  edit: [character: Character]
}>()

const deleteTarget = ref<Character | null>(null)

function confirmDelete(char: Character) {
  deleteTarget.value = char
}

function doDelete() {
  if (deleteTarget.value) {
    emit('delete', deleteTarget.value)
    deleteTarget.value = null
  }
}
</script>

<style scoped>
.char-section {
  margin-bottom: 24px;
}

.section-header-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.section-label {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.label-cn {
  font-size: 18px;
  color: #ffd700;
  letter-spacing: 4px;
}

.label-en {
  font-size: 10px;
  color: rgba(255, 215, 0, 0.5);
  letter-spacing: 2px;
}

.section-accent {
  flex: 1;
  height: 1px;
  opacity: 0.3;
}

.char-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

.char-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.char-card:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: var(--accent);
  box-shadow: 0 0 20px rgba(var(--accent), 0.2);
  transform: translateY(-2px);
}

.char-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
  border: 2px solid rgba(255, 255, 255, 0.1);
}

.char-symbol {
  font-size: 24px;
  color: rgba(0, 0, 0, 0.6);
}

.char-info {
  text-align: center;
}

.char-name {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 2px;
}

.char-title {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

.char-actions {
  position: absolute;
  top: 6px;
  right: 6px;
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.char-card:hover .char-actions {
  opacity: 1;
}

.char-action-btn {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  border: none;
  border-radius: 4px;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all 0.2s;
}

.char-action-btn:hover {
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
}

.char-action-btn.delete:hover {
  background: rgba(220, 38, 38, 0.6);
  color: #fca5a5;
}

.char-empty {
  grid-column: 1 / -1;
  text-align: center;
  padding: 24px;
  color: rgba(255, 255, 255, 0.3);
  font-size: 13px;
}

/* List transition */
.char-list-move,
.char-list-enter-active,
.char-list-leave-active {
  transition: all 0.4s ease;
}

.char-list-enter-from,
.char-list-leave-to {
  opacity: 0;
  transform: scale(0.8);
}

.char-list-leave-active {
  position: absolute;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: #1a1a2e;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 24px;
  max-width: 320px;
  width: 90%;
}

.modal-title {
  font-size: 16px;
  color: #fff;
  margin-bottom: 12px;
  text-align: center;
}

.modal-body {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 20px;
  text-align: center;
}

.modal-actions {
  display: flex;
  gap: 12px;
}

.modal-actions button {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.7);
}

.btn-cancel:hover {
  background: rgba(255, 255, 255, 0.15);
}

.btn-confirm {
  background: rgba(255, 215, 0, 0.2);
  color: #ffd700;
}

.btn-confirm:hover {
  background: rgba(255, 215, 0, 0.3);
}

.btn-confirm.delete {
  background: rgba(220, 38, 38, 0.2);
  color: #fca5a5;
}

.btn-confirm.delete:hover {
  background: rgba(220, 38, 38, 0.3);
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>
