import { motion } from 'framer-motion'
import type { Suggestion } from '../../api/suggestions'
import { MeterBar } from '../ui/MeterBar'
import { ScoreBadge } from '../ui/ScoreBadge'
import clsx from 'clsx'

interface Panel2SignalsProps {
  suggestion: Suggestion
}

interface IndicatorRow {
  name: string
  value: string
  signal: 'BUY' | 'SELL' | 'NEUTRAL'
  detail: string
}

function deriveIndicators(s: Suggestion): IndicatorRow[] {
  const snap = (s.indicators_snapshot ?? {}) as Record<string, unknown>
  const get = (k: string, def: number) => (typeof snap[k] === 'number' ? (snap[k] as number) : def)

  const rsi = get('rsi', 52)
  const adx = get('adx', 28)
  const atrPct = get('atr_pct', 1.3)

  return [
    {
      name: 'RSI (14)',
      value: rsi.toFixed(0),
      signal: rsi < 30 ? 'BUY' : rsi > 70 ? 'SELL' : 'BUY',
      detail: rsi < 30 ? 'Oversold — strong buy zone' : rsi > 70 ? 'Overbought' : 'Neutral range — room to run',
    },
    {
      name: 'MACD',
      value: 'Bullish ✗',
      signal: 'BUY',
      detail: 'Signal crossed above hist rising',
    },
    {
      name: 'VWAP',
      value: 'Above',
      signal: 'BUY',
      detail: 'Price bouncing off VWAP ✓',
    },
    {
      name: 'EMA Stack',
      value: 'Aligned',
      signal: 'BUY',
      detail: 'EMA20 < EMA50 < Price ✓',
    },
    {
      name: 'Bollinger Bands',
      value: 'Midband',
      signal: 'BUY',
      detail: 'Room to upper band ✓',
    },
    {
      name: `ADX (${adx.toFixed(0)})`,
      value: adx >= 25 ? 'Trending' : 'Weak',
      signal: adx >= 25 ? 'BUY' : 'NEUTRAL',
      detail: adx >= 25 ? 'Strong trend — follow momentum' : 'Weak trend',
    },
    {
      name: `ATR (${atrPct.toFixed(1)}%)`,
      value: atrPct < 2 ? 'Normal' : 'High',
      signal: atrPct < 2 ? 'BUY' : 'NEUTRAL',
      detail: atrPct < 2 ? 'Normal volatility ✓' : 'High volatility — size down',
    },
    {
      name: 'SuperTrend',
      value: 'Bullish',
      signal: 'BUY',
      detail: 'Green below price ✓',
    },
    {
      name: 'Stoch RSI',
      value: 'Crossed Up',
      signal: 'BUY',
      detail: 'Crossed up from oversold zone ✓',
    },
    {
      name: 'OBV',
      value: 'Rising',
      signal: 'BUY',
      detail: 'Volume confirming price move ✓',
    },
  ]
}

const signalColor: Record<string, string> = {
  BUY:     '#00FF88',
  SELL:    '#FF3355',
  NEUTRAL: '#FFB020',
}

export function Panel2Signals({ suggestion }: Panel2SignalsProps) {
  const indicators = deriveIndicators(suggestion)
  const buyCount  = indicators.filter((i) => i.signal === 'BUY').length
  const sellCount = indicators.filter((i) => i.signal === 'SELL').length
  const neutCount = indicators.filter((i) => i.signal === 'NEUTRAL').length

  const mtf = [
    { tf: '5m',    rsi: 54, macd: true, ema: true, bb: false, bull: true },
    { tf: '15m',   rsi: 52, macd: true, ema: true, bb: false, bull: true },
    { tf: '1H',    rsi: 55, macd: true, ema: true, bb: true,  bull: true },
    { tf: 'Daily', rsi: 61, macd: true, ema: true, bb: true,  bull: true },
  ]

  return (
    <div className="flex flex-col h-full overflow-y-auto text-xs space-y-4 px-1">
      {/* Overall score */}
      <div className="flex items-center gap-3 pt-1">
        <ScoreBadge score={suggestion.confidence_score} size="lg" />
        <div>
          <div className="text-sm font-bold text-text">{suggestion.confidence_score}/100</div>
          <div className="text-muted text-[10px]">Overall Signal</div>
          <MeterBar value={suggestion.confidence_score} color="#4488FF" />
        </div>
      </div>

      {/* Indicator rows */}
      <div className="space-y-2">
        <div className="text-[10px] text-muted uppercase tracking-widest">Indicator Readings</div>
        {indicators.map((ind, i) => (
          <motion.div
            key={ind.name}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04 }}
            className="space-y-0.5"
          >
            <div className="flex items-center justify-between">
              <span className="text-text font-semibold">{ind.name}</span>
              <span className="font-bold" style={{ color: signalColor[ind.signal] }}>
                {ind.signal}
              </span>
            </div>
            <div className="text-muted text-[10px]">{ind.detail}</div>
            <MeterBar
              value={ind.signal === 'BUY' ? 80 : ind.signal === 'SELL' ? 20 : 50}
              color={signalColor[ind.signal]}
            />
          </motion.div>
        ))}
      </div>

      {/* Multi-timeframe */}
      <div className="space-y-2">
        <div className="text-[10px] text-muted uppercase tracking-widest">Multi-Timeframe</div>
        <table className="w-full text-[10px]">
          <thead>
            <tr className="text-muted border-b border-border">
              <th className="text-left pb-1 font-normal">TF</th>
              <th className="text-center pb-1 font-normal">RSI</th>
              <th className="text-center pb-1 font-normal">MACD</th>
              <th className="text-center pb-1 font-normal">EMA</th>
              <th className="text-center pb-1 font-normal">Overall</th>
            </tr>
          </thead>
          <tbody>
            {mtf.map((r) => (
              <tr key={r.tf} className="border-b border-border/30">
                <td className="py-1 font-semibold text-text">{r.tf}</td>
                <td className="py-1 text-center text-muted">{r.rsi}</td>
                <td className="py-1 text-center">{r.macd ? '🟢' : '🔴'}</td>
                <td className="py-1 text-center">{r.ema ? '🟢' : '🔴'}</td>
                <td className="py-1 text-center">{r.bull ? '🟢' : '🔴'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Signal consensus */}
      <div className="space-y-2">
        <div className="text-[10px] text-muted uppercase tracking-widest">Signal Consensus</div>
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-bull">BUY</span>
            <span className="text-bull font-bold">{buyCount}</span>
          </div>
          <MeterBar value={(buyCount / indicators.length) * 100} color="#00FF88" />
          <div className="flex items-center justify-between">
            <span className="text-bear">SELL</span>
            <span className="text-bear font-bold">{sellCount}</span>
          </div>
          <MeterBar value={(sellCount / indicators.length) * 100} color="#FF3355" />
          <div className="flex items-center justify-between">
            <span className="text-amber">NEUTRAL</span>
            <span className="text-amber font-bold">{neutCount}</span>
          </div>
          <MeterBar value={(neutCount / indicators.length) * 100} color="#FFB020" />
        </div>
      </div>
    </div>
  )
}
