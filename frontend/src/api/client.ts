import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
  withCredentials: true,
})

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail ?? error.message
  }
  return error instanceof Error ? error.message : '请求失败'
}
