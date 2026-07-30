<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

import { api, getErrorMessage } from '../api/client'
import type { ReportSummary, TaskStatus } from '../types/api'

const reports = ref<ReportSummary[]>([])
const selected = ref<ReportSummary | null>(null)
const reportHtml = ref('')
const reportMarkdown = ref('')
const rawView = ref(false)
const loading = ref(false)
const task = ref<TaskStatus | null>(null)
const days = ref(365)
const errorMessage = ref('')
const loadError = ref('')
let timer: number | undefined

async function loadReports() {
  loadError.value = ''
  try {
    reports.value = (await api.get<{ reports: ReportSummary[] }>('/reports')).data.reports
  } catch (error) {
    reports.value = []
    loadError.value = getErrorMessage(error)
  }
}

async function openReport(report: ReportSummary) {
  selected.value = report
  loadError.value = ''
  try {
    const { data } = await api.get<{ html: string; markdown: string }>(
      `/reports/${report.year}/${report.month}`,
    )
    reportHtml.value = data.html
    reportMarkdown.value = data.markdown
  } catch (error) {
    loadError.value = getErrorMessage(error)
  }
}

async function runTask(path: string, payload: object) {
  errorMessage.value = ''
  try {
    task.value = (await api.post<TaskStatus>(path, payload)).data
    startPolling()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

function startPolling() {
  window.clearInterval(timer)
  timer = window.setInterval(async () => {
    task.value = (await api.get<TaskStatus>('/tasks/current')).data
    if (!task.value.running) {
      window.clearInterval(timer)
      await loadReports()
    }
  }, 1500)
}

onMounted(async () => {
  loading.value = true
  try {
    await loadReports()
    task.value = (await api.get<TaskStatus>('/tasks/current')).data
    if (task.value.running) startPolling()
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <section>
    <div class="page-heading">
      <div>
        <span class="eyebrow">REPORTS & AUTOMATION</span>
        <h1>报告管理</h1>
        <p>抓取邮件、同步数据库并查看动态生成的月度报告。</p>
      </div>
    </div>

    <div class="operation-bar" aria-label="报告自动化操作">
      <div class="operation-field">
        <label for="fetch-days">抓取范围</label>
        <el-input-number id="fetch-days" v-model="days" :min="1" :max="3650" />
        <span>天</span>
      </div>
      <div class="operation-actions">
        <el-button
          type="primary"
          :loading="task?.running && task.type === 'fetch'"
          :disabled="task?.running"
          @click="runTask('/tasks/fetch', { days })"
        >
          抓取并入库
        </el-button>
        <el-button :disabled="task?.running" @click="runTask('/tasks/process', { force: false })">
          生成本地报告
        </el-button>
        <el-button :disabled="task?.running" @click="runTask('/tasks/sync-database', {})">
          同步历史文件
        </el-button>
      </div>
      <span v-if="task?.message" class="task-message" :class="{ busy: task.running }" role="status">
        <i aria-hidden="true" />{{ task.message }}
      </span>
    </div>
    <p v-if="errorMessage" class="inline-error" role="alert">{{ errorMessage }}</p>

    <div v-if="loadError" class="state-card error-state report-error" role="alert">
      <span class="state-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24">
          <path d="M12 4 3.5 19h17z" />
          <path d="M12 9v4M12 16.5v.1" />
        </svg>
      </span>
      <div>
        <strong>报告数据暂时无法加载</strong>
        <p>{{ loadError }}</p>
      </div>
      <el-button @click="loadReports">重新加载</el-button>
    </div>

    <div v-else class="report-layout" v-loading="loading" :aria-busy="loading">
      <aside class="report-list" aria-label="月度报告列表">
        <button
          v-for="report in reports"
          :key="`${report.year}-${report.month}`"
          :class="{ active: selected?.filename === report.filename }"
          @click="openReport(report)"
        >
          <strong>{{ report.year }}年{{ report.month }}月</strong>
          <small>{{ report.entries }} 条记录 · {{ report.hours.toFixed(1) }}h</small>
        </button>
        <div v-if="reports.length === 0" class="state-card compact-state">
          <strong>暂无月度报告</strong>
          <p>抓取邮件并完成入库后，报告将按月份显示在这里。</p>
        </div>
      </aside>
      <article class="report-viewer">
        <header v-if="selected">
          <h2>{{ selected.filename.replace('.md', '') }}</h2>
          <el-switch v-model="rawView" active-text="Markdown 源码" />
        </header>
        <div v-if="!selected" class="state-card">从左侧选择一份报告</div>
        <pre v-else-if="rawView" class="report-source">{{ reportMarkdown }}</pre>
        <div v-else class="markdown-body" v-html="reportHtml" />
      </article>
    </div>
  </section>
</template>
