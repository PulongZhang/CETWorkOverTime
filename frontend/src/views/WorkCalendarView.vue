<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { api, getErrorMessage } from '../api/client'
import type { WorkCalendarResponse } from '../types/api'

const calendar = ref<WorkCalendarResponse | null>(null)
const dateRange = ref<[string, string] | null>(null)
const loading = ref(true)
const saving = ref(false)
const deletingDate = ref('')
const errorMessage = ref('')
const successMessage = ref('')

const leaveDates = computed(() => [...(calendar.value?.leave_dates ?? [])].sort())

function formatDate(value: string) {
  const target = new Date(`${value}T00:00:00`)
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  }).format(target)
}

async function loadCalendar() {
  loading.value = true
  errorMessage.value = ''
  try {
    calendar.value = (await api.get<WorkCalendarResponse>('/work-calendar')).data
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function addLeave() {
  if (!dateRange.value) {
    errorMessage.value = '请先选择请假日期'
    return
  }
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  const [startDate, endDate] = dateRange.value
  const previousCount = leaveDates.value.length
  try {
    calendar.value = (
      await api.post<WorkCalendarResponse>('/work-calendar/leaves', {
        start_date: startDate,
        end_date: endDate,
      })
    ).data
    dateRange.value = null
    const addedCount = leaveDates.value.length - previousCount
    successMessage.value =
      addedCount > 0
        ? `已保存 ${addedCount} 个请假工作日，届时将跳过工作计划检查和自动提交。`
        : '所选范围内没有需要登记的工作日。'
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    saving.value = false
  }
}

async function removeLeave(leaveDate: string) {
  deletingDate.value = leaveDate
  errorMessage.value = ''
  successMessage.value = ''
  try {
    calendar.value = (
      await api.delete<WorkCalendarResponse>(`/work-calendar/leaves/${leaveDate}`)
    ).data
    successMessage.value = `${leaveDate} 的请假设置已移除。`
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    deletingDate.value = ''
  }
}

onMounted(loadCalendar)
</script>

<template>
  <section class="calendar-page">
    <div class="page-heading">
      <div>
        <span class="eyebrow">WORK CALENDAR</span>
        <h1>请假日期</h1>
        <p>登记全天请假后，当天不再检查、提醒或自动提交工作计划。</p>
      </div>
      <el-button :loading="loading" @click="loadCalendar">刷新</el-button>
    </div>

    <div v-if="errorMessage && !calendar" class="state-card error-state" role="alert">
      <div>
        <strong>工作日历暂时无法加载</strong>
        <p>{{ errorMessage }}</p>
      </div>
      <el-button @click="loadCalendar">重新加载</el-button>
    </div>

    <template v-else>
      <div v-if="calendar" class="today-status" :class="{ resting: !calendar.today.required }">
        <span class="today-dot" aria-hidden="true" />
        <div>
          <small>今天 · {{ calendar.today.date }}</small>
          <strong>
            {{ calendar.today.required ? '需要提交工作计划' : '无需提交工作计划' }}
          </strong>
        </div>
        <el-tag :type="calendar.today.required ? 'success' : 'info'" effect="dark">
          {{ calendar.today.reason }}
        </el-tag>
      </div>

      <div v-loading="loading" class="calendar-grid">
        <article class="calendar-card leave-card">
          <header>
            <div>
              <span class="eyebrow">PERSONAL LEAVE</span>
              <h2>添加请假</h2>
            </div>
            <span class="record-count">{{ leaveDates.length }} 天</span>
          </header>

          <form class="leave-form" @submit.prevent="addLeave">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              value-format="YYYY-MM-DD"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              unlink-panels
            />
            <el-button type="primary" native-type="submit" :loading="saving">保存请假</el-button>
          </form>

          <p v-if="errorMessage" class="inline-error" role="alert">{{ errorMessage }}</p>
          <p v-if="successMessage" class="inline-success" role="status">
            {{ successMessage }}
          </p>

          <div v-if="leaveDates.length" class="leave-list">
            <div v-for="leaveDate in leaveDates" :key="leaveDate" class="leave-row">
              <span class="date-icon" aria-hidden="true">{{ leaveDate.slice(8, 10) }}</span>
              <div>
                <strong>{{ formatDate(leaveDate) }}</strong>
                <small>{{ leaveDate }}</small>
              </div>
              <el-popconfirm
                title="移除这一天的请假设置？"
                confirm-button-text="移除"
                cancel-button-text="取消"
                @confirm="removeLeave(leaveDate)"
              >
                <template #reference>
                  <el-button
                    link
                    type="danger"
                    :loading="deletingDate === leaveDate"
                    :disabled="Boolean(deletingDate)"
                  >
                    移除
                  </el-button>
                </template>
              </el-popconfirm>
            </div>
          </div>
          <div v-else class="calendar-empty">
            <strong>暂无请假日期</strong>
            <p>选择单日或日期范围后保存即可。</p>
          </div>
        </article>

        <aside class="calendar-card rule-card">
          <span class="eyebrow">ACTIVE RULES</span>
          <h2>当前规则</h2>
          <ul>
            <li>
              <i class="rule-mark leave" aria-hidden="true" />
              <div><strong>个人请假</strong><span>优先跳过当天计划</span></div>
            </li>
            <li>
              <i class="rule-mark makeup" aria-hidden="true" />
              <div><strong>调休补班</strong><span>周末也会正常检查</span></div>
              <em>{{ calendar?.makeup_workdays.length ?? 0 }} 天</em>
            </li>
            <li>
              <i class="rule-mark holiday" aria-hidden="true" />
              <div><strong>法定节假日</strong><span>自动跳过计划</span></div>
              <em>{{ calendar?.holidays.length ?? 0 }} 天</em>
            </li>
            <li>
              <i class="rule-mark weekend" aria-hidden="true" />
              <div><strong>普通周末</strong><span>自动跳过计划</span></div>
            </li>
          </ul>
          <p class="rule-note">
            日期保存在 <code>output/work_calendar.json</code>，无需数据库。
          </p>
        </aside>
      </div>
    </template>
  </section>
</template>

<style scoped>
.calendar-page {
  max-width: 980px;
  margin: 0 auto;
}

.today-status {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 76px;
  margin-bottom: 20px;
  padding: 14px 18px;
  border: 1px solid rgb(69 214 160 / 24%);
  border-radius: var(--radius-md);
  background: rgb(69 214 160 / 6%);
}

.today-status.resting {
  border-color: var(--border-subtle);
  background: var(--surface-1);
}

.today-dot {
  flex: 0 0 auto;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--status-success);
  box-shadow: 0 0 0 5px rgb(69 214 160 / 12%);
}

.resting .today-dot {
  background: var(--text-muted);
  box-shadow: 0 0 0 5px rgb(143 160 184 / 10%);
}

.today-status > div {
  display: grid;
  flex: 1;
  gap: 3px;
}

.today-status small,
.leave-row small {
  color: var(--text-muted);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.today-status strong {
  color: var(--text-primary);
  font-size: 15px;
}

.calendar-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.85fr);
  gap: 20px;
}

.calendar-card {
  padding: 24px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--surface-1);
}

.calendar-card > header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.calendar-card h2 {
  margin: 5px 0 0;
  color: var(--text-primary);
  font-size: 20px;
}

.record-count {
  padding: 5px 9px;
  border-radius: 999px;
  color: var(--text-secondary);
  background: var(--surface-raised);
  font-size: 12px;
}

.leave-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  margin: 22px 0 18px;
}

.leave-form :deep(.el-date-editor) {
  width: 100%;
}

.inline-error,
.inline-success {
  margin: -6px 0 14px;
  font-size: 13px;
}

.inline-error {
  color: var(--status-danger);
}

.inline-success {
  color: var(--status-success);
}

.leave-list {
  display: grid;
  border-top: 1px solid var(--border-subtle);
}

.leave-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 68px;
  border-bottom: 1px solid var(--border-subtle);
}

.leave-row > div {
  display: grid;
  flex: 1;
  gap: 3px;
}

.leave-row strong {
  color: var(--text-primary);
  font-size: 14px;
}

.date-icon {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  color: #dce9ff;
  background: var(--surface-active);
  font-size: 13px;
  font-weight: 700;
}

.calendar-empty {
  display: grid;
  place-items: center;
  min-height: 150px;
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--text-muted);
  text-align: center;
}

.calendar-empty strong {
  align-self: end;
  color: var(--text-secondary);
  font-size: 14px;
}

.calendar-empty p {
  align-self: start;
  margin: 5px 0 0;
  font-size: 12px;
}

.rule-card > h2 {
  margin-bottom: 20px;
}

.rule-card ul {
  display: grid;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.rule-card li {
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 58px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-subtle);
}

.rule-card li > div {
  display: grid;
  flex: 1;
  gap: 3px;
}

.rule-card li strong {
  color: var(--text-primary);
  font-size: 13px;
}

.rule-card li span,
.rule-card li em {
  color: var(--text-muted);
  font-size: 11px;
  font-style: normal;
}

.rule-mark {
  flex: 0 0 auto;
  width: 9px;
  height: 9px;
  border-radius: 3px;
  background: var(--text-muted);
}

.rule-mark.leave {
  background: var(--status-warning);
}

.rule-mark.makeup {
  background: var(--status-success);
}

.rule-mark.holiday {
  background: var(--status-info);
}

.rule-note {
  margin: 18px 0 0;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.6;
}

.rule-note code {
  color: var(--text-secondary);
}

@media (max-width: 760px) {
  .calendar-grid {
    grid-template-columns: 1fr;
  }

  .leave-form {
    grid-template-columns: 1fr;
  }

  .today-status {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .today-status > div {
    min-width: calc(100% - 30px);
  }
}
</style>
