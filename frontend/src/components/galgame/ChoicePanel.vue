<template>
  <div class="choice-panel">
    <button
      v-for="(choice, index) in choices"
      :key="index"
      class="choice-button"
      @click="$emit('select', choice)"
    >
      {{ choice }}
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  choices: string[]
}>()

defineEmits<{
  select: [choice: string]
}>()
</script>

<style scoped>
.choice-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 20px 0;
}

.choice-button {
  background: linear-gradient(135deg, #2a2a4a, #1a1a2e);
  border: 2px solid #4a4a8a;
  color: #fff;
  padding: 15px 30px;
  font-size: 16px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.choice-button:hover {
  background: linear-gradient(135deg, #4a4a8a, #3a3a7a);
  border-color: #ffd700;
  transform: translateX(10px);
  box-shadow: 0 0 15px rgba(255, 215, 0, 0.3);
}
</style>