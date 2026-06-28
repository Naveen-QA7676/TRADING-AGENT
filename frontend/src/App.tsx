import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useEffect } from 'react'
import { Layout } from './components/layout/Layout'
import { MorningBrief } from './pages/MorningBrief'
import { Suggestions } from './pages/Suggestions'
import { Terminal } from './pages/Terminal'
import { Positions } from './pages/Positions'
import { StockExplorer } from './pages/StockExplorer'
import { PredictionBoard } from './pages/PredictionBoard'
import { NewsFeed } from './pages/NewsFeed'
import { Journal } from './pages/Journal'
import { TaxDashboard } from './pages/TaxDashboard'
import { AgentMonitor } from './pages/AgentMonitor'
import { Settings } from './pages/Settings'
import { useStore } from './store/useStore'
import { positionsApi } from './api/positions'
import { newsApi } from './api/news'
import { agentsApi } from './api/agents'
import { suggestionsApi } from './api/suggestions'
import { api } from './api/client'

function DataPoller() {
  const { setSuggestions, setPositions, setDailyPnL, setNews, setBreakingNews, setAgents, setConnected, setMarketContext } = useStore()

  useEffect(() => {
    async function pollAll() {
      try {
        const [sugg, live, daily, news, breaking, agents, status] = await Promise.allSettled([
          suggestionsApi.getActive(),
          positionsApi.getLive(),
          positionsApi.getDailyPnL(),
          newsApi.getAll(30),
          newsApi.getBreaking(),
          agentsApi.getAll(),
          api.get('/status').then((r) => r.data),
        ])

        if (sugg.status === 'fulfilled') setSuggestions(sugg.value)
        if (live.status === 'fulfilled') setPositions(live.value.positions)
        if (daily.status === 'fulfilled') setDailyPnL(daily.value)
        if (news.status === 'fulfilled') setNews(news.value)
        if (breaking.status === 'fulfilled') setBreakingNews(breaking.value)
        if (agents.status === 'fulfilled') setAgents(agents.value)
        if (status.status === 'fulfilled') {
          setConnected(status.value.broker_connected ?? false)
        }

        // Pull regime + FII/VIX from scanner morning-brief
        try {
          const brief = await api.get('/scanner/morning-brief').then((r) => r.data)
          setMarketContext({
            regime: brief.market_regime ?? 'UNKNOWN',
            niftyBias: 72,
            vix: brief.global_data?.india_vix ?? 0,
            fii: brief.fii_dii?.fii_net ?? 0,
          })
        } catch {
          // keep existing context
        }
      } catch {
        // silent
      }
    }

    pollAll()
    const id = setInterval(pollAll, 5000)
    return () => clearInterval(id)
  }, [setSuggestions, setPositions, setDailyPnL, setNews, setBreakingNews, setAgents, setConnected, setMarketContext])

  return null
}

export default function App() {
  return (
    <BrowserRouter>
      <DataPoller />
      <Layout>
        <Routes>
          <Route path="/" element={<MorningBrief />} />
          <Route path="/signals" element={<Suggestions />} />
          <Route path="/terminal" element={<Terminal />} />
          <Route path="/positions" element={<Positions />} />
          <Route path="/explore" element={<StockExplorer />} />
          <Route path="/predict" element={<PredictionBoard />} />
          <Route path="/news" element={<NewsFeed />} />
          <Route path="/journal" element={<Journal />} />
          <Route path="/tax" element={<TaxDashboard />} />
          <Route path="/agents" element={<AgentMonitor />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
