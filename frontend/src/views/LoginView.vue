<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { getErrorMessage } from '../api/client'
import { useAuthStore } from '../stores/auth'

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
  <main class="login-page">
    <section class="login-frame" aria-label="CETWorkOverTime 安全登录">
      <div class="login-intro">
        <div class="login-brand">
          <span class="login-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <path d="M4 6.75h16v10.5H4z" />
              <path d="m5 8 7 5 7-5" />
            </svg>
          </span>
          <strong>CETWorkOverTime</strong>
        </div>
        <div>
          <span class="eyebrow">WORK LOG CENTER</span>
          <h1 id="login-title">清晰掌握每一段<br />投入时间</h1>
          <p>集中查看邮件工作日志、月度勤奋时间与自动生成的工作报告。</p>
        </div>
        <ul class="login-features" aria-label="系统能力">
          <li><i aria-hidden="true" /> 月度工作时间统计</li>
          <li><i aria-hidden="true" /> 邮件日志自动同步</li>
          <li><i aria-hidden="true" /> 动态工作报告生成</li>
        </ul>
      </div>

      <form class="login-card" @submit.prevent="submit">
        <div class="login-card-heading">
          <span class="security-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <path d="M12 3.5 19 6v5.25c0 4.4-2.9 7.75-7 9.25-4.1-1.5-7-4.85-7-9.25V6z" />
              <path d="m9.5 12 1.7 1.7 3.6-3.6" />
            </svg>
          </span>
          <div>
            <span class="eyebrow">SECURE ACCESS</span>
            <h2>验证身份</h2>
          </div>
        </div>
        <p class="login-help">请输入 Authenticator 中当前显示的 6 位动态验证码。</p>
        <label class="field-label" for="totp-code">动态验证码</label>
        <el-input
          id="totp-code"
          v-model="code"
          inputmode="numeric"
          maxlength="6"
          placeholder="输入 6 位验证码"
          size="large"
          autocomplete="one-time-code"
          autofocus
        />
        <span class="form-error" role="alert">{{ errorMessage }}</span>
        <el-button
          native-type="submit"
          type="primary"
          size="large"
          :loading="loading"
          :disabled="code.length !== 6"
        >
          安全登录
        </el-button>
        <small class="login-footnote">验证码每 30 秒更新，请勿向他人提供。</small>
      </form>
    </section>
  </main>
</template>
