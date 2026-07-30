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

function deltaClass(delta: number) {
  return delta >= 0 ? 'positive' : 'negative'
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
  <section>
    <div class="page-heading">
      <div>
        <span class="eyebrow">DILIGENCE OVERVIEW</span>
        <h1>勤奋时间仪表板</h1>
        <p>按年度和月份查看工作日志中的投入时间、目标与完成情况。</p>
      </div>
      <el-button :loading="loading" @click="loadDashboard">刷新数据</el-button>
    </div>

    <div v-if="loading" class="dashboard-skeleton" aria-label="正在加载统计数据">
      <div v-for="item in 3" :key="item" class="skeleton-block" />
    </div>
    <div v-else-if="errorMessage" class="state-card error-state" role="alert">
      <span class="state-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24">
          <path d="M12 4 3.5 19h17z" />
          <path d="M12 9v4M12 16.5v.1" />
        </svg>
      </span>
      <div>
        <strong>统计数据暂时无法加载</strong>
        <p>{{ errorMessage }}</p>
      </div>
      <el-button @click="loadDashboard">重新加载</el-button>
    </div>
    <div v-else-if="years.length === 0" class="state-card empty-state">
      <span class="state-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24">
          <path d="M5 5h14v14H5zM8 9h8M8 13h5" />
        </svg>
      </span>
      <div>
        <strong>尚无工作日志数据</strong>
        <p>完成邮件抓取后，这里将展示月度投入时间和目标进度。</p>
      </div>
    </div>

    <div v-else class="metric-strip" aria-label="全部年度汇总">
      <div>
        <span>累计投入</span>
        <strong>{{ overview.totalHours.toFixed(1) }}<small>h</small></strong>
      </div>
      <div>
        <span>累计目标</span>
        <strong>{{ overview.totalTarget.toFixed(0) }}<small>h</small></strong>
      </div>
      <div>
        <span>日志记录</span>
        <strong>{{ overview.totalEntries }}<small>条</small></strong>
      </div>
    </div>

    <article v-for="[year, summary] in years" :key="year" class="year-panel">
      <header class="year-header">
        <div>
          <span class="eyebrow">YEAR</span>
          <h2>{{ year }}</h2>
        </div>
        <div class="year-metrics">
          <div><span>累计</span><strong>{{ summary.total_hours.toFixed(1) }}h</strong></div>
          <div><span>目标</span><strong>{{ summary.total_target.toFixed(0) }}h</strong></div>
          <div>
            <span>差值</span>
            <strong :class="deltaClass(summary.total_delta)">
              {{ summary.total_delta > 0 ? '+' : '' }}{{ summary.total_delta.toFixed(1) }}h
            </strong>
          </div>
        </div>
      </header>

      <div class="month-grid">
        <button
          v-for="month in summary.months"
          :key="month.month"
          class="month-card"
          type="button"
          @click="openMonth(Number(year), month.month)"
        >
          <div class="month-card-header">
            <span>{{ month.month }}月</span>
            <small>{{ month.entries }} 条记录</small>
          </div>
          <strong>{{ month.hours.toFixed(1) }}<small> / {{ month.target }}h</small></strong>
          <span class="delta-label" :class="deltaClass(month.delta)">
            {{ month.delta >= 0 ? '✓ 达标' : '↓ 未达标' }}
            · {{ month.delta > 0 ? '+' : '' }}{{ month.delta.toFixed(1) }}h
          </span>
          <div
            class="progress-track"
            role="progressbar"
            :aria-label="`${month.month}月目标完成率`"
            :aria-valuenow="Math.round(progress(month))"
            aria-valuemin="0"
            aria-valuemax="100"
          >
            <div class="progress-fill" :style="{ width: `${progress(month)}%` }" />
          </div>
        </button>
      </div>
    </article>

    <el-drawer v-model="detailVisible" :title="selectedTitle" size="min(720px, 92vw)">
      <div v-loading="detailLoading" class="daily-list">
        <button v-for="day in days" :key="day.date" class="daily-row" @click="selectedDay = day">
          <span>{{ day.date }}</span>
          <strong>{{ day.hours.toFixed(2) }}h</strong>
          <small>{{ day.start || '--:--' }} – {{ day.end || '--:--' }}</small>
          <em>{{ day.subject || '无主题' }}</em>
        </button>
      </div>
    </el-drawer>

    <el-dialog
      :model-value="Boolean(selectedDay)"
      :title="`${selectedDay?.date ?? ''} 工作记录`"
      width="min(640px, 92vw)"
      @update:model-value="selectedDay = null"
    >
      <pre class="email-content">{{ selectedDay?.content }}</pre>
    </el-dialog>
  </section>
</template>
