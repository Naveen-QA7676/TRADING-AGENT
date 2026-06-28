import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RefreshCw, ExternalLink, Bell, Globe, TrendingUp, Calendar } from 'lucide-react'
import { newsApi, NewsItem } from '../api/news'
import { Card, CardHeader, SectionTitle } from '../components/ui/Card'
import clsx from 'clsx'

// ─── Types ────────────────────────────────────────────────────────────────────

type FilterTab = 'ALL' | 'BREAKING' | 'STOCKS' | 'GLOBAL'
type Sentiment = 'BULLISH' | 'BEARISH' | 'NEUTRAL'
type Impact    = 'BREAKING' | 'HIGH' | 'MEDIUM' | 'LOW'

interface EconEvent {
  time: string
  event: string
  actual?: string
  forecast?: string
  previous?: string
  impact: Impact
}

// ─── Mock data ────────────────────────────────────────────────────────────────

const MOCK_NEWS: NewsItem[] = [
  {
    id: 1,
    source: 'MoneyControl',
    title: 'FIIs turn net buyers, pump ₹2,840Cr into Indian markets',
    summary: 'Foreign institutional investors reversed their selling trend, buying equities worth ₹2,840Cr on Thursday. Banking and IT sectors led the inflows.',
    url: '#',
    published_at: new Date(Date.now() - 4 * 60 * 1000).toISOString(),
    sentiment: 'BULLISH',
    impact_level: 'HIGH',
    symbols: ['NIFTYBANK', 'HDFCBANK', 'ICICIBANK'],
    category: 'FII',
  },
  {
    id: 2,
    source: 'Economic Times',
    title: 'RBI keeps repo rate unchanged at 6.5%; maintains accommodative stance',
    summary: 'The Monetary Policy Committee voted 4-2 to hold rates for the third consecutive meeting. Governor flagged inflation risks but remained optimistic on growth.',
    url: '#',
    published_at: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
    sentiment: 'NEUTRAL',
    impact_level: 'BREAKING',
    symbols: ['NIFTY', 'NIFTYBANK'],
    category: 'POLICY',
  },
  {
    id: 3,
    source: 'CNBC TV18',
    title: 'Infosys Q1 revenue miss; guidance reduced from 1–3% to flat',
    summary: 'Infosys reported Q1 FY26 revenue of $4.71B, missing estimates of $4.78B. Management cut full-year revenue guidance citing deal ramp slowdowns.',
    url: '#',
    published_at: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
    sentiment: 'BEARISH',
    impact_level: 'HIGH',
    symbols: ['INFY', 'TCS', 'WIPRO', 'HCLTECH'],
    category: 'EARNINGS',
  },
  {
    id: 4,
    source: 'Bloomberg',
    title: 'S&P 500 gains 0.8% on strong jobs data; Nasdaq hits record high',
    summary: 'US markets rallied after non-farm payrolls came in at 220K vs 185K estimate. Technology stocks led gains as rate cut expectations firmed.',
    url: '#',
    published_at: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
    sentiment: 'BULLISH',
    impact_level: 'MEDIUM',
    symbols: [],
    category: 'GLOBAL',
  },
  {
    id: 5,
    source: 'Business Standard',
    title: 'Reliance Industries planning ₹75,000Cr capex in renewable energy over 3 years',
    summary: 'RIL announced plans to invest ₹75,000Cr in solar panels, green hydrogen and battery storage. The capex will be spread over FY26–FY28.',
    url: '#',
    published_at: new Date(Date.now() - 1.5 * 60 * 60 * 1000).toISOString(),
    sentiment: 'BULLISH',
    impact_level: 'MEDIUM',
    symbols: ['RELIANCE'],
    category: 'CORPORATE',
  },
  {
    id: 6,
    source: 'PTI',
    title: 'Crude oil slides 1.4% to $78/bbl on demand concerns from China',
    summary: 'Brent crude fell on weak Chinese manufacturing PMI data published overnight. Aviation and paint sectors expected to benefit.',
    url: '#',
    published_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    sentiment: 'BEARISH',
    impact_level: 'MEDIUM',
    symbols: ['ONGC', 'BPCL', 'INDIGO'],
    category: 'COMMODITY',
  },
]

const ECON_CALENDAR: EconEvent[] = [
  { time: '09:00', event: 'India CPI (MoM)',          actual: '5.1%', forecast: '5.3%', previous: '4.8%', impact: 'HIGH' },
  { time: '09:30', event: 'RBI MPC Minutes',           actual: 'Released',                               impact: 'BREAKING' },
  { time: '12:00', event: 'US PPI (MoM)',              forecast: '0.2%',              previous: '0.3%',  impact: 'MEDIUM' },
  { time: '18:00', event: 'FOMC Member Speech',        forecast: 'Hawkish expected',                     impact: 'MEDIUM' },
  { time: '21:30', event: 'US Initial Jobless Claims', forecast: '218K',              previous: '222K',  impact: 'LOW' },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function timeAgo(iso: string) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 60)   return `${Math.floor(diff)}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

function sentimentStyle(s: Sentiment) {
  const map: Record<Sentiment, string> = {
    BULLISH: 'bg-bull/10 text-bull border border-bull/30',
    BEARISH: 'bg-bear/10 text-bear border border-bear/30',
    NEUTRAL: 'bg-muted/10 text-muted border border-border',
  }
  return map[s]
}

function impactStyle(i: Impact) {
  const map: Record<Impact, string> = {
    BREAKING: 'bg-bear/20 text-bear border border-bear/50 font-bold animate-pulse',
    HIGH:     'bg-amber/10 text-amber border border-amber/30',
    MEDIUM:   'bg-info/10 text-info border border-info/30',
    LOW:      'bg-border text-muted border border-border',
  }
  return map[i]
}

function impactEconStyle(i: Impact) {
  const map: Record<Impact, string> = {
    BREAKING: 'text-bear',
    HIGH:     'text-amber',
    MEDIUM:   'text-info',
    LOW:      'text-muted',
  }
  return map[i]
}

function econDotColor(i: Impact) {
  const map: Record<Impact, string> = { BREAKING: '#FF3355', HIGH: '#FFB020', MEDIUM: '#4488FF', LOW: '#6B7280' }
  return map[i]
}

function matchesFilter(item: NewsItem, filter: FilterTab) {
  if (filter === 'ALL')      return true
  if (filter === 'BREAKING') return item.impact_level === 'BREAKING'
  if (filter === 'STOCKS')   return item.symbols.length > 0
  if (filter === 'GLOBAL')   return item.category === 'GLOBAL'
  return true
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function NewsCard({ item, i }: { item: NewsItem; i: number }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: i * 0.04 }}
      className="border border-border rounded-lg p-3 hover:border-info/30 transition-colors cursor-pointer"
      onClick={() => setExpanded((p) => !p)}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className={clsx('text-[10px] px-1.5 py-0.5 rounded', sentimentStyle(item.sentiment as Sentiment))}>
              {item.sentiment}
            </span>
            <span className={clsx('text-[10px] px-1.5 py-0.5 rounded', impactStyle(item.impact_level as Impact))}>
              {item.impact_level}
            </span>
            <span className="text-[10px] text-muted">{item.source}</span>
            <span className="text-[10px] text-muted ml-auto">{timeAgo(item.published_at)}</span>
          </div>
          <p className="text-sm font-medium text-text leading-snug">{item.title}</p>
          <AnimatePresence>
            {expanded && (
              <motion.p
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="text-xs text-muted mt-2 leading-relaxed"
              >
                {item.summary}
              </motion.p>
            )}
          </AnimatePresence>
        </div>
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-muted hover:text-info transition-colors shrink-0"
        >
          <ExternalLink size={13} />
        </a>
      </div>

      {item.symbols.length > 0 && (
        <div className="flex gap-1.5 mt-2 flex-wrap">
          {item.symbols.map((s) => (
            <span key={s} className="text-[10px] px-1.5 py-0.5 rounded bg-info/10 text-info border border-info/20">
              {s}
            </span>
          ))}
        </div>
      )}
    </motion.div>
  )
}

function EconCalendarCard() {
  return (
    <Card>
      <CardHeader>
        <SectionTitle>
          <Calendar size={14} className="inline mr-1.5 mb-0.5" />
          Economic Calendar
        </SectionTitle>
        <span className="text-xs text-muted">Today's key events (IST)</span>
      </CardHeader>
      <div className="space-y-2">
        {ECON_CALENDAR.map((ev, i) => (
          <div key={i} className="flex items-center gap-3 py-2 border-b border-border/50 last:border-0">
            <span className="text-xs font-mono text-muted w-12 shrink-0">{ev.time}</span>
            <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: econDotColor(ev.impact) }} />
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-text">{ev.event}</div>
              {ev.forecast && (
                <div className="text-[10px] text-muted mt-0.5">
                  {ev.actual && <span className={clsx('font-bold mr-2', impactEconStyle(ev.impact))}>A:{ev.actual}</span>}
                  <span className="mr-2">F:{ev.forecast}</span>
                  {ev.previous && <span>P:{ev.previous}</span>}
                </div>
              )}
            </div>
            <span className={clsx('text-[10px] shrink-0', impactEconStyle(ev.impact))}>
              {ev.impact}
            </span>
          </div>
        ))}
      </div>
    </Card>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function NewsFeed() {
  const [filter, setFilter] = useState<FilterTab>('ALL')
  const [items, setItems] = useState<NewsItem[]>(MOCK_NEWS)
  const [loading, setLoading] = useState(false)
  const [breakingCount, setBreakingCount] = useState(0)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await newsApi.getAll()
      if (data.length > 0) setItems(data)
      const brk = await newsApi.getBreaking()
      if (brk.length > 0) setBreakingCount(brk.length)
    } catch {
      // use mock
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const filtered = items.filter((n) => matchesFilter(n, filter))
  const tabs: { id: FilterTab; label: string; icon: React.ReactNode }[] = [
    { id: 'ALL',      label: 'All',      icon: <Globe size={13} /> },
    { id: 'BREAKING', label: 'Breaking', icon: <Bell size={13} /> },
    { id: 'STOCKS',   label: 'Stocks',   icon: <TrendingUp size={13} /> },
    { id: 'GLOBAL',   label: 'Global',   icon: <Globe size={13} /> },
  ]

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Left — main news feed */}
      <div className="lg:col-span-2 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold">📰 News Feed</h1>
            <p className="text-xs text-muted">Sentiment-tagged · Real-time market news</p>
          </div>
          <button
            onClick={load}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md border border-border text-xs text-muted hover:text-text transition-colors"
          >
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        {/* Filter tabs */}
        <div className="flex gap-1 bg-card rounded-lg p-1 border border-border w-fit">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setFilter(t.id)}
              className={clsx(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-all',
                filter === t.id ? 'bg-info text-white font-medium' : 'text-muted hover:text-text',
              )}
            >
              {t.icon}
              {t.label}
              {t.id === 'BREAKING' && breakingCount > 0 && (
                <span className="bg-bear text-white text-[9px] rounded-full px-1 font-bold">{breakingCount}</span>
              )}
            </button>
          ))}
        </div>

        {/* News cards */}
        <div className="space-y-2">
          <AnimatePresence mode="popLayout">
            {filtered.length === 0 ? (
              <div className="text-center text-muted text-sm py-12">No {filter.toLowerCase()} news right now</div>
            ) : (
              filtered.map((item, i) => <NewsCard key={item.id} item={item} i={i} />)
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Right — economic calendar */}
      <div className="space-y-4">
        <EconCalendarCard />

        {/* Legend */}
        <Card>
          <CardHeader><SectionTitle>Impact Key</SectionTitle></CardHeader>
          <div className="space-y-2 text-xs">
            {(['BREAKING', 'HIGH', 'MEDIUM', 'LOW'] as Impact[]).map((lvl) => (
              <div key={lvl} className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: econDotColor(lvl) }} />
                <span className={impactEconStyle(lvl)}>{lvl}</span>
                <span className="text-muted">
                  {lvl === 'BREAKING' ? '— market-moving event' :
                   lvl === 'HIGH'     ? '— significant impact' :
                   lvl === 'MEDIUM'   ? '— moderate impact' : '— low impact'}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
