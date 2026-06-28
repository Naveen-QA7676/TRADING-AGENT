import { api } from './client'

export interface NewsItem {
  id: number
  title: string
  source: string
  url: string
  summary: string
  sentiment: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  impact_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'BREAKING'
  symbols: string[]
  category: string
  published_at: string
}

export const newsApi = {
  getAll: (limit = 50, sentiment?: string, impact?: string) => {
    const params: Record<string, unknown> = { limit }
    if (sentiment) params.sentiment = sentiment
    if (impact) params.impact = impact
    return api.get<NewsItem[]>('/news/', { params }).then((r) => r.data)
  },
  getBreaking: () => api.get<NewsItem[]>('/news/breaking').then((r) => r.data),
  getBySymbol: (symbol: string) => api.get<NewsItem[]>(`/news/symbol/${symbol}`).then((r) => r.data),
  refresh: () => api.post('/news/refresh').then((r) => r.data),
}
