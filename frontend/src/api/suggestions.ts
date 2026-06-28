import { api } from './client'

export interface Suggestion {
  id: number
  symbol: string
  exchange: string
  direction: 'LONG' | 'SHORT'
  strategy_name: string
  confidence_score: number
  entry_price_low: number
  entry_price_high: number
  entry_price: number
  stop_loss: number
  target_1: number
  target_2: number
  invalidation_level: number
  quantity: number
  capital_deployed: number
  risk_amount: number
  risk_pct: number
  rr_ratio: number
  win_probability: number
  stop_probability: number
  sideways_probability: number
  agent_scores: Record<string, number>
  reasons_for: string[]
  reasons_against: string[]
  setup_conditions: string[]
  indicators_snapshot: Record<string, unknown>
  chart_pattern: string
  candlestick_pattern: string
  historical_win_rate: number
  historical_trades_count: number
  historical_avg_win_r: number
  historical_avg_loss_r: number
  historical_expectancy: number
  nifty_bias: string
  banknifty_bias: string
  vix_level: number
  fii_net_flow: number
  market_regime: string
  status: string
  created_at: string
  expires_at: string
}

export const suggestionsApi = {
  getActive: () => api.get<Suggestion[]>('/suggestions/').then((r) => r.data),
  getLatest: () => api.get<{ suggestion: Suggestion | null }>('/suggestions/latest').then((r) => r.data),
  getById: (id: number) => api.get<Suggestion>(`/suggestions/${id}`).then((r) => r.data),
  decide: (id: number, decision: 'YES' | 'NO', notes = '') =>
    api.post(`/suggestions/${id}/decision`, { suggestion_id: id, decision, notes }).then((r) => r.data),
  expire: (id: number) => api.delete(`/suggestions/${id}`).then((r) => r.data),
}
