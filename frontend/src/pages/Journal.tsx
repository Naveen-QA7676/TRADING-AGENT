import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, Cell,
} from 'recharts'
import { TrendingUp, Award, AlertCircle } from 'lucide-react'
import { journalApi, JournalTrade, PerformanceStats } from '../api/journal'
import { Card, CardHeader, SectionTitle } from '../components/ui/Card'
import { MeterBar } from '../components/ui/MeterBar'
import clsx from 'clsx'

// ─── Mock data ────────────────────────────────────────────────────────────────

const MOCK_STATS: PerformanceStats = {
  total_trades: 47,
  win_rate:     0.638,
  avg_win:      2.14,
  avg_loss:     0.97,
  profit_factor: 3.52,
  expectancy:   0.84,
  max_drawdown: -4.8,
  sharpe:       1.72,
  equity_curve: [
    { date: 'Apr 1',  equity: 100000 },
    { date: 'Apr 8',  equity: 102400 },
    { date: 'Apr 15', equity: 101100 },
    { date: 'Apr 22', equity: 104500 },
    { date: 'May 1',  equity: 107200 },
    { date: 'May 8',  equity: 105800 },
    { date: 'May 15', equity: 110100 },
    { date: 'May 22', equity: 113400 },
    { date: 'Jun 1',  equity: 116200 },
    { date: 'Jun 8',  equity: 118900 },
    { date: 'Jun 15', equity: 121500 },
    { date: 'Jun 22', equity: 124700 },
  ],
  r_distribution: [
    { bucket: '< -3R', count: 1 },
    { bucket: '-3R',   count: 2 },
    { bucket: '-2R',   count: 4 },
    { bucket: '-1R',   count: 11 },
    { bucket: '0',     count: 2 },
    { bucket: '+1R',   count: 13 },
    { bucket: '+2R',   count: 8 },
    { bucket: '+3R',   count: 4 },
    { bucket: '+4R+',  count: 2 },
  ],
  by_setup: [
    { setup: 'VWAP Bounce',      trades: 14, win_rate: 0.71, avg_r: 1.4 },
    { setup: 'ORB Breakout',     trades: 11, win_rate: 0.64, avg_r: 1.2 },
    { setup: 'EMA Pullback',     trades: 9,  win_rate: 0.67, avg_r: 0.9 },
    { setup: 'Pre-mkt Momentum', trades: 7,  win_rate: 0.57, avg_r: 0.8 },
    { setup: 'Gap Fill',         trades: 6,  win_rate: 0.50, avg_r: 0.7 },
  ],
  by_hour: [
    { hour: '9:15', win_rate: 0.52, trades: 8 },
    { hour: '9:30', win_rate: 0.69, trades: 11 },
    { hour: '10:00',win_rate: 0.75, trades: 8 },
    { hour: '11:00',win_rate: 0.65, trades: 7 },
    { hour: '12:00',win_rate: 0.50, trades: 4 },
    { hour: '13:00',win_rate: 0.44, trades: 5 },
    { hour: '14:00',win_rate: 0.58, trades: 4 },
  ],
}

const MOCK_TRADES: JournalTrade[] = [
  { id: 1, symbol: 'HDFCBANK', direction: 'LONG', entry: 1645.20, exit: 1671.45, qty: 60,  pnl: 1575,  r_multiple: 2.1, setup: 'VWAP Bounce',  date: '2026-06-27', duration: '38m', tags: ['clean setup'], mistake: null },
  { id: 2, symbol: 'INFY',     direction: 'LONG', entry: 1528.00, exit: 1518.50, qty: 65,  pnl: -617,  r_multiple: -1.0, setup: 'ORB',       date: '2026-06-27', duration: '22m', tags: [], mistake: 'Chased after breakout already ran 0.5%' },
  { id: 3, symbol: 'RELIANCE', direction: 'LONG', entry: 2940.00, exit: 2968.80, qty: 34,  pnl: 979,   r_multiple: 1.4, setup: 'EMA Pullback', date: '2026-06-26', duration: '55m', tags: [], mistake: null },
  { id: 4, symbol: 'BAJFINANCE', direction: 'SHORT', entry: 6820.00, exit: 6748.00, qty: 14, pnl: 1008, r_multiple: 1.8, setup: 'Distribution', date: '2026-06-26', duration: '1h 14m', tags: ['high conviction'], mistake: null },
  { id: 5, symbol: 'TCS',     direction: 'LONG', entry: 3740.00, exit: 3752.50, qty: 26,  pnl: 325,   r_multiple: 0.6, setup: 'Pre-mkt momo', date: '2026-06-25', duration: '18m', tags: ['early exit'], mistake: 'Exited at +0.3% instead of T1 at +0.8%' },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function statColor(v: number) { return v >= 0 ? '#00FF88' : '#FF3355' }

function WinRateRing({ rate }: { rate: number }) {
  const pct = Math.round(rate * 100)
  const color = pct >= 60 ? '#00FF88' : pct >= 50 ? '#FFB020' : '#FF3355'
  const r = 36, circ = 2 * Math.PI * r
  const offset = circ * (1 - pct / 100)
  return (
    <svg width={88} height={88}>
      <circle cx={44} cy={44} r={r} fill="none" stroke="#1E2535" strokeWidth={8} />
      <motion.circle
        cx={44} cy={44} r={r} fill="none"
        stroke={color} strokeWidth={8}
        strokeLinecap="round"
        strokeDasharray={circ}
        initial={{ strokeDashoffset: circ }}
        animate={{ strokeDashoffset: offset }}
        transition={{ duration: 1.2, ease: 'easeOut' }}
        style={{ transform: 'rotate(-90deg)', transformOrigin: '44px 44px' }}
      />
      <text x={44} y={44} textAnchor="middle" dominantBaseline="central" fill={color} fontSize={16} fontWeight={700}>
        {pct}%
      </text>
    </svg>
  )
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatsBar({ stats }: { stats: PerformanceStats }) {
  const items = [
    { label: 'Trades',        value: stats.total_trades, fmt: String(stats.total_trades) },
    { label: 'Profit Factor', value: stats.profit_factor, fmt: stats.profit_factor.toFixed(2) + 'x' },
    { label: 'Expectancy',    value: stats.expectancy,    fmt: stats.expectancy.toFixed(2) + 'R' },
    { label: 'Max DD',        value: stats.max_drawdown,  fmt: stats.max_drawdown.toFixed(1) + '%' },
    { label: 'Sharpe',        value: stats.sharpe,        fmt: stats.sharpe.toFixed(2) },
    { label: 'Avg Win',       value: stats.avg_win,       fmt: '+' + stats.avg_win.toFixed(2) + '%' },
    { label: 'Avg Loss',      value: -stats.avg_loss,     fmt: '−' + stats.avg_loss.toFixed(2) + '%' },
  ]
  return (
    <div className="grid grid-cols-4 sm:grid-cols-7 gap-3">
      {items.map((it) => (
        <div key={it.label} className="text-center bg-card rounded-lg p-2 border border-border">
          <div className="text-xs text-muted mb-0.5">{it.label}</div>
          <div className="text-sm font-bold" style={{ color: statColor(it.value) }}>{it.fmt}</div>
        </div>
      ))}
    </div>
  )
}

function EquityCurve({ data }: { data: { date: string; equity: number }[] }) {
  const startEquity = data[0]?.equity ?? 100000
  const endEquity   = data[data.length - 1]?.equity ?? 100000
  const pct         = ((endEquity - startEquity) / startEquity * 100).toFixed(1)

  return (
    <Card>
      <CardHeader>
        <SectionTitle>Equity Curve</SectionTitle>
        <span className="text-bull font-bold">+{pct}% this period</span>
      </CardHeader>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 50 }}>
          <XAxis dataKey="date" tick={{ fill: '#6B7280', fontSize: 10 }} />
          <YAxis
            tickFormatter={(v: number) => '₹' + (v / 1000).toFixed(0) + 'K'}
            tick={{ fill: '#6B7280', fontSize: 10 }}
          />
          <Tooltip
            contentStyle={{ background: '#141824', border: '1px solid #1E2535', fontSize: 11 }}
            formatter={(v: number) => ['₹' + v.toLocaleString('en-IN'), 'Equity']}
          />
          <Line
            type="monotone" dataKey="equity"
            stroke="#00FF88" strokeWidth={2} dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  )
}

function RDistribution({ data }: { data: { bucket: string; count: number }[] }) {
  return (
    <Card>
      <CardHeader>
        <SectionTitle>R Distribution</SectionTitle>
        <span className="text-xs text-muted">Trade outcomes by R-multiple</span>
      </CardHeader>
      <ResponsiveContainer width="100%" height={130}>
        <BarChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
          <XAxis dataKey="bucket" tick={{ fill: '#6B7280', fontSize: 10 }} />
          <YAxis tick={{ fill: '#6B7280', fontSize: 10 }} allowDecimals={false} />
          <Tooltip
            contentStyle={{ background: '#141824', border: '1px solid #1E2535', fontSize: 11 }}
            formatter={(v: number) => [v, 'Trades']}
          />
          <ReferenceLine x="0" stroke="#1E2535" strokeWidth={2} />
          <Bar dataKey="count" radius={[3, 3, 0, 0]}>
            {data.map((d) => (
              <Cell key={d.bucket} fill={d.bucket.startsWith('-') || d.bucket === '< -3R' ? '#FF3355' : '#00FF88'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  )
}

function SetupBreakdown({ data }: { data: PerformanceStats['by_setup'] }) {
  return (
    <Card>
      <CardHeader>
        <SectionTitle>Win Rate by Setup</SectionTitle>
      </CardHeader>
      <div className="space-y-3">
        {data.map((s) => (
          <div key={s.setup}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-text">{s.setup}</span>
              <span className="text-muted">{s.trades} trades · avg {s.avg_r.toFixed(1)}R</span>
            </div>
            <MeterBar value={s.win_rate * 100} color={s.win_rate >= 0.6 ? '#00FF88' : '#FFB020'} />
            <div className="text-right text-xs mt-0.5" style={{ color: s.win_rate >= 0.6 ? '#00FF88' : '#FFB020' }}>
              {(s.win_rate * 100).toFixed(0)}%
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

function TimeHeatmap({ data }: { data: PerformanceStats['by_hour'] }) {
  const maxTrades = Math.max(...data.map((d) => d.trades))
  return (
    <Card>
      <CardHeader>
        <SectionTitle>Best Trading Hours</SectionTitle>
      </CardHeader>
      <div className="flex gap-2 items-end">
        {data.map((h) => {
          const ht = Math.round((h.trades / maxTrades) * 80)
          const color = h.win_rate >= 0.65 ? '#00FF88' : h.win_rate >= 0.5 ? '#FFB020' : '#FF3355'
          return (
            <div key={h.hour} className="flex-1 flex flex-col items-center gap-1">
              <motion.div
                initial={{ height: 0 }} animate={{ height: ht }}
                transition={{ duration: 0.8 }}
                className="w-full rounded-t-sm"
                style={{ backgroundColor: color + '80', minHeight: 4 }}
              />
              <div className="text-[10px] text-muted">{h.hour}</div>
              <div className="text-[10px] font-bold" style={{ color }}>{(h.win_rate * 100).toFixed(0)}%</div>
            </div>
          )
        })}
      </div>
      <div className="text-xs text-muted mt-2">Bar height = # trades. Color = win rate at that hour.</div>
    </Card>
  )
}

function TradeLog({ trades }: { trades: JournalTrade[] }) {
  return (
    <Card>
      <CardHeader>
        <SectionTitle>Trade Log</SectionTitle>
        <span className="text-xs text-muted">{trades.length} trades</span>
      </CardHeader>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border text-muted text-left">
              <th className="pb-2 font-normal">Date</th>
              <th className="pb-2 font-normal">Symbol</th>
              <th className="pb-2 font-normal">Dir</th>
              <th className="pb-2 font-normal text-right">Entry</th>
              <th className="pb-2 font-normal text-right">Exit</th>
              <th className="pb-2 font-normal text-right">P&L</th>
              <th className="pb-2 font-normal text-right">R</th>
              <th className="pb-2 font-normal">Setup</th>
              <th className="pb-2 font-normal">Dur</th>
              <th className="pb-2 font-normal">Notes</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t, i) => (
              <motion.tr
                key={t.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.05 }}
                className="border-b border-border/40 hover:bg-border/10 transition-colors"
              >
                <td className="py-2 text-muted">{t.date}</td>
                <td className="py-2 font-bold text-text">{t.symbol}</td>
                <td className="py-2">
                  <span className={clsx('px-1 py-0.5 rounded text-[10px] font-bold',
                    t.direction === 'LONG' ? 'text-bull' : 'text-bear')}>
                    {t.direction}
                  </span>
                </td>
                <td className="py-2 text-right font-mono">{t.entry.toFixed(2)}</td>
                <td className="py-2 text-right font-mono">{t.exit?.toFixed(2) ?? '—'}</td>
                <td className={clsx('py-2 text-right font-mono font-bold', t.pnl >= 0 ? 'text-bull' : 'text-bear')}>
                  {t.pnl >= 0 ? '+' : ''}₹{t.pnl.toLocaleString('en-IN')}
                </td>
                <td className={clsx('py-2 text-right font-bold', t.r_multiple >= 0 ? 'text-bull' : 'text-bear')}>
                  {t.r_multiple > 0 ? '+' : ''}{t.r_multiple.toFixed(1)}R
                </td>
                <td className="py-2 text-info">{t.setup}</td>
                <td className="py-2 text-muted">{t.duration ?? '—'}</td>
                <td className="py-2 max-w-40">
                  {t.mistake ? (
                    <span className="text-amber flex items-start gap-1">
                      <AlertCircle size={10} className="shrink-0 mt-0.5" />{t.mistake}
                    </span>
                  ) : t.tags.length > 0 ? (
                    <span className="text-muted">{t.tags.join(', ')}</span>
                  ) : null}
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

function MistakeAnalysis({ trades }: { trades: JournalTrade[] }) {
  const mistakes = trades.filter((t) => t.mistake)
  if (mistakes.length === 0) return null
  return (
    <Card>
      <CardHeader>
        <SectionTitle>
          <AlertCircle size={14} className="inline mr-1 mb-0.5 text-amber" />
          Mistake Analysis
        </SectionTitle>
        <span className="text-amber text-xs">{mistakes.length} trade{mistakes.length > 1 ? 's' : ''} with noted mistakes</span>
      </CardHeader>
      <div className="space-y-2">
        {mistakes.map((t) => (
          <div key={t.id} className="flex items-start gap-3 p-2 rounded bg-amber/5 border border-amber/20">
            <div className="text-amber shrink-0">
              <AlertCircle size={14} />
            </div>
            <div>
              <div className="text-xs font-bold text-text">{t.symbol} ({t.date}) — {t.setup}</div>
              <div className="text-xs text-amber mt-0.5">{t.mistake}</div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function Journal() {
  const [stats, setStats] = useState<PerformanceStats>(MOCK_STATS)
  const [trades, setTrades] = useState<JournalTrade[]>(MOCK_TRADES)

  useEffect(() => {
    Promise.allSettled([journalApi.getStats(), journalApi.getTrades()]).then(([s, t]) => {
      if (s.status === 'fulfilled' && s.value) setStats(s.value)
      if (t.status === 'fulfilled' && t.value?.length) setTrades(t.value)
    })
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-lg font-bold flex items-center gap-2">
            <Award size={18} className="text-amber" /> Trading Journal
          </h1>
          <p className="text-xs text-muted">Performance analytics & trade log · FY 2025-26</p>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-2 justify-end">
            <WinRateRing rate={stats.win_rate} />
            <div className="text-xs text-muted">Win Rate</div>
          </div>
        </div>
      </div>

      <StatsBar stats={stats} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <EquityCurve data={stats.equity_curve} />
        <RDistribution data={stats.r_distribution} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SetupBreakdown data={stats.by_setup} />
        <div className="space-y-4">
          <TimeHeatmap data={stats.by_hour} />
          <Card>
            <CardHeader><SectionTitle>Performance Edge</SectionTitle></CardHeader>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="space-y-1">
                <div className="text-muted">Best setup</div>
                <div className="text-bull font-bold">VWAP Bounce <span className="text-muted font-normal">71% WR</span></div>
              </div>
              <div className="space-y-1">
                <div className="text-muted">Best hour</div>
                <div className="text-bull font-bold">10:00–11:00 <span className="text-muted font-normal">75% WR</span></div>
              </div>
              <div className="space-y-1">
                <div className="text-muted">Avg hold time</div>
                <div className="text-text font-bold">44 min</div>
              </div>
              <div className="space-y-1">
                <div className="text-muted">W:L ratio</div>
                <div className="text-bull font-bold flex items-center gap-1">
                  <TrendingUp size={12} /> {(stats.avg_win / stats.avg_loss).toFixed(2)}:1
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>

      <TradeLog trades={trades} />
      <MistakeAnalysis trades={trades} />
    </div>
  )
}
