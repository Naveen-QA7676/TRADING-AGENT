import { api } from './client'

export interface LiveQuote {
  symbol: string
  ltp: number
  ohlc: { open: number; high: number; low: number; close: number }
  volume: number
  change: number
  depth: {
    buy:  { price: number; quantity: number; orders: number }[]
    sell: { price: number; quantity: number; orders: number }[]
  }
}

export interface OrderRequest {
  symbol: string
  transaction_type: 'BUY' | 'SELL'
  quantity: number
  price?: number
  trigger_price?: number
  product?: 'MIS' | 'CNC' | 'NRML'
  order_type?: 'LIMIT' | 'MARKET' | 'SL' | 'SL-M'
}

export interface GTTRequest {
  symbol: string
  direction: 'LONG' | 'SHORT'
  quantity: number
  stop_loss: number
  target: number
  ltp: number
}

export interface Margins {
  available: number
  used: number
  net: number
}

export const terminalApi = {
  getQuote:   (symbol: string) => api.get<LiveQuote>(`/terminal/quote/${symbol}`).then((r) => r.data),
  placeOrder: (body: OrderRequest) => api.post('/terminal/order', body).then((r) => r.data),
  setGTT:     (body: GTTRequest)   => api.post('/terminal/gtt', body).then((r) => r.data),
  getOrders:  () => api.get('/terminal/orders').then((r) => r.data),
  cancelOrder:(id: string) => api.delete(`/terminal/order/${id}`).then((r) => r.data),
  getMargins: () => api.get<Margins>('/terminal/margins').then((r) => r.data),
  getCandles: (symbol: string, interval: string, days = 5) =>
    api.get(`/stocks/${symbol}/candles`, { params: { interval, days } }).then((r) => r.data),
}
