import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../api/client'

export const useAuthStore = defineStore('auth', () => {
  const authenticated = ref(false)
  const checked = ref(false)

  async function checkSession() {
    try {
      const { data } = await api.get<{ authenticated: boolean }>('/auth/session')
      authenticated.value = data.authenticated
    } finally {
      checked.value = true
    }
  }

  async function login(code: string) {
    const { data } = await api.post<{ authenticated: boolean }>('/auth/login', { code })
    authenticated.value = data.authenticated
    checked.value = true
  }

  async function logout() {
    await api.post('/auth/logout')
    authenticated.value = false
  }

  return { authenticated, checked, checkSession, login, logout }
})
