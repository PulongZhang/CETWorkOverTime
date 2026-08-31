<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Monitor, Calendar, Message, Document, SwitchButton, Sunny, Moon } from '@element-plus/icons-vue'

import { api } from '../api/client'
import { useAuthStore } from '../stores/auth'
import { isDark, toggleDark } from '../stores/theme'
import type { SystemStatus } from '../types/api'

const router = useRouter()
const route = useRoute()
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
  <div class="flex h-screen overflow-hidden bg-[var(--bg-color)] text-[var(--text-primary)] transition-colors duration-300 relative">
    <!-- Background glowing orbs -->
    <div class="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-500/20 rounded-full blur-[120px] pointer-events-none z-0"></div>
    <div class="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-500/20 rounded-full blur-[120px] pointer-events-none z-0"></div>

    <!-- Sidebar -->
    <aside class="w-64 flex-shrink-0 glass border-r flex flex-col transition-all duration-300 z-20 shadow-[4px_0_24px_rgba(0,0,0,0.02)]">
      <div class="h-16 flex items-center px-6 border-b border-[var(--border-color)]">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-blue-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/30">
            <el-icon :size="18"><Monitor /></el-icon>
          </div>
          <div>
            <div class="font-bold text-sm tracking-wide">CETWorkOverTime</div>
            <div class="text-xs text-[var(--text-secondary)]">工作时间管理</div>
          </div>
        </div>
      </div>
      
      <div class="flex-1 overflow-y-auto py-6 px-4">
        <nav class="space-y-1">
          <RouterLink to="/" class="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200" :class="route.path === '/' ? 'bg-blue-500 text-white shadow-md shadow-blue-500/20' : 'hover:bg-[var(--border-color)]'">
            <el-icon><Monitor /></el-icon>
            <span class="font-medium text-sm">仪表板</span>
          </RouterLink>
          <RouterLink to="/reports" class="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200" :class="route.path.startsWith('/reports') ? 'bg-blue-500 text-white shadow-md shadow-blue-500/20' : 'hover:bg-[var(--border-color)]'">
            <el-icon><Document /></el-icon>
            <span class="font-medium text-sm">报告管理</span>
          </RouterLink>
          <RouterLink to="/compose" class="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200" :class="route.path.startsWith('/compose') ? 'bg-blue-500 text-white shadow-md shadow-blue-500/20' : 'hover:bg-[var(--border-color)]'">
            <el-icon><Message /></el-icon>
            <span class="font-medium text-sm">发邮件</span>
          </RouterLink>
          <RouterLink to="/calendar" class="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200" :class="route.path.startsWith('/calendar') ? 'bg-blue-500 text-white shadow-md shadow-blue-500/20' : 'hover:bg-[var(--border-color)]'">
            <el-icon><Calendar /></el-icon>
            <span class="font-medium text-sm">请假</span>
          </RouterLink>
        </nav>
      </div>

      <div class="p-4 border-t border-[var(--border-color)]">
        <button @click="logout" class="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-red-500 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors duration-200 font-medium text-sm">
          <el-icon><SwitchButton /></el-icon>
          <span>退出登录</span>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="flex-1 flex flex-col overflow-hidden relative">
      <!-- Top Header -->
      <header class="h-16 glass border-b flex items-center justify-between px-6 z-10">
        <div class="flex items-center">
          <div v-if="status" class="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border border-[var(--border-color)] bg-[var(--surface-color)] transition-colors">
            <span class="w-2 h-2 rounded-full relative flex h-2 w-2">
              <span v-if="status.task.running" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2" :class="status.task.running ? 'bg-yellow-500' : 'bg-green-500'"></span>
            </span>
            <span :class="status.task.running ? 'text-yellow-600 dark:text-yellow-400' : 'text-[var(--text-secondary)]'">
              {{ status.task.running ? status.task.message : '系统就绪' }}
            </span>
          </div>
        </div>
        <div class="flex items-center gap-4">
          <button @click="toggleDark()" class="w-9 h-9 flex items-center justify-center rounded-full hover:bg-[var(--border-color)] transition-colors text-[var(--text-secondary)] hover:text-blue-500">
            <el-icon :size="18">
              <Moon v-if="!isDark" />
              <Sunny v-else />
            </el-icon>
          </button>
        </div>
      </header>

      <!-- Page Content -->
      <main class="flex-1 overflow-y-auto p-6 lg:p-8">
        <div class="max-w-6xl mx-auto">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </main>
    </div>
  </div>
</template>
