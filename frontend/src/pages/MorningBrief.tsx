import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Bell, RefreshCw } from 'lucide-react'
import { Card, CardHeader, SectionTitle } from '../components/ui/Card'
import { MeterBar } from '../components/ui/MeterBar'
import { useStore } from '../store/useStore'
import { api } from '../api/client'
import clsx from 'clsx'

// ─── Types ────────────────────────────────────────────────────────────────────

interface GlobalTicker {
  label: string
  value: string
  change: number   // percent
  status: 'good' | 'watch' | 'bad' | 'neutral'
}

interface WatchlistItem {
  rank: number
  symbol: string
  score: number
  setup: string
  ltp: number
  change: number
  key_level: number
}

interface MorningData {
  global: GlobalTicker[]
  fii_net: number
  dii_net: number
  expected_gap: number
  india_vix: number
  regime: string
  adx: number
  strategy_today: string
  avoid_sectors: string[]
  watchlist: WatchlistItem[]
}

// ─── Mock data (replaces API until backend morning endpoint exists) ─────────

function buildMockData(): MorningData {
  return {
    global: [
      { label: 'S&P 500',   value: '5,478',  change: +0.82, status: 'good'    },
      { label: 'NASDAQ',    value: '17,690', change: +1.12, status: 'good'    },
      { label: 'Dow',       value: '39,120', change: +0.51, status: 'good'    },
      { label: 'VIX',       value: '16.2',   change: -1.40, status: 'good'    },
      { label: 'DXY',       value: '104.3',  change: +0.05, status: 'neutral' },
      { label: 'Crude',     value: '$78.4',  change: +0.38, status: 'watch'   },
      { label: 'Gold',      value: '$2340',  change: -0.12, status: 'neutral' },
      { label: 'Nikkei',    value: '38,720', change: +0.41, status: 'good'    },
      { label: 'Hang Seng', value: '18,240', change: +0.22, status: 'neutral' },
      { label: 'SGX Nifty', value: '+35 pts', change: +0.14, status: 'good'  },
      { label: 'BTC',       value: '$62,400', change: +1.80, status: 'neutral'},
      { label: 'US 10Y',    value: '4.32%',  change: +0.02, status: 'neutral' },
    ],
    fii_net: 1840,
    dii_net: 620,
    expected_gap: 90,
    india_vix: 14.2,
    regime: 'TRENDING_UP',
    adx: 28,
    strategy_today: 'Pullback setups, Breakouts — NO counter-trend trades',
    avoid_sectors: ['FMCG', 'Pharma'],
    watchlist: [
      { rank: 1, symbol: 'HDFCBANK', score: 82, setup: 'VWAP Bounce',      ltp: 1648.40, change: +0.42, key_level: 1645 },
      { rank: 2, symbol: 'RELIANCE', score: 78, setup: 'ORB Candidate',     ltp: 2934.60, change: +0.65, key_level: 2920 },
      { rank: 3, symbol: 'INFY',     score: 75, setup: 'Post-result momo',  ltp: 1842.10, change: +1.24, key_level: 1830 },
      { rank: 4, symbol: 'TCS',      score: 70, setup: 'EMA Pullback',      ltp: 3824.55, change: -0.18, key_level: 3800 },
      { rank: 5, symbol: 'ICICIBANK',score: 68, setup: 'PDH Breakout',      ltp: 1198.30, change: +0.31, key_level: 1195 },
    ],
  }
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function GlobalTickerCard({ ticker }: { ticker: GlobalTicker }) {
  const pos = ticker.change >= 0
  const statusColors: Record<string, string> = {
    good:    'text-bull',
    watch:   'text-amber',
    bad:     'text-bear',
    neutral: 'text-muted',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-card border border-border rounded-lg px-3 py-2 min-w-[90px] flex flex-col gap-0.5"
    >
      <span className="text-[10px] text-muted uppercase tracking-wide">{ticker.label}</span>
      <span className="text-sm font-bold text-text">{ticker.value}</span>
      <span className={clsx('text-xs font-semibold', pos ? 'text-bull' : 'text-bear')}>
        {pos ? '+' : ''}{ticker.change.toFixed(2)}%
      </span>
      <span className={clsx('text-[10px] font-bold uppercase', statusColors[ticker.status])}>
        {ticker.status === 'good' ? '●' : ticker.status === 'bad' ? '●' : '◐'} {ticker.status}
      </span>
    </motion.div>
  )
}

function RegimeBadge({ regime }: { regime: string }) {
  const cfg: Record<string, { label: string; color: string; bg: string }> = {
    TRENDING_UP:   { label: 'TRENDING UP',   color: '#00FF88', bg: 'rgba(0,255,136,0.08)' },
    TRENDING_DOWN: { label: 'TRENDING DOWN', color: '#FF3355', bg: 'rgba(255,51,85,0.08)'  },
    RANGE_BOUND:   { label: 'RANGE BOUND',   color: '#FFB020', bg: 'rgba(255,176,32,0.08)' },
    VOLATILE:      { label: 'VOLATILE',      color: '#FFB020', bg: 'rgba(255,176,32,0.08)' },
    COMPRESSING:   { label: 'COMPRESSING',   color: '#6B7280', bg: 'rgba(107,114,128,0.08)'},
    UNKNOWN:       { label: 'UNKNOWN',       color: '#6B7280', bg: 'rgba(107,114,128,0.08)'},
  }
  const c = cfg[regime] ?? cfg.UNKNOWN
  return (
    <motion.div
      animate={{ opacity: [1, 0.7, 1] }}
      transition={{ duration: 2, repeat: Infinity }}
      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border text-lg font-bold"
      style={{ color: c.color, background: c.bg, borderColor: c.color + '40' }}
    >
      <span className="text-xl">🟢</span>
      {c.label}
    </motion.div>
  )
}

function Sparkline({ change }: { change: number }) {
  const color = change >= 0 ? '#00FF88' : '#FF3355'
  const pts = change >= 0
    ? '0,20 10,15 20,18 30,10 40,12 50,5'
    : '0,5 10,8 20,12 30,10 40,15 50,20'
  return (
    <svg width={50} height={20}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} />
    </svg>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export function MorningBrief() {
  useStore()
  const [data, setData] = useState<MorningData | null>(null)
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    try {
      const res = await api.get<MorningData>('/scanner/morning-brief').then((r) => r.data)
      setData(res)
    } catch {
      // Fallback to mock while endpoint isn't live
      setData(buildMockData())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const d = data ?? buildMockData()

  return (
    <div className="space-y-4 max-w-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-text">Morning Intelligence Brief</h1>
          <p className="text-xs text-muted">
            {new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
            {' · '}Pre-market analysis
          </p>
        </div>
        <button
          onClick={load}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-border text-xs text-muted hover:text-text hover:border-info/40 transition-colors"
        >
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Section A: Global Market Board */}
      <Card>
        <CardHeader>
          <SectionTitle>Global Market Board</SectionTitle>
          <span className="text-[10px] text-muted">Pre-market snapshot</span>
        </CardHeader>
        <div className="flex flex-wrap gap-2">
          {d.global.map((t) => (
            <GlobalTickerCard key={t.label} ticker={t} />
          ))}
        </div>
      </Card>

      {/* Section B: India Overview */}
      <Card>
        <CardHeader>
          <SectionTitle>India Overview</SectionTitle>
          <span className="text-[10px] text-muted live-pulse text-bull">● LIVE</span>
        </CardHeader>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {/* FII/DII */}
          <div className="space-y-2">
            <div className="text-[10px] text-muted uppercase tracking-wide">FII Flow</div>
            <div className={clsx('text-base font-bold', d.fii_net >= 0 ? 'text-bull' : 'text-bear')}>
              ₹{Math.abs(d.fii_net).toLocaleString('en-IN')}Cr
            </div>
            <div className={clsx('text-xs font-semibold', d.fii_net >= 0 ? 'text-bull' : 'text-bear')}>
              {d.fii_net >= 0 ? '▲ BUY' : '▼ SELL'}
            </div>
            <MeterBar value={Math.min(100, Math.abs(d.fii_net) / 30)} color={d.fii_net >= 0 ? '#00FF88' : '#FF3355'} />
          </div>

          <div className="space-y-2">
            <div className="text-[10px] text-muted uppercase tracking-wide">DII Flow</div>
            <div className={clsx('text-base font-bold', d.dii_net >= 0 ? 'text-bull' : 'text-bear')}>
              ₹{Math.abs(d.dii_net).toLocaleString('en-IN')}Cr
            </div>
            <div className={clsx('text-xs font-semibold', d.dii_net >= 0 ? 'text-bull' : 'text-bear')}>
              {d.dii_net >= 0 ? '▲ BUY' : '▼ SELL'}
            </div>
            <MeterBar value={Math.min(100, Math.abs(d.dii_net) / 30)} color={d.dii_net >= 0 ? '#00FF88' : '#FF3355'} />
          </div>

          {/* Expected Gap */}
          <div className="space-y-2">
            <div className="text-[10px] text-muted uppercase tracking-wide">Expected Gap</div>
            <div className={clsx('text-base font-bold', d.expected_gap >= 0 ? 'text-bull' : 'text-bear')}>
              {d.expected_gap >= 0 ? '+' : ''}{d.expected_gap} pts
            </div>
            <div className={clsx('text-xs', d.expected_gap >= 0 ? 'text-bull' : 'text-bear')}>
              {d.expected_gap >= 0 ? 'Gap Up' : 'Gap Down'}
            </div>
          </div>

          {/* India VIX */}
          <div className="space-y-2">
            <div className="text-[10px] text-muted uppercase tracking-wide">India VIX</div>
            <div className={clsx('text-base font-bold', d.india_vix < 15 ? 'text-bull' : d.india_vix < 20 ? 'text-amber' : 'text-bear')}>
              {d.india_vix.toFixed(1)}
            </div>
            <div className={clsx('text-xs font-bold px-2 py-0.5 rounded inline-block',
              d.india_vix < 15 ? 'bg-bull/10 text-bull' : d.india_vix < 20 ? 'bg-amber/10 text-amber' : 'bg-bear/10 text-bear'
            )}>
              {d.india_vix < 15 ? 'LOW — CALM' : d.india_vix < 20 ? 'MEDIUM' : 'HIGH — CAUTION'}
            </div>
          </div>
        </div>
      </Card>

      {/* Section C: Regime + Strategy */}
      <Card>
        <CardHeader>
          <SectionTitle>Today's Regime &amp; Strategy</SectionTitle>
          <span className="text-xs text-muted">ADX {d.adx}</span>
        </CardHeader>
        <div className="flex flex-col sm:flex-row gap-6 items-start">
          <div className="shrink-0">
            <RegimeBadge regime={d.regime} />
            <p className="text-xs text-muted mt-2">Structure: HH/HL intact · ADX {d.adx}</p>
          </div>
          <div className="flex-1 space-y-3">
            <div>
              <div className="text-[10px] text-muted uppercase tracking-wide mb-1">Strategy Today</div>
              <p className="text-sm text-bull font-semibold">{d.strategy_today}</p>
            </div>
            {d.avoid_sectors.length > 0 && (
              <div>
                <div className="text-[10px] text-muted uppercase tracking-wide mb-1">Avoid Today</div>
                <div className="flex gap-2 flex-wrap">
                  {d.avoid_sectors.map((s) => (
                    <span key={s} className="px-2 py-0.5 rounded text-xs bg-bear/10 text-bear border border-bear/20">
                      ✗ {s}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Section D: Watchlist */}
      <Card>
        <CardHeader>
          <SectionTitle>Today's Watchlist — AI Ranked</SectionTitle>
          <span className="text-[10px] text-muted">Updated at market open</span>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-muted border-b border-border">
                <th className="text-left pb-2 font-normal">#</th>
                <th className="text-left pb-2 font-normal">Stock</th>
                <th className="text-right pb-2 font-normal">Score</th>
                <th className="text-left pb-2 font-normal pl-3">Setup</th>
                <th className="text-right pb-2 font-normal">LTP</th>
                <th className="text-right pb-2 font-normal">Chg%</th>
                <th className="text-right pb-2 font-normal">Key Level</th>
                <th className="text-right pb-2 font-normal pl-3">Chart</th>
                <th className="pb-2"></th>
              </tr>
            </thead>
            <tbody>
              {d.watchlist.map((item, i) => (
                <motion.tr
                  key={item.symbol}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.07 }}
                  className="border-b border-border/50 hover:bg-border/20 transition-colors"
                >
                  <td className="py-2.5 text-muted">#{item.rank}</td>
                  <td className="py-2.5 font-bold text-text">{item.symbol}</td>
                  <td className="py-2.5 text-right">
                    <span
                      className={clsx('font-bold', item.score >= 80 ? 'text-bull' : item.score >= 65 ? 'text-amber' : 'text-bear')}
                    >
                      {item.score}/100
                    </span>
                  </td>
                  <td className="py-2.5 pl-3 text-info">{item.setup}</td>
                  <td className="py-2.5 text-right font-mono font-semibold text-text">₹{item.ltp.toFixed(2)}</td>
                  <td className={clsx('py-2.5 text-right font-semibold', item.change >= 0 ? 'text-bull' : 'text-bear')}>
                    {item.change >= 0 ? '+' : ''}{item.change.toFixed(2)}%
                  </td>
                  <td className="py-2.5 text-right text-muted">₹{item.key_level}</td>
                  <td className="py-2.5 pl-3">
                    <Sparkline change={item.change} />
                  </td>
                  <td className="py-2.5 pl-2">
                    <button className="flex items-center gap-1 px-2 py-1 rounded border border-info/30 text-info hover:bg-info/10 transition-colors text-[10px]">
                      <Bell size={10} /> Alert
                    </button>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
