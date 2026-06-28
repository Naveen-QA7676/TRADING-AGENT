import { api } from './client'

export interface AuthStatus {
  kite_connected: boolean
  user_name: string
  user_id: string
  trading_disabled: boolean
  message: string
}

export const authApi = {
  getStatus: () => api.get<AuthStatus>('/auth/status').then((r) => r.data),
  getLoginUrl: () => api.get<{ login_url: string }>('/auth/login-url').then((r) => r.data),
  logout: () => api.post('/auth/logout').then((r) => r.data),
  resetDailyLimits: () => api.post('/auth/reset-daily-limits').then((r) => r.data),
}
