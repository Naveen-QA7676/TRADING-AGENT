import { api } from './client'

export interface TaxSummary {
  fy: string
  pnl_report: {
    speculative_income: number
    speculative_loss: number
    net_speculative: number
    stcg: number
    ltcg: number
    total_net_pnl: number
    estimated_tax: number
    net_after_tax: number
    advance_tax_sep: number
  }
  turnover: {
    speculative: number
    delivery: number
    total: number
    audit_required: boolean
    gst_required: boolean
  }
  charges: {
    brokerage: number
    stt: number
    exchange_charges: number
    gst: number
    stamp_duty: number
    total: number
  }
}

export interface MonthlyBreakdown {
  fy: string
  monthly: Record<string, number>
}

export const taxApi = {
  getSummary:  (fy = '2025-26') => api.get<TaxSummary>(`/tax/summary?fy=${fy}`).then((r) => r.data),
  getMonthly:  (fy = '2025-26') => api.get<MonthlyBreakdown>(`/tax/monthly?fy=${fy}`).then((r) => r.data),
  downloadPnL: (fy = '2025-26') => `/api/tax/download/pnl-csv?fy=${fy}`,
  downloadITR: (fy = '2025-26') => `/api/tax/download/itr-summary?fy=${fy}`,
}
