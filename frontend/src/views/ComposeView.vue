<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, getErrorMessage } from '../api/client'

type TemplateKey = 'plan' | 'summary'

interface ComposeConfig {
  recipient: string
  plan_subject: string
}

interface SendEmailResponse {
  success: boolean
  to: string
  subject: string
  error?: string
}

const DEFAULT_START = '17:45'
const DEFAULT_END = '19:45'
const beijingDateFormatter = new Intl.DateTimeFormat('en-US', {
  timeZone: 'Asia/Shanghai',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})

function todayInBeijing() {
  const parts = beijingDateFormatter.formatToParts(new Date())
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${values.year}-${values.month}-${values.day}`
}

const to = ref('')
const cc = ref('')
const subject = ref('')
const content = ref('')
const planSubject = ref('')
const configLoaded = ref(false)
const sending = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
let activeTemplate: TemplateKey | null = null
let generatedDate = ''

function fillTemplate(key: TemplateKey) {
  generatedDate = todayInBeijing()
  if (key === 'plan') {
    subject.value = `${planSubject.value}[${generatedDate}]`
    content.value = `${planSubject.value}[${generatedDate}]\n1、\n2、\n3、`
  } else {
    subject.value = `工作总结[${generatedDate}]`
    content.value =
      `工作总结[${generatedDate}]\n1、\n2、\n3、\n\n[勤奋时间][${DEFAULT_START}][${DEFAULT_END}].`
  }
  activeTemplate = key
}

function refreshTemplateDate() {
  if (!activeTemplate) return
  const currentDate = todayInBeijing()
  if (currentDate === generatedDate) return
  const oldMarker = `[${generatedDate}]`
  const newMarker = `[${currentDate}]`
  subject.value = subject.value.replace(oldMarker, newMarker)
  content.value = content.value.replace(oldMarker, newMarker)
  generatedDate = currentDate
}

async function loadComposeConfig() {
  try {
    const { data } = await api.get<ComposeConfig>('/emails/compose-config')
    to.value = data.recipient
    planSubject.value = data.plan_subject
    configLoaded.value = true
    fillTemplate('plan')
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function send() {
  errorMessage.value = ''
  successMessage.value = ''
  if (!configLoaded.value) {
    errorMessage.value = '邮件配置尚未加载，请稍后重试'
    return
  }
  refreshTemplateDate()

  sending.value = true
  try {
    const ccList = cc.value
      .split(/[,;，；\s]+/)
      .map((item) => item.trim())
      .filter(Boolean)
    const { data } = await api.post<SendEmailResponse>('/emails/send', {
      to: to.value.trim(),
      cc: ccList,
      subject: subject.value,
      content: content.value,
    })
    if (!data.success) {
      errorMessage.value = data.error ?? '邮件仅部分发送成功，请检查收件人地址'
      return
    }
    successMessage.value = `已发送至 ${data.to}`
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    sending.value = false
  }
}

onMounted(loadComposeConfig)
</script>

<template>
  <section class="space-y-6 max-w-4xl mx-auto h-full flex flex-col">
    <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
      <div>
        <span class="text-blue-500 font-bold text-xs tracking-widest uppercase">Compose</span>
        <h1 class="text-3xl font-bold mt-1 mb-2 text-[var(--text-primary)]">发邮件</h1>
        <p class="text-[var(--text-secondary)] text-sm max-w-2xl">使用模板快速发送每日工作计划与工作总结。</p>
      </div>
    </div>

    <form class="glass rounded-2xl border border-[var(--border-color)] shadow-sm p-6 sm:p-8 flex flex-col gap-6" @submit.prevent="send">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-[var(--border-color)] gap-4">
        <span class="text-sm font-bold text-[var(--text-primary)]">填入模板</span>
        <div class="flex items-center gap-3 w-full sm:w-auto">
          <el-button :disabled="!configLoaded" @click="fillTemplate('plan')" class="flex-1 sm:flex-none !rounded-xl">每日计划</el-button>
          <el-button :disabled="!configLoaded" @click="fillTemplate('summary')" class="flex-1 sm:flex-none !rounded-xl">每日总结</el-button>
        </div>
      </div>

      <div class="space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-6">
          <label for="compose-to" class="w-20 text-sm font-semibold text-[var(--text-secondary)] shrink-0">收件人</label>
          <el-input id="compose-to" v-model="to" placeholder="收件人邮箱" size="large" class="flex-1" />
        </div>
        
        <div class="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-6">
          <label for="compose-cc" class="w-20 text-sm font-semibold text-[var(--text-secondary)] shrink-0">抄送</label>
          <el-input id="compose-cc" v-model="cc" placeholder="多个地址用逗号分隔，可留空" size="large" class="flex-1" />
        </div>
        
        <div class="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-6">
          <label for="compose-subject" class="w-20 text-sm font-semibold text-[var(--text-secondary)] shrink-0">主题</label>
          <el-input id="compose-subject" v-model="subject" placeholder="邮件主题" size="large" class="flex-1" />
        </div>
      </div>

      <div class="flex flex-col gap-2 mt-2">
        <label for="compose-content" class="text-sm font-semibold text-[var(--text-secondary)]">正文</label>
        <textarea
          id="compose-content"
          v-model="content"
          rows="12"
          spellcheck="false"
          placeholder="邮件正文"
          class="w-full p-4 rounded-xl border border-[var(--border-color)] bg-[var(--surface-color)]/50 text-[var(--text-primary)] text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all resize-y leading-relaxed font-mono"
        />
      </div>

      <p v-if="errorMessage" class="text-red-500 text-sm font-medium" role="alert">{{ errorMessage }}</p>
      <p v-if="successMessage" class="text-green-500 text-sm font-medium" role="status">{{ successMessage }}</p>

      <div class="flex justify-end pt-4 border-t border-[var(--border-color)] mt-2">
        <el-button
          type="primary"
          native-type="submit"
          :loading="sending"
          :disabled="!configLoaded"
          size="large"
          class="!rounded-xl !px-8 shadow-sm shadow-blue-500/20"
        >
          发送
        </el-button>
      </div>
    </form>
  </section>
</template>
