<template>
  <div class="dialog-overlay">
    <div class="confirm-dialog">
      <div class="dialog-header">
        <span class="tool-icon">🔧</span>
        <h3>工具调用请求</h3>
      </div>

      <div class="dialog-body">
        <div class="field">
          <label>工具名称</label>
          <div class="value tool-name">{{ tool }}</div>
        </div>

        <div class="field">
          <label>查询内容</label>
          <div class="value query">{{ query }}</div>
        </div>

        <div class="field">
          <label>调用原因</label>
          <div class="value reason">{{ reason }}</div>
        </div>
      </div>

      <div class="dialog-footer">
        <button class="cancel-btn" @click="$emit('cancel')">取消</button>
        <button class="confirm-btn" @click="$emit('confirm')">确认执行</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  tool: string
  query: string
  reason: string
}>()

defineEmits<{
  confirm: []
  cancel: []
}>()
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.confirm-dialog {
  background: linear-gradient(180deg, #2a2a4a 0%, #1a1a2e 100%);
  border: 2px solid #ffd700;
  border-radius: 16px;
  padding: 24px;
  width: 90%;
  max-width: 450px;
  box-shadow: 0 0 30px rgba(255, 215, 0, 0.3);
}

.dialog-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #4a4a8a;
}

.tool-icon {
  font-size: 24px;
}

.dialog-header h3 {
  color: #ffd700;
  margin: 0;
}

.dialog-body {
  margin-bottom: 20px;
}

.field {
  margin-bottom: 15px;
}

.field label {
  display: block;
  color: #888;
  font-size: 12px;
  margin-bottom: 5px;
}

.value {
  color: #fff;
  padding: 10px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 6px;
}

.tool-name {
  color: #ffd700;
  font-weight: bold;
}

.query, .reason {
  color: #ddd;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 15px;
  border-top: 1px solid #4a4a8a;
}

.cancel-btn, .confirm-btn {
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.cancel-btn {
  background: transparent;
  border: 1px solid #4a4a8a;
  color: #fff;
}

.cancel-btn:hover {
  background: #3a3a5a;
}

.confirm-btn {
  background: #4a8a4a;
  border: none;
  color: #fff;
}

.confirm-btn:hover {
  background: #5a9a5a;
}
</style>