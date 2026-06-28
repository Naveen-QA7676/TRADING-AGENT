import { api } from './client'

export interface JournalTrade {
  id: number
  symbol: string
  direction: 'LONG' | 'SHORT'
  entry: number
  exit: number | null
  qty: number
  pnl: number
  r_multiple: number
  setup: string
  date: string
  duration: string | null
  tags: string[]
  mistake: string | null
}

export interface PerformanceStats {
  total_trades: number
  win_rate: number
  avg_win: number
  avg_loss: number
  profit_factor: number
  expectancy: number
  max_drawdown: number
  sharpe: number
  equity_curve: { date: string; equity: number }[]
  r_distribution: { bucket: string; count: number }[]
  by_setup: { setup: string; trades: number; win_rate: number; avg_r: number }[]
  by_hour: { hour: string; win_rate: number; trades: number }[]
}

export const journalApi = {
  getTrades: (days = 30) =>
    api.get<JournalTrade[]>('/journal/trades', { params: { days } }).then((r) => r.data),
  getStats: (days = 30) =>
    api.get<PerformanceStats>('/journal/stats', { params: { days } }).then((r) => r.data),
  addEntry: (body: { trade_id: number; mood: string; notes: string; lesson: string; rating: number }) =>
    api.post('/journal/entry', body).then((r) => r.data),
  getEntries: (limit = 50) =>
    api.get('/journal/entries', { params: { limit } }).then((r) => r.data),
}
