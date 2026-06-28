import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Star, TrendingUp, TrendingDown, BarChart2, Bot } from 'lucide-react'
import {
  createChart, ColorType, CrosshairMode,
  type IChartApi, type CandlestickData,
} from 'lightweight-charts'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, Cell,
} from 'recharts'
import { stocksApi, type StockQuote, type TechnicalSnapshot, type Fundamentals } from '../api/stocks'
import { Card, CardHeader, SectionTitle } from '../components/ui/Card'
import { MeterBar } from '../components/ui/MeterBar'
import { ScoreBadge } from '../components/ui/ScoreBadge'
import { AnimatedNumber } from '../components/ui/AnimatedNumber'
import clsx from 'clsx'

// ─── Mock data helpers ────────────────────────────────────────────────────────

function mockQuote(symbol: string): StockQuote {
  const ltps: Record<string, number> = { HDFCBANK: 1648, RELIANCE: 2934, INFY: 1842, TCS: 3824, NIFTY50: 24460 }
  const ltp = ltps[symbol] ?? 1000
  return {
    symbol, ltp, open: ltp * 0.993, high: ltp * 1.008, low: ltp * 0.987,
    close: ltp * 0.999, volume: 1_240_000, change_pct: +0.42,
  }
}

function mockFundamentals(symbol: string): Fundamentals {
  return {
    symbol,
    grade: 'A',
    data: {
      pe: 18.4, eps: 89.5, roe: 16.2, roce: 13.8, de_ratio: 0.12,
      promoter_holding: 26.1, market_cap: '12.4L Cr',
      revenue_growth_yoy: 18.3, pat_growth_yoy: 22.1,
      '52w_high': 1794.5, '52w_low': 1363.2,
    },
  }
}

function mockTechnical(symbol: string): TechnicalSnapshot {
  return {
    symbol,
    timeframes: {
      '5m':    { bull_score: 72, buy_count: 8, sell_count: 2, neutral_count: 1, rsi: 54, macd_signal: 'BUY', vwap: 1647 },
      '15m':   { bull_score: 76, buy_count: 9, sell_count: 1, neutral_count: 1, rsi: 52, macd_signal: 'BUY', vwap: 1646 },
      '1h':    { bull_score: 68, buy_count: 7, sell_count: 2, neutral_count: 2, rsi: 55, macd_signal: 'BUY', vwap: 1643 },
      'daily': { bull_score: 62, buy_count: 6, sell_count: 3, neutral_count: 2, rsi: 61, macd_signal: 'NEUTRAL', vwap: null },
    },
  }
}

function mockMonthlyReturns() {
  return ['Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr','May','Jun'].map((m) => ({
    month: m,
    return: (Math.random() - 0.35) * 8,
  }))
}

function buildMockCandles(center: number, count = 200) {
  let price = center * 0.94
  const now = Math.floor(Date.now() / 1000)
  return Array.from({ length: count }, (_, i) => {
    const o = price
    const c = o + (Math.random() - 0.47) * center * 0.003
    const h = Math.max(o, c) + Math.random() * center * 0.002
    const l = Math.min(o, c) - Math.random() * center * 0.002
    price = c
    return { time: now - (count - i) * 900, open: +o.toFixed(2), high: +h.toFixed(2), low: +l.toFixed(2), close: +c.toFixed(2) }
  })
}

// ─── Tab: Overview ────────────────────────────────────────────────────────────

function TabOverview({ quote, fundamentals }: { quote: StockQuote; fundamentals: Fundamentals | null }) {
  const fund = fundamentals?.data ?? {}
  const grade = fundamentals?.grade ?? 'A'
  const ltp = quote.ltp
  const high52 = (fund['52w_high'] as number) ?? ltp * 1.09
  const low52  = (fund['52w_low']  as number) ?? ltp * 0.83
  const rangePct = ((ltp - low52) / (high52 - low52)) * 100

  const gradeColor: Record<string, string> = { 'A+': '#00FF88', A: '#00FF88', B: '#FFB020', C: '#FF3355' }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Price card */}
      <Card>
        <CardHeader><SectionTitle>Live Price</SectionTitle></CardHeader>
        <div className="space-y-3">
          <div className="flex items-baseline gap-3">
            <span className="text-3xl font-bold text-text">₹{ltp.toFixed(2)}</span>
            <span className={clsx('text-sm font-bold', quote.change_pct >= 0 ? 'text-bull' : 'text-bear')}>
              {quote.change_pct >= 0 ? '+' : ''}{quote.change_pct.toFixed(2)}%
            </span>
          </div>
          <div className="grid grid-cols-4 gap-2 text-xs">
            {[['Open', quote.open],['High', quote.high],['Low', quote.low],['Prev', quote.close]].map(([l, v]) => (
              <div key={l as string}><div className="text-muted">{l}</div><div className="font-semibold text-text">₹{(v as number).toFixed(2)}</div></div>
            ))}
          </div>
          <div>
            <div className="flex justify-between text-[10px] text-muted mb-1">
              <span>52W Low ₹{low52.toFixed(0)}</span>
              <span>52W High ₹{high52.toFixed(0)}</span>
            </div>
            <MeterBar value={rangePct} color="#4488FF" />
            <div className="text-[10px] text-muted mt-0.5 text-center">{rangePct.toFixed(0)}% from 52W low</div>
          </div>
        </div>
      </Card>

      {/* Fundamental grade */}
      <Card>
        <CardHeader>
          <SectionTitle>Fundamental Grade</SectionTitle>
          <span className="text-lg font-bold" style={{ color: gradeColor[grade] ?? '#FFB020' }}>{grade}</span>
        </CardHeader>
        <div className="grid grid-cols-3 gap-3 text-xs">
          {((): { label: string; display: string }[] => [
            { label: 'P/E',      display: `${String(fund.pe ?? '—')}x` },
            { label: 'EPS',      display: `₹${String(fund.eps ?? '—')}` },
            { label: 'ROE',      display: `${String(fund.roe ?? '—')}%` },
            { label: 'ROCE',     display: `${String(fund.roce ?? '—')}%` },
            { label: 'D/E',      display: `${String(fund.de_ratio ?? '—')}x` },
            { label: 'Promoter', display: `${String(fund.promoter_holding ?? '—')}%` },
          ])().map(({ label, display }) => (
            <div key={label}>
              <div className="text-muted text-[10px]">{label}</div>
              <div className="font-bold text-text">{display}</div>
            </div>
          ))}
        </div>
        <div className="mt-3 text-xs space-y-1.5">
          <div className="flex justify-between"><span className="text-muted">Revenue Growth YoY</span><span className="text-bull">+{String(fund.revenue_growth_yoy ?? '—')}%</span></div>
          <div className="flex justify-between"><span className="text-muted">PAT Growth YoY</span><span className="text-bull">+{String(fund.pat_growth_yoy ?? '—')}%</span></div>
          <div className="flex justify-between"><span className="text-muted">Market Cap</span><span className="text-text">{String(fund.market_cap ?? '—')}</span></div>
        </div>
      </Card>
    </div>
  )
}

// ─── Tab: Chart ───────────────────────────────────────────────────────────────

function TabChart({ symbol, ltp }: { symbol: string; ltp: number }) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInst = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!chartRef.current) return
    const chart = createChart(chartRef.current, {
      width: chartRef.current.clientWidth, height: chartRef.current.clientHeight,
      layout: { background: { type: ColorType.Solid, color: '#141824' }, textColor: '#6B7280' },
      grid: { vertLines: { color: '#1E2535' }, horzLines: { color: '#1E2535' } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#1E2535' },
      timeScale: { borderColor: '#1E2535', timeVisible: true },
    })
    chartInst.current = chart
    const series = chart.addCandlestickSeries({
      upColor: '#00FF88', downColor: '#FF3355',
      borderUpColor: '#00FF88', borderDownColor: '#FF3355',
      wickUpColor: '#00FF88', wickDownColor: '#FF3355',
    })
    series.setData(buildMockCandles(ltp) as CandlestickData[])

    const ro = new ResizeObserver(() => {
      if (chartRef.current) chart.applyOptions({ width: chartRef.current.clientWidth, height: chartRef.current.clientHeight })
    })
    ro.observe(chartRef.current)
    return () => { ro.disconnect(); chart.remove() }
  }, [symbol, ltp])

  return <div ref={chartRef} className="h-96 w-full rounded-lg overflow-hidden border border-border" />
}

// ─── Tab: Technical Snapshot ──────────────────────────────────────────────────

function TabTechnical({ technical }: { technical: TechnicalSnapshot | null }) {
  const tfs = technical?.timeframes ?? {}
  function scoreToBias(score: number | null) {
    if (score === null || score === undefined) return { label: '—', color: '#6B7280' }
    if (score >= 75) return { label: 'STRONG BUY', color: '#00FF88' }
    if (score >= 60) return { label: 'BUY',        color: '#00FF88' }
    if (score >= 45) return { label: 'NEUTRAL',    color: '#FFB020' }
    if (score >= 30) return { label: 'SELL',       color: '#FF3355' }
    return { label: 'STRONG SELL', color: '#FF3355' }
  }

  const TF_NAMES = ['5m', '15m', '1h', 'daily']

  return (
    <Card>
      <CardHeader><SectionTitle>Multi-Timeframe Technical Matrix</SectionTitle></CardHeader>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border text-muted">
              <th className="text-left py-2 font-normal">Timeframe</th>
              <th className="text-center py-2 font-normal">RSI</th>
              <th className="text-center py-2 font-normal">MACD</th>
              <th className="text-center py-2 font-normal">VWAP</th>
              <th className="text-center py-2 font-normal">Buy</th>
              <th className="text-center py-2 font-normal">Sell</th>
              <th className="text-center py-2 font-normal">Score</th>
              <th className="text-center py-2 font-normal">Bias</th>
            </tr>
          </thead>
          <tbody>
            {TF_NAMES.map((tf) => {
              const d = tfs[tf]
              if (!d) return <tr key={tf} className="border-b border-border/50"><td className="py-2 text-muted uppercase">{tf}</td><td colSpan={7} className="text-center text-muted">No data</td></tr>
              const bias = scoreToBias(d.bull_score)
              return (
                <tr key={tf} className="border-b border-border/50 hover:bg-border/10">
                  <td className="py-2 font-semibold text-text uppercase">{tf}</td>
                  <td className="py-2 text-center">
                    <span className={clsx('font-bold', (d.rsi ?? 50) > 70 ? 'text-bear' : (d.rsi ?? 50) < 30 ? 'text-bull' : 'text-amber')}>
                      {d.rsi?.toFixed(0) ?? '—'}
                    </span>
                  </td>
                  <td className="py-2 text-center">
                    <span className={d.macd_signal === 'BUY' ? 'text-bull' : d.macd_signal === 'SELL' ? 'text-bear' : 'text-amber'}>
                      {d.macd_signal ?? '—'}
                    </span>
                  </td>
                  <td className="py-2 text-center text-muted">{d.vwap?.toFixed(0) ?? '—'}</td>
                  <td className="py-2 text-center text-bull">{d.buy_count}</td>
                  <td className="py-2 text-center text-bear">{d.sell_count}</td>
                  <td className="py-2 text-center">
                    <ScoreBadge score={d.bull_score} size="sm" />
                  </td>
                  <td className="py-2 text-center font-bold text-xs" style={{ color: bias.color }}>
                    {bias.label}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

// ─── Tab: Historical Performance ──────────────────────────────────────────────

function TabHistorical({ symbol }: { symbol: string }) {
  const monthly = mockMonthlyReturns()
  const calendarData = Array.from({ length: 20 }, (_, i) => ({ day: i + 1, ret: (Math.random() - 0.4) * 5 }))

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><SectionTitle>Monthly Returns (12 months)</SectionTitle></CardHeader>
        <ResponsiveContainer width="100%" height={160}>
          <BarChart data={monthly} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
            <XAxis dataKey="month" tick={{ fill: '#6B7280', fontSize: 10 }} />
            <YAxis tick={{ fill: '#6B7280', fontSize: 10 }} unit="%" />
            <Tooltip contentStyle={{ background: '#141824', border: '1px solid #1E2535', fontSize: 11 }} formatter={(v: number) => [`${v.toFixed(2)}%`, 'Return']} />
            <Bar dataKey="return" radius={[2, 2, 0, 0]}>
              {monthly.map((m, i) => <Cell key={i} fill={m.return >= 0 ? '#00FF88' : '#FF3355'} />)}
            </Bar>
            <ReferenceLine y={0} stroke="#1E2535" />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card>
        <CardHeader><SectionTitle>Daily Return Calendar Heatmap</SectionTitle></CardHeader>
        <div className="flex flex-wrap gap-1">
          {calendarData.map((d) => (
            <div
              key={d.day}
              title={`Day ${d.day}: ${d.ret.toFixed(2)}%`}
              className="w-7 h-7 rounded text-[9px] flex items-center justify-center font-semibold"
              style={{ backgroundColor: d.ret > 0 ? `rgba(0,255,136,${Math.min(0.8, d.ret / 5)})` : `rgba(255,51,85,${Math.min(0.8, Math.abs(d.ret) / 5)})`, color: Math.abs(d.ret) > 2 ? '#fff' : '#6B7280' }}
            >
              {d.day}
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <CardHeader><SectionTitle>Intraday Strategy Win Rate for {symbol}</SectionTitle></CardHeader>
        <div className="space-y-2 text-xs">
          {[
            { setup: 'VWAP Bounce', wins: 12, total: 18, avgR: 1.8 },
            { setup: 'ORB Breakout', wins: 9, total: 14, avgR: 1.5 },
            { setup: 'EMA Pullback', wins: 7, total: 11, avgR: 2.1 },
          ].map((s) => (
            <div key={s.setup} className="space-y-0.5">
              <div className="flex justify-between">
                <span className="text-text">{s.setup}</span>
                <span className="text-muted">{s.wins}/{s.total} · Avg {s.avgR}R</span>
              </div>
              <MeterBar value={(s.wins / s.total) * 100} color="#00FF88" />
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

// ─── Tab: AI Full Analysis ────────────────────────────────────────────────────

function TabAIAnalysis({ symbol, quote }: { symbol: string; quote: StockQuote }) {
  return (
    <div className="space-y-4">
      <Card glow="info">
        <CardHeader>
          <SectionTitle>AI Full Analysis</SectionTitle>
          <Bot size={14} className="text-info" />
        </CardHeader>
        <div className="text-sm text-muted leading-relaxed space-y-3">
          <p>
            <span className="text-text font-semibold">{symbol}</span> is a{' '}
            {quote.change_pct >= 0 ? <span className="text-bull">bullish</span> : <span className="text-bear">bearish</span>}{' '}
            candidate today. Price is {quote.change_pct >= 0 ? 'above' : 'below'} all key EMAs and the VWAP is acting as{' '}
            {quote.change_pct >= 0 ? 'support' : 'resistance'}. The ADX at 28 indicates a trending environment, favorable for momentum strategies.
          </p>
          <p>
            From a Varsity Module 9 (Market Psychology) perspective, the CVD divergence suggests institutional accumulation at this level. Volume at price analysis shows a High Value Node (HVN) cluster near current price, which often acts as a magnet.
          </p>
          <p>
            <span className="text-amber font-semibold">Risk factors:</span> Upcoming earnings could introduce volatility. The PCR at 0.88 is slightly below neutral (1.0), indicating mild bearish hedging. Sector rotation data shows Banking at #1 rank today, which is a tailwind.
          </p>
        </div>
      </Card>

      <Card>
        <CardHeader><SectionTitle>Historical Setup Performance for {symbol}</SectionTitle></CardHeader>
        <p className="text-xs text-muted leading-relaxed">
          {symbol} has triggered the <span className="text-info">VWAP Bounce</span> strategy 18 times this year:
          {' '}<span className="text-bull">12 winners</span> (+2.1R avg) and{' '}
          <span className="text-bear">6 losses</span> (−0.9R avg).
          Net expectancy: <span className="text-bull">+1.2R per trade</span>.
          Best time window: <span className="text-amber">9:20–10:30 AM IST</span>.
        </p>
      </Card>

      <Card>
        <CardHeader><SectionTitle>Sector Outlook</SectionTitle></CardHeader>
        <div className="text-xs text-muted space-y-2">
          <div className="flex justify-between"><span>Banking Sector Rank</span><span className="text-bull font-bold">#1 of 11</span></div>
          <div className="flex justify-between"><span>Nifty Bank vs Nifty</span><span className="text-bull">Outperforming +0.8%</span></div>
          <div className="flex justify-between"><span>FII in Banking</span><span className="text-bull">Net Buyers ₹840Cr</span></div>
          <div className="flex justify-between"><span>PCR (Bank Nifty)</span><span className="text-amber">0.88 (Watch)</span></div>
        </div>
      </Card>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'overview',    label: 'Overview',    icon: Star       },
  { id: 'chart',      label: 'Chart',       icon: BarChart2  },
  { id: 'technical',  label: 'Technical',   icon: TrendingUp },
  { id: 'historical', label: 'Historical',  icon: TrendingDown },
  { id: 'ai',         label: 'AI Analysis', icon: Bot        },
] as const

type TabId = typeof TABS[number]['id']

export function StockExplorer() {
  const [input, setInput]       = useState('HDFCBANK')
  const [symbol, setSymbol]     = useState('HDFCBANK')
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [quote, setQuote]       = useState<StockQuote | null>(null)
  const [tech, setTech]         = useState<TechnicalSnapshot | null>(null)
  const [fund, setFund]         = useState<Fundamentals | null>(null)
  const [loading, setLoading]   = useState(false)

  async function load(sym: string) {
    setLoading(true)
    const [q, t, f] = await Promise.allSettled([
      stocksApi.getQuote(sym),
      stocksApi.getTechnical(sym),
      stocksApi.getFundamentals(sym),
    ])
    setQuote(q.status === 'fulfilled' ? q.value : mockQuote(sym))
    setTech(t.status === 'fulfilled' ? t.value : mockTechnical(sym))
    setFund(f.status === 'fulfilled' ? f.value : mockFundamentals(sym))
    setLoading(false)
  }

  useEffect(() => { load(symbol) }, [symbol])

  function search() {
    const sym = input.trim().toUpperCase()
    if (sym && sym !== symbol) setSymbol(sym)
  }

  const q = quote ?? mockQuote(symbol)

  return (
    <div className="space-y-4 max-w-full">
      {/* Search */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 bg-card border border-border rounded-md px-3 py-2 w-64">
          <Search size={14} className="text-muted" />
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search()}
            placeholder="Search symbol (e.g. RELIANCE)…"
            className="bg-transparent text-text text-sm focus:outline-none flex-1"
          />
          <button onClick={search} className="text-info text-xs hover:underline">Go</button>
        </div>
        {quote && !loading && (
          <div className="flex items-center gap-3 text-sm">
            <span className="font-bold text-text">{q.symbol}</span>
            <AnimatedNumber value={q.ltp} prefix="₹" decimals={2} className="font-bold text-text" />
            <span className={clsx('font-semibold', q.change_pct >= 0 ? 'text-bull' : 'text-bear')}>
              {q.change_pct >= 0 ? '+' : ''}{q.change_pct.toFixed(2)}%
            </span>
            <span className="text-muted text-xs">Vol: {(q.volume / 1000).toFixed(0)}K</span>
          </div>
        )}
        {loading && <span className="text-muted text-xs animate-pulse">Loading…</span>}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-border">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 text-xs font-semibold border-b-2 transition-colors',
              activeTab === id
                ? 'border-info text-info'
                : 'border-transparent text-muted hover:text-text'
            )}
          >
            <Icon size={13} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          {activeTab === 'overview'   && <TabOverview quote={q} fundamentals={fund} />}
          {activeTab === 'chart'      && <TabChart symbol={symbol} ltp={q.ltp} />}
          {activeTab === 'technical'  && <TabTechnical technical={tech} />}
          {activeTab === 'historical' && <TabHistorical symbol={symbol} />}
          {activeTab === 'ai'         && <TabAIAnalysis symbol={symbol} quote={q} />}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
