<template>
  <div class="dialog-box" :class="{ 'has-name': characterName }">
    <div v-if="characterName" class="name-box">
      {{ characterName }}
    </div>
    <div class="content">
      <slot>{{ content }}</slot>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  characterName?: string
  content?: string
}>()
</script>

<style scoped>
.dialog-box {
  background: rgba(0, 0, 0, 0.85);
  border: 2px solid #ffd700;
  border-radius: 8px;
  padding: 20px;
  min-height: 120px;
  max-width: 800px;
  margin: 0 auto;
  box-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
}

.name-box {
  background: linear-gradient(90deg, #ffd700, #ff8c00);
  color: #1a1a2e;
  padding: 5px 20px;
  border-radius: 4px;
  display: inline-block;
  font-weight: bold;
  margin-bottom: 10px;
}

.content {
  color: #fff;
  font-size: 16px;
  line-height: 1.8;
  white-space: pre-wrap;
}

.has-name .content {
  margin-top: 10px;
}
</style>