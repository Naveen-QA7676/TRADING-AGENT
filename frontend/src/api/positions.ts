import { api } from './client'

export interface Position {
  id: number
  symbol: string
  direction: 'LONG' | 'SHORT'
  quantity: number
  avg_price: number
  current_price: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  stop_loss: number
  target_1: number
  target_2: number
  mae: number
  mfe: number
  entry_time: string
}

export interface DailyPnL {
  date: string
  total_pnl: number
  gross_pnl: number
  charges: number
  trade_count: number
  win_count: number
  loss_count: number
}

export const positionsApi = {
  getAll: () => api.get<Position[]>('/positions/').then((r) => r.data),
  getLive: () => api.get<{ count: number; positions: Position[] }>('/positions/live').then((r) => r.data),
  getDailyPnL: () => api.get<DailyPnL>('/positions/daily-pnl').then((r) => r.data),
  partialExit: (position_id: number, quantity: number, price = 0) =>
    api.post('/positions/partial-exit', { position_id, quantity, price }).then((r) => r.data),
  squareoffAll: () => api.post('/positions/squareoff-all').then((r) => r.data),
  moveSlToEntry: (id: number) => api.post(`/positions/${id}/move-sl-to-entry`).then((r) => r.data),
}
