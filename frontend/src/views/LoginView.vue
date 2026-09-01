<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Moon, Sunny } from '@element-plus/icons-vue'

import { getErrorMessage } from '../api/client'
import { useAuthStore } from '../stores/auth'
import { isDark, toggleDark } from '../stores/theme'

const auth = useAuthStore()
const router = useRouter()
const code = ref('')
const loading = ref(false)
const errorMessage = ref('')

async function submit() {
  loading.value = true
  errorMessage.value = ''
  try {
    await auth.login(code.value)
    await router.push({ name: 'dashboard' })
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
    code.value = ''
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="min-h-screen flex items-center justify-center p-4 relative overflow-hidden bg-[var(--bg-color)]">
    <!-- 背景光晕 -->
    <div class="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/20 rounded-full blur-[100px] pointer-events-none"></div>
    <div class="absolute bottom-1/4 right-1/4 w-96 h-96 bg-violet-500/20 rounded-full blur-[100px] pointer-events-none"></div>

    <button
      :title="isDark ? '切换到浅色模式' : '切换到深色模式'"
      class="absolute top-6 right-6 w-9 h-9 flex items-center justify-center rounded-full border border-[var(--border-color)] bg-[var(--surface-color)]/60 backdrop-blur hover:bg-[var(--surface-color)] hover:border-blue-500/40 hover:text-blue-500 transition-all duration-200 text-[var(--text-secondary)] z-10"
      @click="toggleDark()"
    >
      <el-icon :size="17">
        <Moon v-if="!isDark" />
        <Sunny v-else />
      </el-icon>
    </button>

    <section class="relative w-full max-w-4xl grid lg:grid-cols-2 gap-8 lg:gap-12 items-center" aria-label="CETWorkOverTime 安全登录">
      <!-- Left side: Intro -->
      <div class="flex flex-col gap-6 lg:pr-8">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-violet-500 text-white flex items-center justify-center shadow-lg shadow-blue-500/30">
            <svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 6.75h16v10.5H4z" />
              <path d="m5 8 7 5 7-5" />
            </svg>
          </div>
          <strong class="text-xl font-black tracking-tight text-[var(--text-primary)]">CETWorkOverTime</strong>
        </div>
        
        <div class="mt-4">
          <span class="eyebrow">Work Log Center</span>
          <h1 class="text-4xl sm:text-5xl font-black mt-2 mb-4 leading-tight text-[var(--text-primary)]">清晰掌握每一段<br /><span class="text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-violet-500">投入时间</span></h1>
          <p class="text-[var(--text-secondary)] text-lg">集中查看邮件工作日志、月度勤奋时间与自动生成的工作报告。</p>
        </div>
        
        <ul class="space-y-3 mt-4" aria-label="系统能力">
          <li class="flex items-center gap-3 text-[var(--text-primary)] font-medium">
            <div class="w-6 h-6 rounded-full bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
            </div>
            月度工作时间统计
          </li>
          <li class="flex items-center gap-3 text-[var(--text-primary)] font-medium">
            <div class="w-6 h-6 rounded-full bg-blue-500/10 text-blue-500 flex items-center justify-center">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
            </div>
            邮件日志自动同步
          </li>
          <li class="flex items-center gap-3 text-[var(--text-primary)] font-medium">
            <div class="w-6 h-6 rounded-full bg-violet-500/10 text-violet-500 flex items-center justify-center">
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
            </div>
            动态工作报告生成
          </li>
        </ul>
      </div>

      <!-- Right side: Login Card -->
      <form class="glass rounded-3xl border border-[var(--border-color)] shadow-2xl p-8 sm:p-10 flex flex-col backdrop-blur-xl" @submit.prevent="submit">
        <div class="flex items-center gap-4 mb-8">
          <div class="w-12 h-12 rounded-full bg-blue-50 dark:bg-blue-500/10 text-blue-500 flex items-center justify-center border border-blue-100 dark:border-blue-500/20">
            <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <div>
            <span class="text-[10px] font-bold text-slate-400 tracking-widest uppercase">Secure Access</span>
            <h2 class="text-xl font-bold text-[var(--text-primary)]">验证身份</h2>
          </div>
        </div>
        
        <p class="text-sm text-[var(--text-secondary)] mb-6">请输入 Authenticator 中当前显示的 6 位动态验证码。</p>
        
        <div class="flex flex-col gap-2 mb-6">
          <label class="text-sm font-semibold text-[var(--text-primary)]" for="totp-code">动态验证码</label>
          <el-input
            id="totp-code"
            v-model="code"
            inputmode="numeric"
            maxlength="6"
            placeholder="······"
            size="large"
            autocomplete="one-time-code"
            autofocus
            class="totp-input"
          />
        </div>
        
        <div v-if="errorMessage" class="text-rose-500 text-sm font-medium mb-4 p-3 bg-rose-50 dark:bg-rose-500/10 rounded-lg border border-rose-200 dark:border-rose-500/20 flex items-center gap-2" role="alert">
          <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
          {{ errorMessage }}
        </div>
        
        <el-button
          native-type="submit"
          type="primary"
          size="large"
          :loading="loading"
          :disabled="code.length !== 6"
          class="!rounded-xl !h-12 text-base font-bold shadow-lg shadow-blue-500/30 transition-transform active:scale-95"
        >
          安全登录
        </el-button>
        
        <div class="mt-8 pt-6 border-t border-[var(--border-color)] text-center">
          <small class="text-xs text-[var(--text-secondary)] flex items-center justify-center gap-1.5">
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            验证码每 30 秒更新，请勿向他人提供。
          </small>
        </div>
      </form>
    </section>
  </main>
</template>

<style scoped>
/* 验证码输入：样式必须落在内部 input 上，加在 el-input 根节点无效 */
.totp-input :deep(.el-input__wrapper) {
  border-radius: 12px;
  padding: 4px 15px;
}

.totp-input :deep(.el-input__inner) {
  height: 48px;
  text-align: center;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: 0.5em;
  text-indent: 0.5em;
  font-variant-numeric: tabular-nums;
}
</style>
