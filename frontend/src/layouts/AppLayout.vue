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
      <RouterLink class="brand" to="/" aria-label="CETWorkOverTime 首页">
        <span class="brand-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <path d="M4 6.75h16v10.5H4z" />
            <path d="m5 8 7 5 7-5" />
          </svg>
        </span>
        <span class="brand-copy">
          <strong>CETWorkOverTime</strong>
          <small>工作时间管理</small>
        </span>
      </RouterLink>
      <nav class="nav-links" aria-label="主导航">
        <RouterLink to="/">
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path d="M4 13h6V4H4zM14 20h6V11h-6zM4 20h6v-3H4zM14 7h6V4h-6z" />
          </svg>
          仪表板
        </RouterLink>
        <RouterLink to="/reports">
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path d="M6 3.75h9l3 3v13.5H6z" />
            <path d="M9 11h6M9 15h6M15 3.75v3h3" />
          </svg>
          报告管理
        </RouterLink>
        <RouterLink to="/compose">
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path d="M4 5.5h16v13H4z" />
            <path d="m4 7 8 6 8-6" />
          </svg>
          发邮件
        </RouterLink>
      </nav>
      <div class="header-actions">
        <span class="runtime-status" :class="{ busy: status?.task.running }" role="status">
          <i aria-hidden="true" />
          <span>{{ status?.task.running ? status.task.message : '系统就绪' }}</span>
        </span>
        <button class="logout-button" type="button" aria-label="退出登录" @click="logout">
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path d="M10 5H5v14h5M14 8l4 4-4 4M8 12h10" />
          </svg>
          <span>退出</span>
        </button>
      </div>
    </header>
    <main class="page-container">
      <RouterView />
    </main>
  </div>
</template>
