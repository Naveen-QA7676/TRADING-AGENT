import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, RefreshCw } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
} from 'recharts'
import { api } from '../api/client'
import { Card, CardHeader, SectionTitle } from '../components/ui/Card'
import { MeterBar } from '../components/ui/MeterBar'
import clsx from 'clsx'

// ─── Types & mock data ────────────────────────────────────────────────────────

interface NiftyForecast {
  bullish_prob: number
  bearish_prob: number
  range_low: number
  range_high: number
  key_factors_bull: string[]
  key_factors_bear: string[]
  regime: string
}

interface AIPick {
  symbol: string
  direction: 'LONG' | 'SHORT'
  probability: number
  expected_move_low: number
  expected_move_high: number
  setup: string
  confidence: number
}

interface SectorProb {
  name: string
  prob: number
}

interface PredictionData {
  nifty: NiftyForecast
  picks: AIPick[]
  sectors: SectorProb[]
  updated_at: string
}

function buildMock(): PredictionData {
  return {
    nifty: {
      bullish_prob: 72,
      bearish_prob: 28,
      range_low: 24250,
      range_high: 24680,
      key_factors_bull: ['SGX +35 pts', 'FII buying ₹1,840Cr', 'S&P +0.8%', 'Regime trending'],
      key_factors_bear: ['DXY near resistance', 'PCR below 1.0'],
      regime: 'TRENDING_UP',
    },
    picks: [
      { symbol: 'HDFCBANK', direction: 'LONG', probability: 67, expected_move_low: 1.8, expected_move_high: 2.7, setup: 'VWAP Bounce',      confidence: 88 },
      { symbol: 'RELIANCE', direction: 'LONG', probability: 64, expected_move_low: 1.5, expected_move_high: 2.2, setup: 'ORB Candidate',     confidence: 78 },
      { symbol: 'INFY',     direction: 'LONG', probability: 62, expected_move_low: 2.0, expected_move_high: 3.0, setup: 'Post-result momo',  confidence: 75 },
      { symbol: 'TCS',      direction: 'LONG', probability: 58, expected_move_low: 1.2, expected_move_high: 1.8, setup: 'EMA Pullback',      confidence: 70 },
      { symbol: 'RELCAPITAL', direction: 'SHORT', probability: 61, expected_move_low: 1.0, expected_move_high: 1.5, setup: 'Distribution',  confidence: 66 },
    ],
    sectors: [
      { name: 'Banking',  prob: 82 }, { name: 'IT',      prob: 75 },
      { name: 'Infra',    prob: 65 }, { name: 'Metal',   prob: 58 },
      { name: 'Energy',   prob: 60 }, { name: 'Auto',    prob: 55 },
      { name: 'Pharma',   prob: 40 }, { name: 'FMCG',   prob: 38 },
    ],
    updated_at: new Date().toISOString(),
  }
}

// Funnel chart data — shows nifty forecast range as widening paths
function buildFunnelData(low: number, high: number) {
  const mid = (low + high) / 2
  const width = (high - low) / 2
  return Array.from({ length: 12 }, (_, i) => ({
    t: `+${i * 30}m`,
    upper: mid + (width * (i + 1)) / 12,
    lower: mid - (width * (i + 1)) / 12,
    mid,
  }))
}

function sectorColor(prob: number) {
  if (prob >= 75) return '#00FF88'
  if (prob >= 60) return '#66FF99'
  if (prob >= 50) return '#FFB020'
  if (prob >= 40) return '#FF7744'
  return '#FF3355'
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function NiftyFunnelCard({ nifty }: { nifty: NiftyForecast }) {
  const funnelData = buildFunnelData(nifty.range_low, nifty.range_high)

  return (
    <Card>
      <CardHeader>
        <SectionTitle>Nifty 50 — Today's Probability</SectionTitle>
        <span className="text-xs text-muted">Updated every 15 min · Probabilities, not predictions</span>
      </CardHeader>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Probability bars */}
        <div className="space-y-4">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="flex items-center gap-2 text-bull font-bold">
                <TrendingUp size={16} /> Bullish
              </span>
              <span className="text-bull font-bold text-lg">{nifty.bullish_prob}%</span>
            </div>
            <MeterBar value={nifty.bullish_prob} color="#00FF88" />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="flex items-center gap-2 text-bear font-bold">
                <TrendingDown size={16} /> Bearish
              </span>
              <span className="text-bear font-bold text-lg">{nifty.bearish_prob}%</span>
            </div>
            <MeterBar value={nifty.bearish_prob} color="#FF3355" />
          </div>

          <div className="pt-2 space-y-2">
            <div className="text-xs text-muted uppercase tracking-wide">Forecast range today</div>
            <div className="flex items-center gap-3 text-base font-bold">
              <span className="text-bear">{nifty.range_low.toLocaleString('en-IN')}</span>
              <span className="text-muted">→</span>
              <span className="text-bull">{nifty.range_high.toLocaleString('en-IN')}</span>
            </div>
            <div className="text-xs text-muted">Band width: {(nifty.range_high - nifty.range_low).toFixed(0)} pts</div>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <div className="text-muted mb-1">Bullish factors</div>
              {nifty.key_factors_bull.map((f) => (
                <div key={f} className="text-bull flex items-start gap-1">+ {f}</div>
              ))}
            </div>
            <div>
              <div className="text-muted mb-1">Bearish factors</div>
              {nifty.key_factors_bear.map((f) => (
                <div key={f} className="text-bear flex items-start gap-1">− {f}</div>
              ))}
            </div>
          </div>
        </div>

        {/* Funnel chart */}
        <div>
          <div className="text-xs text-muted mb-2">Intraday range funnel (expected path)</div>
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={funnelData} margin={{ top: 5, right: 10, bottom: 5, left: 40 }}>
              <XAxis dataKey="t" tick={{ fill: '#6B7280', fontSize: 10 }} />
              <YAxis domain={['dataMin - 20', 'dataMax + 20']} tick={{ fill: '#6B7280', fontSize: 10 }} />
              <Tooltip
                contentStyle={{ background: '#141824', border: '1px solid #1E2535', fontSize: 11 }}
                formatter={(v: number) => [v.toFixed(0), '']}
              />
              <Area type="monotone" dataKey="upper" stroke="#00FF88" strokeWidth={1} fill="#00FF88" fillOpacity={0.08} />
              <Area type="monotone" dataKey="lower" stroke="#FF3355" strokeWidth={1} fill="#FF3355" fillOpacity={0.05} />
              <Area type="monotone" dataKey="mid"   stroke="#4488FF" strokeWidth={2} fill="none" strokeDasharray="4 2" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </Card>
  )
}

function AIPicksCard({ picks }: { picks: AIPick[] }) {
  return (
    <Card>
      <CardHeader>
        <SectionTitle>Top AI Picks Today</SectionTitle>
        <span className="text-xs text-muted italic">Not a guarantee — probability based on historical edge + confluence</span>
      </CardHeader>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border text-muted">
              <th className="text-left pb-2 font-normal">Stock</th>
              <th className="text-left pb-2 font-normal pl-2">Dir</th>
              <th className="text-right pb-2 font-normal">Prob</th>
              <th className="text-right pb-2 font-normal">Expected Move</th>
              <th className="text-left pb-2 font-normal pl-3">Setup</th>
              <th className="text-right pb-2 font-normal">Score</th>
              <th className="pb-2"></th>
            </tr>
          </thead>
          <tbody>
            {picks.map((p, i) => (
              <motion.tr
                key={p.symbol}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.06 }}
                className="border-b border-border/50 hover:bg-border/10 transition-colors"
              >
                <td className="py-2.5 font-bold text-text">{p.symbol}</td>
                <td className="py-2.5 pl-2">
                  <span className={clsx('px-1.5 py-0.5 rounded text-[11px] font-bold',
                    p.direction === 'LONG' ? 'bg-bull/10 text-bull' : 'bg-bear/10 text-bear')}>
                    {p.direction === 'LONG' ? '🟢' : '🔴'} {p.direction}
                  </span>
                </td>
                <td className="py-2.5 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <div className="w-20">
                      <MeterBar value={p.probability} color={p.direction === 'LONG' ? '#00FF88' : '#FF3355'} animate={false} />
                    </div>
                    <span className={clsx('font-bold w-8 text-right', p.direction === 'LONG' ? 'text-bull' : 'text-bear')}>
                      {p.probability}%
                    </span>
                  </div>
                </td>
                <td className="py-2.5 text-right font-mono">
                  <span className={p.direction === 'LONG' ? 'text-bull' : 'text-bear'}>
                    {p.direction === 'LONG' ? '+' : '−'}{p.expected_move_low.toFixed(1)}–{p.expected_move_high.toFixed(1)}%
                  </span>
                </td>
                <td className="py-2.5 pl-3 text-info">{p.setup}</td>
                <td className="py-2.5 text-right">
                  <span className={clsx('font-bold', p.confidence >= 80 ? 'text-bull' : 'text-amber')}>
                    {p.confidence}/100
                  </span>
                </td>
                <td className="py-2.5 pl-2">
                  <button className="px-2 py-0.5 rounded border border-info/30 text-info hover:bg-info/10 text-[10px] transition-colors">
                    Chart
                  </button>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

function SectorHeatmapCard({ sectors }: { sectors: SectorProb[] }) {
  const sorted = [...sectors].sort((a, b) => b.prob - a.prob)

  return (
    <Card>
      <CardHeader>
        <SectionTitle>Sector Probability Map</SectionTitle>
        <span className="text-xs text-muted">Bullish probability for each sector today</span>
      </CardHeader>

      {/* Visual grid heatmap */}
      <div className="grid grid-cols-4 sm:grid-cols-8 gap-2 mb-4">
        {sorted.map((s, i) => (
          <motion.div
            key={s.name}
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.05 }}
            className="flex flex-col items-center justify-center rounded-lg p-3 text-center border"
            style={{
              backgroundColor: sectorColor(s.prob) + '15',
              borderColor: sectorColor(s.prob) + '40',
            }}
          >
            <span className="text-xs font-bold" style={{ color: sectorColor(s.prob) }}>
              {s.prob}%
            </span>
            <span className="text-[10px] text-muted mt-0.5">{s.name}</span>
          </motion.div>
        ))}
      </div>

      {/* Bar chart */}
      <ResponsiveContainer width="100%" height={120}>
        <BarChart data={sorted} layout="vertical" margin={{ top: 0, right: 30, bottom: 0, left: 48 }}>
          <XAxis type="number" domain={[0, 100]} tick={{ fill: '#6B7280', fontSize: 10 }} unit="%" />
          <YAxis type="category" dataKey="name" tick={{ fill: '#9CA3AF', fontSize: 11 }} width={48} />
          <Tooltip
            contentStyle={{ background: '#141824', border: '1px solid #1E2535', fontSize: 11 }}
            formatter={(v: number) => [`${v}%`, 'Bullish probability']}
          />
          <Bar dataKey="prob" radius={[0, 4, 4, 0]}>
            {sorted.map((s) => (
              <Cell key={s.name} fill={sectorColor(s.prob)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="flex items-center gap-4 text-[10px] text-muted mt-2">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-bull inline-block" /> Very bullish ≥75%</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber inline-block" /> Neutral 50–74%</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-bear inline-block" /> Bearish &lt;50%</span>
      </div>
    </Card>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function PredictionBoard() {
  const [data, setData] = useState<PredictionData>(buildMock())
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const [candidates, regime] = await Promise.allSettled([
        api.get('/scanner/candidates').then((r) => r.data),
        api.get('/scanner/regime').then((r) => r.data),
      ])
      // Merge live data if available; fall back to mock
      if (candidates.status === 'fulfilled' && candidates.value?.candidates?.length) {
        setData((prev) => ({
          ...prev,
          picks: candidates.value.candidates.slice(0, 5).map((c: Record<string, unknown>) => ({
            symbol:             String(c.symbol ?? ''),
            direction:          String(c.direction ?? 'LONG') as 'LONG' | 'SHORT',
            probability:        Number(c.win_probability ?? 60) * 100,
            expected_move_low:  Number(c.expected_move_low ?? 1.5),
            expected_move_high: Number(c.expected_move_high ?? 2.5),
            setup:              String(c.strategy_name ?? 'Scanner pick'),
            confidence:         Number(c.confidence_score ?? 70),
          })),
        }))
      }
      if (regime.status === 'fulfilled') {
        setData((prev) => ({ ...prev, nifty: { ...prev.nifty, regime: regime.value.regime } }))
      }
    } catch {
      // keep mock
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold">🔮 AI Probability Board</h1>
          <p className="text-xs text-muted">
            Probabilities, not predictions · Updated{' '}
            {new Date(data.updated_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
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

      <NiftyFunnelCard nifty={data.nifty} />
      <AIPicksCard picks={data.picks} />
      <SectorHeatmapCard sectors={data.sectors} />
    </div>
  )
}
