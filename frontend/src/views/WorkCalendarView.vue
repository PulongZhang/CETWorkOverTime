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

function getDayStatus(day: string) {
  if (!calendar.value) return { isWork: true, label: '' }
  
  if (calendar.value.leave_dates.includes(day)) {
    return { kind: 'leave', label: '假', isWork: false, class: 'bg-orange-500 text-white' }
  }
  if (calendar.value.holidays.includes(day)) {
    return { kind: 'holiday', label: '休', isWork: false, class: 'bg-green-500 text-white' }
  }
  if (calendar.value.makeup_workdays.includes(day)) {
    return { kind: 'makeup', label: '班', isWork: true, class: 'bg-blue-500 text-white' }
  }
  
  const dateObj = new Date(day)
  const isWeekend = dateObj.getDay() === 0 || dateObj.getDay() === 6
  if (isWeekend) {
    return { kind: 'weekend', label: '休', isWork: false, class: 'text-gray-400 bg-gray-100 dark:bg-gray-800' }
  }
  
  return { kind: 'workday', label: '', isWork: true, class: '' }
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
        ? `已保存 ${addedCount} 个请假工作日，届时将跳过检查。`
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
  <section class="space-y-6 h-full flex flex-col">
    <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
      <div>
        <span class="text-blue-500 font-bold text-xs tracking-widest uppercase">Work Calendar</span>
        <h1 class="text-3xl font-bold mt-1 mb-2 text-[var(--text-primary)]">请假与日历</h1>
        <p class="text-[var(--text-secondary)] text-sm max-w-2xl">登记请假、查看法定节假日与调休补班，自动判断是否需要提交工作计划。</p>
      </div>
      <el-button :loading="loading" @click="loadCalendar" type="primary" plain class="!rounded-xl">刷新日历</el-button>
    </div>

    <div v-if="errorMessage && !calendar" class="flex items-center gap-4 p-6 rounded-2xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-red-600 dark:text-red-400" role="alert">
      <div class="w-12 h-12 rounded-xl flex items-center justify-center bg-red-100 dark:bg-red-500/20 shrink-0">
        <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
      </div>
      <div class="flex-1">
        <strong class="block text-lg mb-1">工作日历暂时无法加载</strong>
        <p class="text-sm opacity-80">{{ errorMessage }}</p>
      </div>
      <el-button @click="loadCalendar" type="danger" plain class="!rounded-xl">重新加载</el-button>
    </div>

    <template v-else>
      <div v-if="calendar" class="glass rounded-2xl p-5 border border-[var(--border-color)] flex flex-col sm:flex-row items-start sm:items-center gap-4 shadow-sm transition-colors" :class="calendar.today.required ? 'bg-blue-50/50 dark:bg-blue-500/5' : 'bg-[var(--surface-color)]/50'">
        <div class="flex items-center gap-4 flex-1">
          <div class="w-10 h-10 rounded-full flex items-center justify-center shadow-inner" :class="calendar.today.required ? 'bg-blue-100 dark:bg-blue-500/20 text-blue-500' : 'bg-gray-100 dark:bg-gray-800 text-gray-400'">
            <div class="w-3 h-3 rounded-full" :class="calendar.today.required ? 'bg-blue-500 animate-pulse' : 'bg-gray-400'"></div>
          </div>
          <div>
            <div class="text-xs font-semibold tracking-wide uppercase text-[var(--text-secondary)] mb-0.5">今天 · {{ calendar.today.date }}</div>
            <strong class="text-lg font-bold text-[var(--text-primary)]">
              {{ calendar.today.required ? '需要提交工作计划' : '无需提交工作计划' }}
            </strong>
          </div>
        </div>
        <div class="px-4 py-1.5 rounded-full text-sm font-medium border" :class="calendar.today.required ? 'bg-blue-100 border-blue-200 text-blue-700 dark:bg-blue-500/20 dark:border-blue-500/30 dark:text-blue-400' : 'bg-gray-100 border-gray-200 text-gray-600 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-400'">
          {{ calendar.today.reason }}
        </div>
      </div>

      <div v-loading="loading" class="flex-1 flex flex-col lg:flex-row gap-6 min-h-0">
        <!-- Calendar View -->
        <div class="flex-1 glass rounded-2xl border border-[var(--border-color)] shadow-sm overflow-hidden flex flex-col p-2">
          <el-calendar class="!bg-transparent">
            <template #date-cell="{ data }">
              <div class="w-full h-full flex flex-col p-1 group relative">
                <div class="text-sm font-medium mb-1 z-10" :class="[
                  data.isSelected ? 'text-blue-500' : 'text-[var(--text-primary)]',
                  !getDayStatus(data.day).isWork && 'opacity-60'
                ]">
                  {{ data.day.split('-').pop() }}
                </div>
                
                <div v-if="getDayStatus(data.day).label" 
                     class="absolute top-1 right-1 w-5 h-5 flex items-center justify-center rounded text-[10px] font-bold shadow-sm z-10"
                     :class="getDayStatus(data.day).class">
                  {{ getDayStatus(data.day).label }}
                </div>
                
                <div v-if="!getDayStatus(data.day).isWork" class="absolute inset-0 bg-gray-50/50 dark:bg-gray-900/30 pointer-events-none rounded-lg"></div>
              </div>
            </template>
          </el-calendar>
        </div>

        <!-- Right Side: Add Leave & Rules -->
        <div class="w-full lg:w-96 flex flex-col gap-6 shrink-0">
          <article class="glass rounded-2xl border border-[var(--border-color)] shadow-sm p-6 flex flex-col">
            <header class="flex items-center justify-between mb-5">
              <div>
                <span class="text-[10px] font-bold text-blue-500 tracking-widest uppercase">Personal Leave</span>
                <h2 class="text-xl font-bold text-[var(--text-primary)] mt-0.5">登记请假</h2>
              </div>
              <span class="px-3 py-1 rounded-full bg-[var(--surface-color)] border border-[var(--border-color)] text-xs font-semibold text-[var(--text-secondary)] shadow-inner">
                共 {{ leaveDates.length }} 天
              </span>
            </header>

            <form @submit.prevent="addLeave" class="flex flex-col gap-3 mb-4">
              <el-date-picker
                v-model="dateRange"
                type="daterange"
                value-format="YYYY-MM-DD"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                unlink-panels
                class="!w-full"
              />
              <el-button type="primary" native-type="submit" :loading="saving" class="!rounded-xl !w-full">
                保存请假
              </el-button>
            </form>

            <p v-if="errorMessage" class="text-red-500 text-sm font-medium mb-3" role="alert">{{ errorMessage }}</p>
            <p v-if="successMessage" class="text-green-500 text-sm font-medium mb-3" role="status">{{ successMessage }}</p>

            <div class="flex-1 overflow-y-auto max-h-[300px] border-t border-[var(--border-color)] pt-3">
              <div v-if="leaveDates.length" class="space-y-2">
                <div v-for="leaveDate in leaveDates" :key="leaveDate" class="flex items-center gap-3 p-3 rounded-xl hover:bg-[var(--surface-color)] transition-colors border border-transparent hover:border-[var(--border-color)] group">
                  <div class="w-10 h-10 rounded-xl bg-orange-50 dark:bg-orange-500/10 text-orange-500 flex items-center justify-center font-bold text-sm shadow-inner">
                    {{ leaveDate.slice(8, 10) }}
                  </div>
                  <div class="flex-1 min-w-0">
                    <strong class="block text-sm font-semibold text-[var(--text-primary)] truncate">{{ formatDate(leaveDate) }}</strong>
                    <small class="text-xs text-[var(--text-secondary)]">{{ leaveDate }}</small>
                  </div>
                  <el-popconfirm
                    title="移除这一天的请假设置？"
                    confirm-button-text="移除"
                    cancel-button-text="取消"
                    @confirm="removeLeave(leaveDate)"
                  >
                    <template #reference>
                      <el-button link type="danger" :loading="deletingDate === leaveDate" :disabled="Boolean(deletingDate)" class="opacity-0 group-hover:opacity-100 transition-opacity">
                        移除
                      </el-button>
                    </template>
                  </el-popconfirm>
                </div>
              </div>
              <div v-else class="h-32 flex flex-col items-center justify-center text-center p-4 border border-dashed border-[var(--border-color)] rounded-xl bg-[var(--surface-color)]/30">
                <strong class="text-sm text-[var(--text-primary)] mb-1">暂无请假日期</strong>
                <p class="text-xs text-[var(--text-secondary)]">在上方选择日期范围后保存。</p>
              </div>
            </div>
          </article>

          <aside class="glass rounded-2xl border border-[var(--border-color)] shadow-sm p-6">
            <span class="text-[10px] font-bold text-gray-500 tracking-widest uppercase">Rules</span>
            <h2 class="text-lg font-bold text-[var(--text-primary)] mt-0.5 mb-4">判定规则与图例</h2>
            <ul class="space-y-3">
              <li class="flex items-start gap-3">
                <div class="mt-1 w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold bg-orange-500 text-white shadow-sm shrink-0">假</div>
                <div>
                  <strong class="block text-sm text-[var(--text-primary)]">个人请假</strong>
                  <span class="text-xs text-[var(--text-secondary)]">优先于其他规则，跳过计划提交。</span>
                </div>
              </li>
              <li class="flex items-start gap-3">
                <div class="mt-1 w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold bg-blue-500 text-white shadow-sm shrink-0">班</div>
                <div>
                  <strong class="block text-sm text-[var(--text-primary)]">调休补班 ({{ calendar?.makeup_workdays.length ?? 0 }}天)</strong>
                  <span class="text-xs text-[var(--text-secondary)]">周末但也正常需要提交计划。</span>
                </div>
              </li>
              <li class="flex items-start gap-3">
                <div class="mt-1 w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold bg-green-500 text-white shadow-sm shrink-0">休</div>
                <div>
                  <strong class="block text-sm text-[var(--text-primary)]">法定节假日 ({{ calendar?.holidays.length ?? 0 }}天)</strong>
                  <span class="text-xs text-[var(--text-secondary)]">非周末的节假日自动跳过计划。</span>
                </div>
              </li>
            </ul>
          </aside>
        </div>
      </div>
    </template>
  </section>
</template>

<style>
/* 覆盖 el-calendar 的默认样式以适配毛玻璃和暗色模式 */
.el-calendar {
  --el-calendar-border: var(--border-color);
  --el-calendar-header-border-bottom: var(--border-color);
  --el-calendar-selected-bg-color: transparent;
}
.el-calendar-table td {
  border-bottom: 1px solid var(--border-color);
  border-right: 1px solid var(--border-color);
}
.el-calendar-table td.is-selected {
  background-color: transparent;
}
.el-calendar-table .el-calendar-day {
  padding: 0;
  height: 85px;
}
.el-calendar__header {
  border-bottom: 1px solid var(--border-color);
  padding: 12px 20px;
}
.el-calendar-table thead th {
  padding: 12px 0;
  color: var(--text-secondary);
}
</style>
