import { api } from './client'

export interface AgentStatus {
  name: string
  status: 'ACTIVE' | 'WAITING' | 'SLEEP' | 'ERROR'
  last_run: string | null
  last_output: string | null
  run_count: number
  error_count: number
}

export const agentsApi = {
  getAll: () => api.get<AgentStatus[]>('/agents/').then((r) => r.data),
  getOne: (name: string) => api.get<AgentStatus>(`/agents/${name}`).then((r) => r.data),
}
