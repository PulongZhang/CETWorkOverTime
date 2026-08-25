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
  <section class="compose-page">
    <div class="page-heading">
      <div>
        <span class="eyebrow">COMPOSE</span>
        <h1>发邮件</h1>
        <p>使用模板快速发送每日工作计划与工作总结。</p>
      </div>
    </div>

    <form class="compose-card" @submit.prevent="send">
      <div class="template-actions" role="group" aria-label="填入模板">
        <span class="template-label">模板</span>
        <el-button :disabled="!configLoaded" @click="fillTemplate('plan')">每日计划</el-button>
        <el-button :disabled="!configLoaded" @click="fillTemplate('summary')">每日总结</el-button>
      </div>

      <div class="compose-row">
        <label for="compose-to">收件人</label>
        <el-input id="compose-to" v-model="to" placeholder="收件人邮箱" />
      </div>
      <div class="compose-row">
        <label for="compose-cc">抄送</label>
        <el-input id="compose-cc" v-model="cc" placeholder="多个地址用逗号分隔，可留空" />
      </div>
      <div class="compose-row">
        <label for="compose-subject">主题</label>
        <el-input id="compose-subject" v-model="subject" placeholder="邮件主题" />
      </div>

      <label class="field-label" for="compose-content">正文</label>
      <textarea
        id="compose-content"
        v-model="content"
        rows="12"
        spellcheck="false"
        placeholder="邮件正文"
      />

      <p v-if="errorMessage" class="inline-error" role="alert">{{ errorMessage }}</p>
      <p v-if="successMessage" class="inline-success" role="status">{{ successMessage }}</p>

      <div class="compose-actions">
        <el-button
          type="primary"
          native-type="submit"
          :loading="sending"
          :disabled="!configLoaded"
        >
          发送
        </el-button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.template-actions {
  display: flex;
  gap: 8px;
}

.compose-page {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.compose-page .page-heading {
  width: 100%;
  max-width: 760px;
}

.compose-card {
  display: grid;
  gap: 14px;
  width: 100%;
  max-width: 760px;
  padding: 24px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--surface-1);
}

.template-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border-subtle);
}

.template-label {
  margin-right: auto;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.compose-row {
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr);
  align-items: center;
  gap: 12px;
}

.compose-row > label {
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.compose-card textarea {
  padding: 14px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: var(--app-bg);
  font: inherit;
  line-height: 1.65;
  resize: vertical;
}

.compose-card textarea:focus-visible {
  outline: 2px solid var(--action-primary);
  outline-offset: -1px;
}

.inline-success {
  margin: 0;
  color: var(--status-success);
  font-size: 13px;
}

.compose-actions {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 680px) {
  .template-actions {
    flex-wrap: wrap;
  }

  .template-label {
    width: 100%;
    margin: 0 0 2px;
  }

  .template-actions .el-button {
    flex: 1;
  }

  .compose-row {
    grid-template-columns: 1fr;
  }
}
</style>
