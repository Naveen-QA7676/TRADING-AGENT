import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Zap, Clock, AlertTriangle } from 'lucide-react'
import { useStore } from '../store/useStore'
import { Panel1Chart } from '../components/suggestion/Panel1Chart'
import { Panel2Signals } from '../components/suggestion/Panel2Signals'
import { Panel3Risk } from '../components/suggestion/Panel3Risk'
import { Panel4Why } from '../components/suggestion/Panel4Why'
import { Panel5Decision } from '../components/suggestion/Panel5Decision'
import type { Suggestion } from '../api/suggestions'
import clsx from 'clsx'

// Demo suggestion — shown when no live signal exists yet
const DEMO_SUGGESTION: Suggestion = {
  id: -1,
  symbol: 'HDFCBANK',
  exchange: 'NSE',
  direction: 'LONG',
  strategy_name: 'VWAP Bounce at POC',
  confidence_score: 88,
  entry_price: 1648,
  entry_price_low: 1645,
  entry_price_high: 1652,
  stop_loss: 1628,
  target_1: 1692,
  target_2: 1720,
  invalidation_level: 1638,
  quantity: 61,
  capital_deployed: 100352,
  risk_amount: 1525,
  risk_pct: 0.01,
  rr_ratio: 2.1,
  win_probability: 0.63,
  stop_probability: 0.21,
  sideways_probability: 0.16,
  agent_scores: {
    market_structure: 9, order_flow: 8, volume_profile: 9,
    strategy_engine: 9, sector_rotation: 9, news_intelligence: 8,
    global_correlation: 8, options_analysis: 7, sentiment: 7,
    liquidity: 9, risk_reward: 10,
  },
  reasons_for: [
    'At POC + VWAP + EMA20 cluster',
    'CVD +48,200 (buyers aggressive)',
    'Volume 2.8× average on bounce',
    'Banking sector outperform +0.8%',
    'FII net buyers ₹1,840Cr',
    'Pattern: Bullish engulfing ✓',
    'Structure: HH/HL intact ✓',
  ],
  reasons_against: [
    'PCR only 0.88 (not strong)',
    '3rd trade today (fatigue risk)',
  ],
  setup_conditions: [
    'Price pulls to VWAP + POC zone',
    'Bullish candle confirmation',
    'CVD rising (buyers dominant)',
    'Sector outperforming',
    'Volume ≥ 1.5× average',
  ],
  indicators_snapshot: { rsi: 52, adx: 28, atr_pct: 1.3 },
  chart_pattern: 'Higher High / Higher Low',
  candlestick_pattern: 'Bullish Engulfing',
  historical_win_rate: 0.67,
  historical_trades_count: 156,
  historical_avg_win_r: 2.3,
  historical_avg_loss_r: 1.0,
  historical_expectancy: 1.2,
  nifty_bias: 'BULLISH',
  banknifty_bias: 'BULLISH',
  vix_level: 16.2,
  fii_net_flow: 1840,
  market_regime: 'TRENDING_UP',
  status: 'SUGGESTED',
  created_at: new Date().toISOString(),
  expires_at: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
}

function SignalTab({ s, active, onClick, isNew }: { s: Suggestion; active: boolean; onClick: () => void; isNew?: boolean }) {
  const bull = s.direction === 'LONG'
  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex items-center gap-2 px-3 py-2 rounded-t-lg text-xs font-semibold border-b-2 transition-colors whitespace-nowrap',
        active
          ? bull ? 'border-bull text-bull bg-bull/5' : 'border-bear text-bear bg-bear/5'
          : 'border-transparent text-muted hover:text-text',
        isNew && 'signal-glow'
      )}
    >
      <span className={bull ? 'text-bull' : 'text-bear'}>
        {bull ? '🔵' : '🔴'}
      </span>
      {s.symbol} {s.direction}
      <span className={clsx('px-1 py-0.5 rounded text-[10px] font-bold',
        s.confidence_score >= 80 ? 'bg-bull/10 text-bull' : 'bg-amber/10 text-amber'
      )}>
        {s.confidence_score}/100
      </span>
      {s.status === 'SUGGESTED' && (
        <span className="w-1.5 h-1.5 rounded-full bg-info live-pulse shrink-0" />
      )}
    </button>
  )
}

export function Suggestions() {
  const liveSuggestions = useStore((s) => s.suggestions)
  const [activeId, setActiveId] = useState<number | null>(null)

  // Use live signals if available, else show demo
  const suggestions: Suggestion[] = liveSuggestions.length > 0 ? liveSuggestions : [DEMO_SUGGESTION]
  const active = suggestions.find((s) => s.id === activeId) ?? suggestions[0]

  return (
    <div className="flex flex-col h-full -m-4">
      {/* Signal tabs header */}
      <div className="flex items-center gap-1 px-4 pt-3 pb-0 border-b border-border bg-card overflow-x-auto shrink-0">
        <div className="flex items-center gap-1 text-xs text-muted mr-4 shrink-0">
          <Zap size={12} className="text-info" />
          Signals
        </div>
        {suggestions.map((s) => (
          <SignalTab
            key={s.id}
            s={s}
            active={active?.id === s.id}
            onClick={() => setActiveId(s.id)}
            isNew={s.id !== DEMO_SUGGESTION.id}
          />
        ))}
        {liveSuggestions.length === 0 && (
          <span className="text-[10px] text-amber/60 ml-2 italic shrink-0">— showing demo signal, no live signals yet —</span>
        )}
      </div>

      {/* 5-panel layout */}
      <AnimatePresence mode="wait">
        {active ? (
          <motion.div
            key={active.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="flex flex-col flex-1 min-h-0"
          >
            {/* Top banner */}
            <div className={clsx(
              'px-4 py-2 flex items-center gap-4 text-sm font-bold shrink-0',
              active.direction === 'LONG' ? 'bg-bull/5 border-b border-bull/20 text-bull' : 'bg-bear/5 border-b border-bear/20 text-bear'
            )}>
              <span>
                {active.direction === 'LONG' ? '🔵 BUY' : '🔴 SELL'} SIGNAL — {active.symbol} (NSE: {active.symbol})
              </span>
              <span className="text-xs font-normal text-muted">
                {new Date(active.created_at).toLocaleTimeString('en-IN')}
              </span>
              <span className={clsx('ml-auto px-2 py-0.5 rounded text-sm font-bold',
                active.confidence_score >= 80 ? 'bg-bull/10 text-bull' : 'bg-amber/10 text-amber'
              )}>
                {active.confidence_score}/100 CONFIDENCE
              </span>
            </div>

            {/* Panels row */}
            <div className="flex flex-1 min-h-0 divide-x divide-border overflow-hidden">
              {/* Panel 1: Chart — 55% */}
              <div className="flex flex-col" style={{ width: '55%', minWidth: 0 }}>
                <div className="text-[10px] text-muted uppercase tracking-widest px-3 py-1.5 border-b border-border bg-card/50 shrink-0">
                  Panel 1 — Live Chart
                </div>
                <div className="flex-1 min-h-0 overflow-hidden">
                  <Panel1Chart suggestion={active} />
                </div>
              </div>

              {/* Panel 2: Signals — 15% */}
              <div className="flex flex-col" style={{ width: '15%', minWidth: 160 }}>
                <div className="text-[10px] text-muted uppercase tracking-widest px-3 py-1.5 border-b border-border bg-card/50 shrink-0">
                  Panel 2 — Signals
                </div>
                <div className="flex-1 min-h-0 overflow-y-auto p-2">
                  <Panel2Signals suggestion={active} />
                </div>
              </div>

              {/* Panel 3: Risk — 15% */}
              <div className="flex flex-col" style={{ width: '15%', minWidth: 160 }}>
                <div className="text-[10px] text-muted uppercase tracking-widest px-3 py-1.5 border-b border-border bg-card/50 shrink-0">
                  Panel 3 — Risk &amp; Probability
                </div>
                <div className="flex-1 min-h-0 overflow-y-auto p-2">
                  <Panel3Risk suggestion={active} />
                </div>
              </div>

              {/* Panel 4: Why — 15% */}
              <div className="flex flex-col" style={{ width: '15%', minWidth: 160 }}>
                <div className="text-[10px] text-muted uppercase tracking-widest px-3 py-1.5 border-b border-border bg-card/50 shrink-0">
                  Panel 4 — Why This Trade
                </div>
                <div className="flex-1 min-h-0 overflow-y-auto p-2">
                  <Panel4Why suggestion={active} />
                </div>
              </div>
            </div>

            {/* Panel 5: Decision zone — bottom */}
            <Panel5Decision suggestion={active} />
          </motion.div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-muted">
            <div className="text-center space-y-2">
              <Zap size={40} className="mx-auto text-info/30" />
              <p className="text-sm">No signals right now.</p>
              <p className="text-xs">Agents are scanning 487 stocks…</p>
            </div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}
