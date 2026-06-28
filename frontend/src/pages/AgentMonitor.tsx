import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Activity, RefreshCw, CheckCircle, Clock, AlertCircle, ZapOff } from 'lucide-react'
import { agentsApi, AgentStatus } from '../api/agents'
import { Card, CardHeader, SectionTitle } from '../components/ui/Card'
import { useStore } from '../store/useStore'
import clsx from 'clsx'

// ─── Types ────────────────────────────────────────────────────────────────────

type Status = 'ACTIVE' | 'WAITING' | 'SLEEP' | 'ERROR'

interface AgentDisplay {
  name: string
  role: string
  group: string
}

// ─── Agent metadata ───────────────────────────────────────────────────────────

const AGENT_META: AgentDisplay[] = [
  // Market Intelligence (7)
  { name: 'market_regime_agent',       role: 'Classifies market regime (trending/ranging/volatile)',         group: 'Market Intelligence' },
  { name: 'multi_tf_agent',            role: 'Multi-timeframe trend alignment (1D/4H/1H/15m)',              group: 'Market Intelligence' },
  { name: 'market_structure_agent',    role: 'Detects S/R levels, HH/HL, LH/LL patterns',                  group: 'Market Intelligence' },
  { name: 'vwap_agent',                role: 'VWAP position, band distances, stretch detection',            group: 'Market Intelligence' },
  { name: 'momentum_agent',            role: 'RSI/MACD/Stoch momentum scoring across timeframes',           group: 'Market Intelligence' },
  { name: 'volume_profile_agent',      role: 'HVN/LVN mapping, volume-at-price analysis',                  group: 'Market Intelligence' },
  { name: 'global_macro_agent',        role: 'SGX/Dow/DXY/crude correlations, gap-up/gap-down strength',   group: 'Market Intelligence' },

  // Execution Intelligence (8)
  { name: 'entry_timing_agent',        role: 'Optimal entry window within session + intraday patterns',     group: 'Execution Intelligence' },
  { name: 'stop_loss_agent',           role: 'ATR-based dynamic SL placement, invalidation points',         group: 'Execution Intelligence' },
  { name: 'target_agent',              role: 'T1/T2 based on S/R, volume nodes, Fibonacci extensions',      group: 'Execution Intelligence' },
  { name: 'position_sizing_agent',     role: 'Risk-per-trade %, Kelly fraction, account % sizing',          group: 'Execution Intelligence' },
  { name: 'risk_reward_agent',         role: 'RR ratio scoring, expected value calculation',                group: 'Execution Intelligence' },
  { name: 'pattern_recognition_agent', role: 'Candlestick + chart pattern detection (flags, W/M, etc.)',    group: 'Execution Intelligence' },
  { name: 'orb_agent',                 role: 'Opening range breakout detection and qualification',          group: 'Execution Intelligence' },
  { name: 'fii_dii_agent',             role: 'Intraday FII/DII flow data → institutional direction bias',  group: 'Execution Intelligence' },

  // Risk & Learning (5)
  { name: 'portfolio_risk_agent',      role: 'Open position correlation, max drawdown guard, exposure %',  group: 'Risk & Learning' },
  { name: 'news_sentiment_agent',      role: 'Real-time news → sentiment score per symbol',                group: 'Risk & Learning' },
  { name: 'historical_edge_agent',     role: 'Back-tests this exact setup: win%, avg R, best times',       group: 'Risk & Learning' },
  { name: 'learning_agent',            role: 'Compares yesterday\'s decisions vs outcomes, updates priors', group: 'Risk & Learning' },
  { name: 'regime_strategy_mapper',    role: 'Maps regime to preferred strategy class + parameters',       group: 'Risk & Learning' },

  // Supervisor (1)
  { name: 'supervisor_agent',          role: 'Aggregates all agent scores → final trade card + confidence', group: 'Supervisor' },
]

// ─── Mock data ────────────────────────────────────────────────────────────────

function buildMockStatus(): AgentStatus[] {
  return AGENT_META.map((a, i) => ({
    name:         a.name,
    status:       (i === 20 ? 'ACTIVE' : i % 7 === 5 ? 'WAITING' : i % 11 === 3 ? 'SLEEP' : 'ACTIVE') as Status,
    last_run:     new Date(Date.now() - (i * 23 + 5) * 1000).toISOString(),
    last_output:  `Score: ${Math.floor(Math.random() * 40 + 55)}/100 · processed HDFCBANK in ${Math.floor(Math.random() * 800 + 200)}ms`,
    run_count:    Math.floor(Math.random() * 200 + 30),
    error_count:  i === 3 ? 1 : 0,
  }))
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function statusIcon(s: Status) {
  const props = { size: 14 }
  const map: Record<Status, React.ReactNode> = {
    ACTIVE:  <CheckCircle {...props} className="text-bull" />,
    WAITING: <Clock {...props} className="text-amber" />,
    SLEEP:   <ZapOff {...props} className="text-muted" />,
    ERROR:   <AlertCircle {...props} className="text-bear" />,
  }
  return map[s]
}

function statusBadge(s: Status) {
  const map: Record<Status, string> = {
    ACTIVE:  'bg-bull/10 text-bull border-bull/30',
    WAITING: 'bg-amber/10 text-amber border-amber/30',
    SLEEP:   'bg-border text-muted border-border',
    ERROR:   'bg-bear/10 text-bear border-bear/30',
  }
  return `px-1.5 py-0.5 rounded text-[10px] border ${map[s]}`
}

function timeAgo(iso: string) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60)   return `${Math.floor(diff)}s`
  if (diff < 3600) return `${Math.floor(diff / 60)}m`
  return `${Math.floor(diff / 3600)}h`
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatusSummary({ agents }: { agents: AgentStatus[] }) {
  const counts: Record<Status, number> = { ACTIVE: 0, WAITING: 0, SLEEP: 0, ERROR: 0 }
  agents.forEach((a) => { counts[a.status as Status]++ })
  return (
    <div className="grid grid-cols-4 gap-3">
      {(Object.entries(counts) as [Status, number][]).map(([s, c]) => (
        <motion.div
          key={s}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center bg-card rounded-lg p-3 border border-border"
        >
          <div className="flex justify-center mb-1">{statusIcon(s)}</div>
          <div className="text-2xl font-bold text-text">{c}</div>
          <div className="text-[10px] text-muted">{s}</div>
        </motion.div>
      ))}
    </div>
  )
}

function AgentTable({ agents, group }: { agents: AgentStatus[]; group: string }) {
  const meta = AGENT_META.filter((m) => m.group === group)
  return (
    <Card>
      <CardHeader>
        <SectionTitle>{group}</SectionTitle>
        <span className="text-xs text-muted">{meta.length} agents</span>
      </CardHeader>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border text-muted text-left">
              <th className="pb-2 font-normal w-4" />
              <th className="pb-2 font-normal">Agent</th>
              <th className="pb-2 font-normal">Status</th>
              <th className="pb-2 font-normal">Last run</th>
              <th className="pb-2 font-normal text-right">Runs</th>
              <th className="pb-2 font-normal">Last output</th>
            </tr>
          </thead>
          <tbody>
            {meta.map((m, i) => {
              const agent = agents.find((a) => a.name === m.name)
              const status = (agent?.status ?? 'SLEEP') as Status
              return (
                <motion.tr
                  key={m.name}
                  initial={{ opacity: 0, x: -5 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="border-b border-border/40 hover:bg-border/10 transition-colors"
                >
                  <td className="py-2.5 pr-2">{statusIcon(status)}</td>
                  <td className="py-2.5">
                    <div className="font-mono text-text text-[11px]">{m.name}</div>
                    <div className="text-muted text-[10px] mt-0.5 max-w-60 truncate">{m.role}</div>
                  </td>
                  <td className="py-2.5">
                    <span className={statusBadge(status)}>{status}</span>
                  </td>
                  <td className="py-2.5 text-muted">
                    {agent?.last_run ? timeAgo(agent.last_run) + ' ago' : '—'}
                  </td>
                  <td className="py-2.5 text-right text-muted">{agent?.run_count ?? '—'}</td>
                  <td className="py-2.5 max-w-48">
                    <div className="text-muted truncate">{agent?.last_output ?? '—'}</div>
                  </td>
                </motion.tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

const GROUPS = ['Market Intelligence', 'Execution Intelligence', 'Risk & Learning', 'Supervisor'] as const

export function AgentMonitor() {
  const storeAgents = useStore((s) => s.agents)
  const [agents, setAgents] = useState<AgentStatus[]>(buildMockStatus())
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const data = await agentsApi.getAll()
      if (data.length > 0) setAgents(data)
    } catch {
      // use mock
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (storeAgents.length > 0) setAgents(storeAgents)
    else load()
  }, [storeAgents])

  const lastUpdate = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold flex items-center gap-2">
            <Activity size={18} className="text-info" />
            Agent Monitor
          </h1>
          <p className="text-xs text-muted">21 AI agents · last polled {lastUpdate}</p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-border text-xs text-muted hover:text-text transition-colors"
        >
          <RefreshCw size={12} className={clsx(loading && 'animate-spin')} />
          Refresh
        </button>
      </div>

      <StatusSummary agents={agents} />

      {GROUPS.map((g) => (
        <AgentTable key={g} agents={agents} group={g} />
      ))}
    </div>
  )
}
