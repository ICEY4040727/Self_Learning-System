<template>
  <div class="character-display" :class="position">
    <img
      v-if="avatar"
      :src="avatar"
      :alt="name"
      class="character-image"
      :class="{ 'flipped': position === 'right' }"
    />
    <div v-else class="character-placeholder">
      {{ name?.[0] || '?' }}
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  name?: string
  avatar?: string
  position?: 'left' | 'center' | 'right'
}>()
</script>

<style scoped>
.character-display {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  min-width: 200px;
  min-height: 300px;
}

.character-display.left {
  justify-content: flex-start;
}

.character-display.right {
  justify-content: flex-end;
}

.character-display.center {
  justify-content: center;
}

.character-image {
  max-height: 400px;
  max-width: 300px;
  object-fit: contain;
  transition: all 0.5s ease;
  filter: drop-shadow(0 0 20px rgba(255, 255, 255, 0.3));
}

.character-image.flipped {
  transform: scaleX(-1);
}

.character-placeholder {
  width: 200px;
  height: 300px;
  background: linear-gradient(135deg, #4a4a8a, #2a2a4a);
  border-radius: 100px 100px 20px 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 80px;
  font-weight: bold;
  color: #ffd700;
  border: 3px solid #ffd700;
}
</style>