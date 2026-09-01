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
const days = ref(7)
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
  <section class="space-y-6 h-full flex flex-col">
    <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
      <div>
        <span class="eyebrow">Reports & Automation</span>
        <h1 class="text-3xl font-bold mt-1 mb-2 text-[var(--text-primary)]">报告管理</h1>
        <p class="text-[var(--text-secondary)] text-sm max-w-2xl">抓取邮件、同步数据库并查看动态生成的月度报告。</p>
      </div>
    </div>

    <!-- Operation Bar -->
    <div class="glass rounded-2xl p-5 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 border border-[var(--border-color)]">
      <div class="flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div class="flex items-center gap-3">
          <label for="fetch-days" class="text-sm font-medium text-[var(--text-primary)] whitespace-nowrap">抓取范围</label>
          <div class="flex items-center gap-2">
            <el-input-number id="fetch-days" v-model="days" :min="1" :max="3650" size="default" class="!w-32" />
            <span class="text-sm text-[var(--text-secondary)]">天</span>
          </div>
        </div>
        <div class="h-px w-full sm:w-px sm:h-8 bg-[var(--border-color)]"></div>
        <div class="flex flex-wrap items-center gap-3">
          <el-button
            type="primary"
            :loading="task?.running && task.type === 'fetch'"
            :disabled="task?.running"
            @click="runTask('/tasks/fetch', { days })"
            class="!rounded-xl shadow-sm shadow-blue-500/20"
          >
            抓取并入库
          </el-button>
          <el-button :disabled="task?.running" @click="runTask('/tasks/process', { force: false })" class="!rounded-xl">
            生成本地报告
          </el-button>
          <el-button :disabled="task?.running" @click="runTask('/tasks/sync-database', {})" class="!rounded-xl">
            同步历史文件
          </el-button>
        </div>
      </div>
      <div v-if="task?.message" class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[var(--surface-color)] border border-[var(--border-color)] shadow-inner text-sm max-w-sm truncate" :class="{ 'animate-pulse text-blue-500': task.running }">
        <span class="relative flex h-2 w-2 flex-shrink-0">
          <span v-if="task.running" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-2 w-2" :class="task.running ? 'bg-blue-500' : 'bg-emerald-500'"></span>
        </span>
        <span class="truncate font-medium">{{ task.message }}</span>
      </div>
    </div>
    
    <p v-if="errorMessage" class="text-rose-500 text-sm font-medium px-4 py-2 bg-rose-50 dark:bg-rose-500/10 rounded-lg border border-rose-200 dark:border-rose-500/20" role="alert">{{ errorMessage }}</p>

    <div v-if="loadError" class="flex items-center gap-4 p-6 rounded-2xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-600 dark:text-rose-400" role="alert">
      <div class="w-12 h-12 rounded-xl flex items-center justify-center bg-rose-100 dark:bg-rose-500/20 shrink-0">
        <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
      </div>
      <div class="flex-1">
        <strong class="block text-lg mb-1">报告数据暂时无法加载</strong>
        <p class="text-sm opacity-80">{{ loadError }}</p>
      </div>
      <el-button @click="loadReports" type="danger" plain class="!rounded-xl">重新加载</el-button>
    </div>

    <!-- Report Layout -->
    <div v-else class="flex-1 min-h-0 flex flex-col md:flex-row gap-6" v-loading="loading">
      <aside class="w-full md:w-72 flex-shrink-0 glass rounded-2xl border border-[var(--border-color)] overflow-hidden flex flex-col">
        <div class="p-4 border-b border-[var(--border-color)] bg-[var(--surface-color)]/50">
          <h3 class="font-bold text-sm tracking-wider text-[var(--text-secondary)] uppercase">Report List</h3>
        </div>
        <div class="flex-1 overflow-y-auto p-3 space-y-2">
          <button
            v-for="report in reports"
            :key="`${report.year}-${report.month}`"
            class="relative w-full flex flex-col items-start gap-1 p-3 pl-4 rounded-xl transition-all duration-200 border text-left overflow-hidden"
            :class="selected?.filename === report.filename ? 'bg-blue-50 dark:bg-blue-500/10 border-blue-200 dark:border-blue-500/20 text-blue-600 dark:text-blue-400' : 'bg-transparent border-transparent hover:bg-[var(--surface-color)] hover:border-[var(--border-color)] text-[var(--text-primary)]'"
            @click="openReport(report)"
          >
            <span
              class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-7 rounded-r-full bg-gradient-to-b from-blue-500 to-violet-500 transition-opacity duration-200"
              :class="selected?.filename === report.filename ? 'opacity-100' : 'opacity-0'"
            ></span>
            <strong class="text-sm font-semibold">{{ report.year }}年{{ report.month }}月</strong>
            <small class="text-xs opacity-80 tabular-nums">{{ report.entries }} 条记录 · {{ report.hours.toFixed(1) }}h</small>
          </button>
          
          <div v-if="reports.length === 0" class="py-10 px-4 text-center">
            <div class="w-12 h-12 mx-auto mb-3 rounded-full bg-[var(--border-color)] flex items-center justify-center text-[var(--text-secondary)]">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
            </div>
            <strong class="block text-sm text-[var(--text-primary)] mb-1">暂无月度报告</strong>
            <p class="text-xs text-[var(--text-secondary)]">抓取邮件并完成入库后，报告将按月份显示在这里。</p>
          </div>
        </div>
      </aside>
      
      <article class="flex-1 min-h-0 glass rounded-2xl border border-[var(--border-color)] flex flex-col overflow-hidden">
        <header v-if="selected" class="h-14 px-6 border-b border-[var(--border-color)] bg-[var(--surface-color)]/50 flex items-center justify-between flex-shrink-0">
          <h2 class="font-bold text-lg text-[var(--text-primary)]">{{ selected.filename.replace('.md', '') }}</h2>
          <el-switch v-model="rawView" active-text="Markdown" class="ml-4" />
        </header>
        
        <div class="flex-1 overflow-y-auto bg-[var(--surface-color)]/30 backdrop-blur-sm p-6 lg:p-8">
          <div v-if="!selected" class="h-full flex flex-col items-center justify-center text-[var(--text-secondary)]">
            <svg class="w-16 h-16 mb-4 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/></svg>
            <p class="text-lg font-medium">从左侧选择一份报告以查看</p>
          </div>
          <pre v-else-if="rawView" class="font-mono text-sm text-[var(--text-primary)] whitespace-pre-wrap leading-relaxed">{{ reportMarkdown }}</pre>
          <div v-else class="report-body" v-html="reportHtml" />
        </div>
      </article>
    </div>
  </section>
</template>
