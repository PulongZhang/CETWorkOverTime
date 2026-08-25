export interface MonthSummary {
  month: number
  hours: number
  entries: number
  target: number
  delta: number
}

export interface YearSummary {
  year: number
  months: MonthSummary[]
  total_hours: number
  total_target: number
  total_delta: number
}

export interface DiligenceResponse {
  target_hours: number
  years: Record<string, YearSummary>
}

export interface DayDetail {
  date: string
  subject: string
  hours: number
  start: string | null
  end: string | null
  content: string
}

export interface ReportSummary {
  year: number
  month: number
  filename: string
  entries: number
  hours: number
}

export interface TaskStatus {
  running: boolean
  type: string | null
  message: string
  started_at: string | null
  finished_at: string | null
}

export interface SystemStatus {
  stats: {
    email_count: number
    report_count: number
    imap_configured: boolean
    smtp_configured: boolean
  }
  scheduler: {
    enabled: boolean
    schedule_time: string
    next_run: string | null
    last_run: string | null
    last_result: string | null
  }
  task: TaskStatus
}
