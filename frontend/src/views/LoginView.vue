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
    <form class="login-card" @submit.prevent="submit">
      <div class="login-icon">✉</div>
      <h1>CETWorkOverTime</h1>
      <p>输入 Authenticator 中的 6 位动态验证码</p>
      <el-input
        v-model="code"
        inputmode="numeric"
        maxlength="6"
        placeholder="123456"
        size="large"
        autocomplete="one-time-code"
      />
      <el-button
        native-type="submit"
        type="primary"
        size="large"
        :loading="loading"
        :disabled="code.length !== 6"
      >
        登录
      </el-button>
      <span class="form-error" role="alert">{{ errorMessage }}</span>
    </form>
  </main>
</template>
