<script setup lang="ts">
import { onMounted, ref } from 'vue'

const apiStatus = ref('正在检查 API...')

onMounted(async () => {
  try {
    const response = await fetch('/api/v1/health')
    const data = await response.json()
    apiStatus.value = data.status === 'ok' ? 'API 已连接' : 'API 状态异常'
  } catch {
    apiStatus.value = 'API 暂未连接'
  }
})
</script>

<template>
  <main class="shell">
    <h1>CETWorkOverTime</h1>
    <p>Vue 3 + FastAPI 迁移工程</p>
    <span class="status">{{ apiStatus }}</span>
  </main>
</template>
