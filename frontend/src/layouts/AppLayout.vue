<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
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

const navItems = [
  { to: '/', label: '仪表板', icon: Monitor },
  { to: '/reports', label: '报告管理', icon: Document },
  { to: '/compose', label: '发邮件', icon: Message },
  { to: '/calendar', label: '请假', icon: Calendar },
]

const currentLabel = computed(
  () => navItems.find((item) => isActive(item.to))?.label ?? '',
)

function isActive(path: string) {
  return path === '/' ? route.path === '/' : route.path.startsWith(path)
}

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
    <div class="absolute top-[-15%] left-[-10%] w-[45%] h-[45%] bg-blue-500/20 rounded-full blur-[130px] pointer-events-none z-0"></div>
    <div class="absolute bottom-[-15%] right-[-10%] w-[45%] h-[45%] bg-violet-500/20 rounded-full blur-[130px] pointer-events-none z-0"></div>

    <!-- Sidebar -->
    <aside class="w-64 flex-shrink-0 glass border-y-0 border-l-0 flex flex-col z-20">
      <div class="h-16 flex items-center px-6 border-b border-[var(--border-color)]">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-violet-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/30">
            <el-icon :size="18"><Monitor /></el-icon>
          </div>
          <div>
            <div class="font-bold text-sm tracking-wide">CETWorkOverTime</div>
            <div class="text-xs text-[var(--text-secondary)]">工作时间管理</div>
          </div>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto py-6 px-3">
        <div class="px-3 pb-3 text-[10px] font-bold tracking-[0.16em] uppercase text-[var(--text-secondary)]">Navigation</div>
        <nav class="space-y-1.5">
          <RouterLink
            v-for="item in navItems"
            :key="item.to"
            :to="item.to"
            class="group relative flex items-center gap-3 px-3.5 py-3 rounded-xl transition-all duration-200 overflow-hidden"
            :class="isActive(item.to)
              ? 'bg-gradient-to-r from-blue-500 to-violet-500 text-white shadow-lg shadow-blue-500/25'
              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-color)]/70'"
          >
            <span
              class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 rounded-r-full bg-white/80 transition-opacity duration-200"
              :class="isActive(item.to) ? 'opacity-100' : 'opacity-0'"
            ></span>
            <el-icon :size="17" class="transition-transform duration-200 group-hover:scale-110"><component :is="item.icon" /></el-icon>
            <span class="font-medium text-sm">{{ item.label }}</span>
          </RouterLink>
        </nav>
      </div>

      <div class="p-3 border-t border-[var(--border-color)]">
        <button @click="logout" class="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors duration-200 font-medium text-sm">
          <el-icon><SwitchButton /></el-icon>
          <span>退出登录</span>
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="flex-1 flex flex-col overflow-hidden relative">
      <!-- Top Header -->
      <header class="h-16 glass border-x-0 border-t-0 flex items-center justify-between px-6 z-10">
        <div class="flex items-center gap-4">
          <h1 class="font-semibold text-[15px] text-[var(--text-primary)]">{{ currentLabel }}</h1>
          <div v-if="status" class="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border border-[var(--border-color)] bg-[var(--surface-color)]/70 transition-colors">
            <span class="relative flex h-2 w-2">
              <span v-if="status.task.running" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2" :class="status.task.running ? 'bg-amber-500' : 'bg-emerald-500'"></span>
            </span>
            <span :class="status.task.running ? 'text-amber-600 dark:text-amber-400' : 'text-[var(--text-secondary)]'">
              {{ status.task.running ? status.task.message : '系统就绪' }}
            </span>
          </div>
        </div>
        <div class="flex items-center gap-4">
          <button
            :title="isDark ? '切换到浅色模式' : '切换到深色模式'"
            @click="toggleDark()"
            class="w-9 h-9 flex items-center justify-center rounded-full border border-[var(--border-color)] bg-[var(--surface-color)]/60 hover:bg-[var(--surface-color)] hover:border-blue-500/40 hover:text-blue-500 transition-all duration-200 text-[var(--text-secondary)]"
          >
            <el-icon :size="17">
              <Moon v-if="!isDark" />
              <Sunny v-else />
            </el-icon>
          </button>
        </div>
      </header>

      <!-- Page Content -->
      <main class="flex-1 overflow-y-auto p-6 lg:p-8">
        <div class="max-w-6xl mx-auto h-full">
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
