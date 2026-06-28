import { motion } from 'framer-motion'
import type { Suggestion } from '../../api/suggestions'
import { MeterBar } from '../ui/MeterBar'
import clsx from 'clsx'

interface Panel4WhyProps {
  suggestion: Suggestion
}

const AGENT_DISPLAY: Record<string, string> = {
  market_structure:   'Market Structure',
  order_flow:         'Order Flow',
  volume_profile:     'Volume Profile',
  strategy_engine:    'Strategy Engine',
  sector_rotation:    'Sector Rotation',
  news_intelligence:  'News Intelligence',
  global_correlation: 'Global Correlation',
  options_analysis:   'Options Analysis',
  sentiment:          'Sentiment',
  liquidity:          'Liquidity',
  risk_reward:        'Risk/Reward',
}

export function Panel4Why({ suggestion: s }: Panel4WhyProps) {
  const scores = (s.agent_scores ?? {}) as Record<string, number>

  // Default agent scores if not provided
  const defaultScores: Record<string, number> = {
    market_structure: 9,   order_flow: 8,   volume_profile: 9,
    strategy_engine: 9,    sector_rotation: 9, news_intelligence: 8,
    global_correlation: 8, options_analysis: 7, sentiment: 7,
    liquidity: 9,          risk_reward: 10,
  }
  const agentScores = Object.keys(defaultScores).length > Object.keys(scores).length ? defaultScores : scores

  const reasonsFor     = s.reasons_for ?? [
    'At POC + VWAP + EMA20 cluster',
    'CVD +48,200 (buyers aggressive)',
    'Volume 2.8× average on bounce',
    'Banking sector outperform +0.8%',
    'FII net buyers ₹1,840Cr',
    'Pattern: Bullish engulfing ✓',
    'Structure: HH/HL intact ✓',
  ]
  const reasonsAgainst = s.reasons_against ?? [
    'PCR only 0.88 (not strong)',
    '3rd trade today (fatigue risk)',
  ]
  const setupConditions = s.setup_conditions ?? [
    'Price pulls to VWAP + POC zone',
    'Bullish candle confirmation',
    'CVD rising (buyers dominant)',
    'Sector outperforming',
    'Volume ≥ 1.5× average',
  ]

  return (
    <div className="flex flex-col h-full overflow-y-auto text-xs space-y-4 px-1">
      {/* Agent contributions */}
      <div className="space-y-2 pt-1">
        <div className="text-[10px] text-muted uppercase tracking-widest">Agent Confidence</div>
        {Object.entries(agentScores).map(([k, v], i) => (
          <motion.div
            key={k}
            initial={{ opacity: 0, x: -4 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04 }}
            className="space-y-0.5"
          >
            <div className="flex items-center justify-between">
              <span className="text-text">{AGENT_DISPLAY[k] ?? k}</span>
              <span className={clsx('font-bold text-[10px]', v >= 9 ? 'text-bull' : v >= 7 ? 'text-amber' : 'text-bear')}>
                {v}/10
              </span>
            </div>
            <MeterBar value={(v / 10) * 100} color={v >= 9 ? '#00FF88' : v >= 7 ? '#FFB020' : '#FF3355'} />
          </motion.div>
        ))}
      </div>

      {/* Top reasons for */}
      <div className="space-y-1.5">
        <div className="text-[10px] text-muted uppercase tracking-widest">Reasons For</div>
        {reasonsFor.map((r, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 + i * 0.05 }}
            className="flex items-start gap-1.5"
          >
            <span className="text-bull mt-0.5 shrink-0">✓</span>
            <span className="text-text">{r}</span>
          </motion.div>
        ))}
      </div>

      {/* Reasons against */}
      {reasonsAgainst.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-[10px] text-muted uppercase tracking-widest">Reasons Against</div>
          {reasonsAgainst.map((r, i) => (
            <div key={i} className="flex items-start gap-1.5">
              <span className="text-bear mt-0.5 shrink-0">✗</span>
              <span className="text-muted">{r}</span>
            </div>
          ))}
        </div>
      )}

      {/* Strategy being applied */}
      <div className="space-y-1.5">
        <div className="text-[10px] text-muted uppercase tracking-widest">Strategy Applied</div>
        <div className="bg-info/5 border border-info/20 rounded-md p-2 space-y-1.5">
          <div className="font-bold text-info">{s.strategy_name ?? 'VWAP Bounce at POC'}</div>
          <div className="text-muted text-[10px]">Conditions required:</div>
          {setupConditions.map((c, i) => (
            <div key={i} className="flex items-center gap-1.5 text-[10px]">
              <span className="text-bull">✓</span>
              <span className="text-text">{c}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Market context */}
      <div className="space-y-1.5">
        <div className="text-[10px] text-muted uppercase tracking-widest">Market Context</div>
        <div className="grid grid-cols-2 gap-x-3 gap-y-1">
          <div className="text-muted">Regime</div>
          <div className="text-bull font-semibold">{(s.market_regime ?? 'TRENDING_UP').replace('_', ' ')}</div>
          <div className="text-muted">Nifty</div>
          <div className={s.nifty_bias === 'BULLISH' ? 'text-bull' : 'text-muted'}>{s.nifty_bias ?? 'Bullish 78%'}</div>
          <div className="text-muted">BankNifty</div>
          <div className={s.banknifty_bias === 'BULLISH' ? 'text-bull' : 'text-muted'}>{s.banknifty_bias ?? 'Bullish 82%'}</div>
          <div className="text-muted">VIX</div>
          <div className={clsx((s.vix_level ?? 14) < 15 ? 'text-bull' : 'text-amber')}>
            {(s.vix_level ?? 14.2).toFixed(1)} {(s.vix_level ?? 14) < 15 ? '(calm)' : '(watch)'}
          </div>
          <div className="text-muted">FII</div>
          <div className={(s.fii_net_flow ?? 0) >= 0 ? 'text-bull' : 'text-bear'}>
            {(s.fii_net_flow ?? 0) >= 0 ? 'Net BUYERS ✓' : 'Net SELLERS'}
          </div>
        </div>
      </div>

      {/* Invalidation */}
      <div className="space-y-1.5">
        <div className="text-[10px] text-muted uppercase tracking-widest">Invalidation Triggers</div>
        <div className="space-y-1">
          <div className="text-bear text-[10px]">→ 5m close below ₹{s.invalidation_level ?? (s.stop_loss * 1.006).toFixed(2)} + volume spike</div>
          <div className="text-bear text-[10px]">→ Nifty structural breakdown</div>
          <div className="text-bear text-[10px]">→ Negative sector/macro news</div>
        </div>
      </div>
    </div>
  )
}
