<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api, getErrorMessage } from '../api/client'

type TemplateKey = 'plan' | 'summary'

const RECIPIENT = 'working@cet-electric.com'
const DEFAULT_START = '17:45'
const DEFAULT_END = '19:45'

function today() {
  const now = new Date()
  const month = `${now.getMonth() + 1}`.padStart(2, '0')
  const day = `${now.getDate()}`.padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

const to = ref(RECIPIENT)
const cc = ref('')
const subject = ref('')
const content = ref('')
const sending = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

function fillTemplate(key: TemplateKey) {
  const date = today()
  if (key === 'plan') {
    subject.value = `工作计划[${date}]`
    content.value = `工作计划[${date}]\n1、\n2、\n3、`
  } else {
    subject.value = `工作总结[${date}]`
    content.value =
      `工作总结[${date}]\n1、\n2、\n3、\n\n[勤奋时间][${DEFAULT_START}][${DEFAULT_END}].`
  }
}

async function send() {
  errorMessage.value = ''
  successMessage.value = ''
  sending.value = true
  try {
    const ccList = cc.value
      .split(/[,;，；\s]+/)
      .map((item) => item.trim())
      .filter(Boolean)
    await api.post('/emails/send', {
      to: to.value.trim(),
      cc: ccList,
      subject: subject.value,
      content: content.value,
    })
    successMessage.value = `已发送至 ${to.value.trim()}`
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    sending.value = false
  }
}

onMounted(() => fillTemplate('plan'))
</script>

<template>
  <section>
    <div class="page-heading">
      <div>
        <span class="eyebrow">COMPOSE</span>
        <h1>发邮件</h1>
        <p>使用模板快速发送每日工作计划与工作总结。</p>
      </div>
      <div class="template-actions">
        <el-button @click="fillTemplate('plan')">填入每日计划</el-button>
        <el-button @click="fillTemplate('summary')">填入每日总结</el-button>
      </div>
    </div>

    <form class="compose-card" @submit.prevent="send">
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
        <el-button type="primary" native-type="submit" :loading="sending">发送</el-button>
      </div>
    </form>
  </section>
</template>

<style scoped>
.template-actions {
  display: flex;
  gap: 8px;
}

.compose-card {
  display: grid;
  gap: 14px;
  max-width: 760px;
  padding: 24px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--surface-1);
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
    width: 100%;
  }

  .template-actions .el-button {
    flex: 1;
  }

  .compose-row {
    grid-template-columns: 1fr;
  }
}
</style>
