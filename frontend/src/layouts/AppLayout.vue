<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { api } from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { SystemStatus } from '../types/api'

const router = useRouter()
const auth = useAuthStore()
const status = ref<SystemStatus | null>(null)
let timer: number | undefined

async function loadStatus() {
  try {
    status.value = (await api.get<SystemStatus>('/status')).data
  } catch {
    status.value = null
  }
}

async function logout() {
  await auth.logout()
  await router.push({ name: 'login' })
}

onMounted(() => {
  loadStatus()
  timer = window.setInterval(loadStatus, 3000)
})

onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <RouterLink class="brand" to="/">
        <span class="brand-icon">✉</span>
        <span>CETWorkOverTime</span>
        <small>v3.0</small>
      </RouterLink>
      <nav class="nav-links" aria-label="主导航">
        <RouterLink to="/">仪表板</RouterLink>
        <RouterLink to="/reports">报告管理</RouterLink>
      </nav>
      <div class="header-actions">
        <span class="runtime-status" :class="{ busy: status?.task.running }">
          <i />{{ status?.task.running ? status.task.message : '就绪' }}
        </span>
        <button class="text-button danger" type="button" @click="logout">退出</button>
      </div>
    </header>
    <main class="page-container">
      <RouterView />
    </main>
  </div>
</template>
