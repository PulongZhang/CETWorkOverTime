<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api, getErrorMessage } from '../api/client'
import type { DayDetail, DiligenceResponse, MonthSummary } from '../types/api'

const data = ref<DiligenceResponse | null>(null)
const loading = ref(true)
const errorMessage = ref('')
const detailVisible = ref(false)
const detailLoading = ref(false)
const selectedTitle = ref('')
const days = ref<DayDetail[]>([])
const selectedDay = ref<DayDetail | null>(null)

const years = computed(() =>
  Object.entries(data.value?.years ?? {}).sort(([left], [right]) => Number(right) - Number(left)),
)
const overview = computed(() => {
  const summaries = years.value.map(([, summary]) => summary)
  return {
    totalHours: summaries.reduce((total, summary) => total + summary.total_hours, 0),
    totalTarget: summaries.reduce((total, summary) => total + summary.total_target, 0),
    totalEntries: summaries.reduce(
      (total, summary) =>
        total + summary.months.reduce((monthTotal, month) => monthTotal + month.entries, 0),
      0,
    ),
  }
})

function progress(month: MonthSummary) {
  return Math.min((month.hours / month.target) * 100, 100)
}

async function loadDashboard() {
  loading.value = true
  errorMessage.value = ''
  try {
    data.value = (await api.get<DiligenceResponse>('/diligence')).data
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function openMonth(year: number, month: number) {
  detailVisible.value = true
  detailLoading.value = true
  selectedTitle.value = `${year}年${month}月明细`
  try {
    days.value = (await api.get<{ days: DayDetail[] }>(`/diligence/${year}/${month}`)).data.days
  } finally {
    detailLoading.value = false
  }
}

onMounted(loadDashboard)
</script>

<template>
  <section class="space-y-6">
    <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
      <div>
        <span class="text-blue-500 font-bold text-xs tracking-widest uppercase">Diligence Overview</span>
        <h1 class="text-3xl font-bold mt-1 mb-2 text-[var(--text-primary)]">勤奋时间仪表板</h1>
        <p class="text-[var(--text-secondary)] text-sm max-w-2xl">按年度和月份查看工作日志中的投入时间、目标与完成情况。</p>
      </div>
      <el-button :loading="loading" @click="loadDashboard" type="primary" plain>刷新数据</el-button>
    </div>

    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-3 gap-4" aria-label="正在加载统计数据">
      <div v-for="item in 3" :key="item" class="h-28 rounded-2xl bg-gradient-to-r from-[var(--border-color)] to-[var(--surface-color)] animate-pulse" />
    </div>
    <div v-else-if="errorMessage" class="flex flex-col sm:flex-row items-center gap-4 p-6 rounded-2xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-red-600 dark:text-red-400" role="alert">
      <div class="w-12 h-12 rounded-xl flex items-center justify-center bg-red-100 dark:bg-red-500/20 shrink-0">
        <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>
      <div class="flex-1 text-center sm:text-left">
        <strong class="block text-lg mb-1">统计数据暂时无法加载</strong>
        <p class="text-sm opacity-80">{{ errorMessage }}</p>
      </div>
      <el-button @click="loadDashboard" type="danger" plain>重新加载</el-button>
    </div>
    <div v-else-if="years.length === 0" class="flex flex-col sm:flex-row items-center gap-4 p-6 rounded-2xl glass text-[var(--text-secondary)] text-center sm:text-left">
      <div class="w-12 h-12 rounded-xl flex items-center justify-center bg-blue-100 dark:bg-blue-500/20 text-blue-500 shrink-0">
        <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
        </svg>
      </div>
      <div>
        <strong class="block text-lg text-[var(--text-primary)] mb-1">尚无工作日志数据</strong>
        <p class="text-sm">完成邮件抓取后，这里将展示月度投入时间和目标进度。</p>
      </div>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-5">
      <div class="relative overflow-hidden glass rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow group">
        <div class="absolute right-0 top-0 w-24 h-24 bg-blue-500/10 rounded-bl-full -mr-4 -mt-4 transition-transform group-hover:scale-110 pointer-events-none"></div>
        <div class="flex items-center gap-4 relative z-10">
          <div class="w-12 h-12 rounded-xl bg-blue-50 dark:bg-blue-500/10 flex items-center justify-center text-blue-500 shadow-inner">
            <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          </div>
          <div>
            <span class="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">累计投入</span>
            <div class="text-3xl font-bold mt-0.5 text-[var(--text-primary)]">{{ overview.totalHours.toFixed(1) }}<span class="text-sm font-medium text-[var(--text-secondary)] ml-1">h</span></div>
          </div>
        </div>
      </div>
      
      <div class="relative overflow-hidden glass rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow group">
        <div class="absolute right-0 top-0 w-24 h-24 bg-purple-500/10 rounded-bl-full -mr-4 -mt-4 transition-transform group-hover:scale-110 pointer-events-none"></div>
        <div class="flex items-center gap-4 relative z-10">
          <div class="w-12 h-12 rounded-xl bg-purple-50 dark:bg-purple-500/10 flex items-center justify-center text-purple-500 shadow-inner">
            <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
          </div>
          <div>
            <span class="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">累计目标</span>
            <div class="text-3xl font-bold mt-0.5 text-[var(--text-primary)]">{{ overview.totalTarget.toFixed(0) }}<span class="text-sm font-medium text-[var(--text-secondary)] ml-1">h</span></div>
          </div>
        </div>
      </div>
      
      <div class="relative overflow-hidden glass rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow group">
        <div class="absolute right-0 top-0 w-24 h-24 bg-green-500/10 rounded-bl-full -mr-4 -mt-4 transition-transform group-hover:scale-110 pointer-events-none"></div>
        <div class="flex items-center gap-4 relative z-10">
          <div class="w-12 h-12 rounded-xl bg-green-50 dark:bg-green-500/10 flex items-center justify-center text-green-500 shadow-inner">
            <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          </div>
          <div>
            <span class="text-xs font-semibold text-[var(--text-secondary)] uppercase tracking-wider">日志记录</span>
            <div class="text-3xl font-bold mt-0.5 text-[var(--text-primary)]">{{ overview.totalEntries }}<span class="text-sm font-medium text-[var(--text-secondary)] ml-1">条</span></div>
          </div>
        </div>
      </div>
    </div>

    <article v-for="[year, summary] in years" :key="year" class="glass rounded-2xl p-6">
      <header class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--border-color)]">
        <div>
          <span class="text-blue-500 font-bold text-xs tracking-widest uppercase">Year</span>
          <h2 class="text-3xl font-bold mt-1 text-[var(--text-primary)]">{{ year }}</h2>
        </div>
        <div class="flex gap-6 text-right">
          <div><span class="block text-xs text-[var(--text-secondary)]">累计</span><strong class="text-lg font-bold text-[var(--text-primary)]">{{ summary.total_hours.toFixed(1) }}h</strong></div>
          <div><span class="block text-xs text-[var(--text-secondary)]">目标</span><strong class="text-lg font-bold text-[var(--text-primary)]">{{ summary.total_target.toFixed(0) }}h</strong></div>
          <div>
            <span class="block text-xs text-[var(--text-secondary)]">差值</span>
            <strong class="text-lg font-bold" :class="summary.total_delta >= 0 ? 'text-green-500' : 'text-red-500'">
              {{ summary.total_delta > 0 ? '+' : '' }}{{ summary.total_delta.toFixed(1) }}h
            </strong>
          </div>
        </div>
      </header>

      <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-5 mt-6">
        <button
          v-for="month in summary.months"
          :key="month.month"
          class="relative flex flex-col gap-3 p-5 rounded-2xl border border-[var(--border-color)] bg-[var(--surface-color)]/60 backdrop-blur-sm hover:bg-[var(--surface-color)] shadow-sm hover:shadow-xl hover:shadow-blue-500/10 hover:-translate-y-1.5 transition-all duration-300 text-left group overflow-hidden"
          type="button"
          @click="openMonth(Number(year), month.month)"
        >
          <!-- 装饰性渐变背景 -->
          <div class="absolute -right-8 -top-8 w-24 h-24 bg-blue-500/5 rounded-full blur-2xl group-hover:bg-blue-500/10 transition-colors pointer-events-none"></div>
          
          <div class="flex justify-between items-center w-full text-sm z-10">
            <span class="font-semibold text-[var(--text-primary)] text-base">{{ month.month }}月</span>
            <span class="text-xs font-medium px-2 py-0.5 rounded-full bg-[var(--border-color)]/50 text-[var(--text-secondary)]">{{ month.entries }} 记录</span>
          </div>
          <div class="text-3xl font-extrabold tracking-tight text-[var(--text-primary)] group-hover:text-blue-500 transition-colors z-10 mt-1">
            {{ month.hours.toFixed(1) }}<span class="text-sm font-medium text-[var(--text-secondary)] ml-1">/ {{ month.target }}h</span>
          </div>
          
          <div class="flex items-center gap-1.5 z-10 mt-1">
            <span class="flex items-center justify-center w-4 h-4 rounded-full" :class="month.delta >= 0 ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'">
              <svg v-if="month.delta >= 0" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
              <svg v-else class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 14l-7 7m0 0l-7-7m7 7V3"/></svg>
            </span>
            <span class="text-xs font-bold" :class="month.delta >= 0 ? 'text-green-500' : 'text-red-500'">
              {{ month.delta >= 0 ? '达标' : '未达标' }} <span class="opacity-75 font-medium ml-0.5">{{ month.delta > 0 ? '+' : '' }}{{ month.delta.toFixed(1) }}h</span>
            </span>
          </div>
          
          <div class="w-full h-2 bg-[var(--border-color)]/60 rounded-full overflow-hidden mt-2 z-10" role="progressbar" :aria-valuenow="Math.round(progress(month))" aria-valuemin="0" aria-valuemax="100">
            <div class="h-full rounded-full transition-all duration-1000 ease-out" 
                 :class="progress(month) >= 100 ? 'bg-green-500' : 'bg-blue-500'" 
                 :style="{ width: `${progress(month)}%` }" />
          </div>
        </button>
      </div>
    </article>

    <el-drawer v-model="detailVisible" :title="selectedTitle" size="min(720px, 92vw)">
      <div v-loading="detailLoading" class="flex flex-col gap-2">
        <button v-for="day in days" :key="day.date" class="grid grid-cols-[100px_70px_120px_1fr] items-center gap-4 p-3 rounded-xl border border-[var(--border-color)] bg-[var(--surface-color)] hover:bg-[var(--border-color)] transition-colors text-left" @click="selectedDay = day">
          <span class="text-sm text-[var(--text-primary)]">{{ day.date }}</span>
          <strong class="text-green-500">{{ day.hours.toFixed(2) }}h</strong>
          <span class="text-xs text-[var(--text-secondary)] truncate">{{ day.start || '--:--' }} – {{ day.end || '--:--' }}</span>
          <span class="text-xs text-[var(--text-secondary)] truncate">{{ day.subject || '无主题' }}</span>
        </button>
      </div>
    </el-drawer>

    <el-dialog
      :model-value="Boolean(selectedDay)"
      :title="`${selectedDay?.date ?? ''} 工作记录`"
      width="min(640px, 92vw)"
      @update:model-value="selectedDay = null"
    >
      <pre class="p-4 rounded-xl border border-[var(--border-color)] bg-[var(--surface-color)] text-sm text-[var(--text-primary)] whitespace-pre-wrap font-mono">{{ selectedDay?.content }}</pre>
    </el-dialog>
  </section>
</template>
