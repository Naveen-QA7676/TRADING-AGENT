import { api } from './client'

export interface StockQuote {
  symbol: string
  ltp: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  change_pct: number
}

export interface TechnicalSnapshot {
  symbol: string
  timeframes: Record<string, {
    bull_score: number
    buy_count: number
    sell_count: number
    neutral_count: number
    rsi: number | null
    macd_signal: string | null
    vwap: number | null
  } | null>
}

export interface Fundamentals {
  symbol: string
  grade: string
  data: Record<string, unknown>
}

export interface MarketStructure {
  symbol: string
  trend: string
  order_blocks: { dir: string; high: number; low: number }[]
  fvgs: { dir: string; high: number; low: number; filled: boolean }[]
  key_levels: { price: number; type: string; strength: number }[]
}

export const stocksApi = {
  getQuote:       (symbol: string) => api.get<StockQuote>(`/stocks/${symbol}/quote`).then((r) => r.data),
  getCandles:     (symbol: string, interval: string, days = 5) =>
    api.get(`/stocks/${symbol}/candles`, { params: { interval, days } }).then((r) => r.data),
  getTechnical:   (symbol: string) => api.get<TechnicalSnapshot>(`/stocks/${symbol}/technical`).then((r) => r.data),
  getFundamentals:(symbol: string) => api.get<Fundamentals>(`/stocks/${symbol}/fundamentals`).then((r) => r.data),
  getStructure:   (symbol: string) => api.get<MarketStructure>(`/stocks/${symbol}/structure`).then((r) => r.data),
}
