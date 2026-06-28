import { create } from 'zustand'
import type { Suggestion } from '../api/suggestions'
import type { Position, DailyPnL } from '../api/positions'
import type { NewsItem } from '../api/news'
import type { AgentStatus } from '../api/agents'

interface AppStore {
  // Suggestions
  suggestions: Suggestion[]
  activeSuggestionId: number | null
  setSuggestions: (s: Suggestion[]) => void
  addSuggestion: (s: Suggestion) => void
  removeSuggestion: (id: number) => void
  setActiveSuggestion: (id: number | null) => void

  // Positions
  positions: Position[]
  dailyPnL: DailyPnL | null
  setPositions: (p: Position[]) => void
  setDailyPnL: (d: DailyPnL) => void

  // News
  news: NewsItem[]
  breakingNews: NewsItem[]
  setNews: (n: NewsItem[]) => void
  setBreakingNews: (n: NewsItem[]) => void

  // Agents
  agents: AgentStatus[]
  setAgents: (a: AgentStatus[]) => void

  // Market context (from morning brief)
  marketRegime: string
  niftyBias: number
  vixLevel: number
  fiiFlow: number
  setMarketContext: (ctx: { regime: string; niftyBias: number; vix: number; fii: number }) => void

  // System
  isConnected: boolean
  setConnected: (v: boolean) => void
}

export const useStore = create<AppStore>((set) => ({
  suggestions: [],
  activeSuggestionId: null,
  setSuggestions: (suggestions) => set({ suggestions }),
  addSuggestion: (s) =>
    set((state) => ({ suggestions: [...state.suggestions.filter((x) => x.id !== s.id), s] })),
  removeSuggestion: (id) =>
    set((state) => ({ suggestions: state.suggestions.filter((x) => x.id !== id) })),
  setActiveSuggestion: (id) => set({ activeSuggestionId: id }),

  positions: [],
  dailyPnL: null,
  setPositions: (positions) => set({ positions }),
  setDailyPnL: (dailyPnL) => set({ dailyPnL }),

  news: [],
  breakingNews: [],
  setNews: (news) => set({ news }),
  setBreakingNews: (breakingNews) => set({ breakingNews }),

  agents: [],
  setAgents: (agents) => set({ agents }),

  marketRegime: 'UNKNOWN',
  niftyBias: 50,
  vixLevel: 0,
  fiiFlow: 0,
  setMarketContext: ({ regime, niftyBias, vix, fii }) =>
    set({ marketRegime: regime, niftyBias, vixLevel: vix, fiiFlow: fii }),

  isConnected: false,
  setConnected: (isConnected) => set({ isConnected }),
}))
