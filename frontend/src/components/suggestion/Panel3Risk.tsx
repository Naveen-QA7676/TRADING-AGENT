import { motion } from 'framer-motion'
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts'
import type { Suggestion } from '../../api/suggestions'
import { MeterBar } from '../ui/MeterBar'
import clsx from 'clsx'

interface Panel3RiskProps {
  suggestion: Suggestion
}

export function Panel3Risk({ suggestion: s }: Panel3RiskProps) {
  const entry = (s.entry_price_low + s.entry_price_high) / 2
  const winPct  = Math.round((s.win_probability  ?? 0.63) * 100)
  const stopPct = Math.round((s.stop_probability ?? 0.21) * 100)
  const sidePct = Math.max(0, 100 - winPct - stopPct)

  const t1Gain  = s.quantity ? (s.target_1 - entry) * s.quantity : 0
  const t2Gain  = s.target_2 && s.quantity ? (s.target_2 - entry) * s.quantity : 0
  const risk    = s.risk_amount ?? 0

  const pieData = [
    { name: 'WIN',      value: winPct,  color: '#00FF88' },
    { name: 'STOP',     value: stopPct, color: '#FF3355' },
    { name: 'SIDEWAYS', value: sidePct, color: '#FFB020' },
  ]

  const histWR = Math.round((s.historical_win_rate ?? 0.67) * 100)
  const count  = s.historical_trades_count ?? 156
  const avgWin = s.historical_avg_win_r ?? 2.3
  const avgLoss= s.historical_avg_loss_r ?? 1.0
  const expectancy = s.historical_expectancy ?? 1.2

  return (
    <div className="flex flex-col h-full overflow-y-auto text-xs space-y-4 px-1">
      {/* Confidence score */}
      <div className="text-center pt-1">
        <div className="text-[10px] text-muted uppercase tracking-widest mb-2">Confidence</div>
        <div className="text-4xl font-bold" style={{ color: s.confidence_score >= 80 ? '#00FF88' : s.confidence_score >= 65 ? '#FFB020' : '#FF3355' }}>
          {s.confidence_score}
        </div>
        <MeterBar value={s.confidence_score} color={s.confidence_score >= 80 ? '#00FF88' : '#FFB020'} />
      </div>

      {/* 3 Scenario probabilities */}
      <div className="space-y-2">
        <div className="text-[10px] text-muted uppercase tracking-widest">Scenario Probabilities</div>
        <div className="flex gap-3 items-center">
          {/* Pie */}
          <div className="w-20 h-20 shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} dataKey="value" cx="50%" cy="50%" innerRadius={20} outerRadius={36} strokeWidth={0}>
                  {pieData.map((d) => <Cell key={d.name} fill={d.color} />)}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
          {/* Bars */}
          <div className="flex-1 space-y-2">
            {pieData.map((d) => (
              <div key={d.name} className="space-y-0.5">
                <div className="flex justify-between">
                  <span className="font-semibold" style={{ color: d.color }}>
                    {d.name === 'WIN' ? '✅' : d.name === 'STOP' ? '❌' : '⏸'} {d.name}
                  </span>
                  <span style={{ color: d.color }}>{d.value}%</span>
                </div>
                <motion.div
                  className="h-1.5 rounded-full"
                  style={{ backgroundColor: '#1E2535' }}
                >
                  <motion.div
                    className="h-full rounded-full"
                    style={{ backgroundColor: d.color }}
                    initial={{ width: 0 }}
                    animate={{ width: `${d.value}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut', delay: 0.2 }}
                  />
                </motion.div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Trade economics */}
      <div className="space-y-1.5">
        <div className="text-[10px] text-muted uppercase tracking-widest">Trade Economics</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
          <div className="text-muted">Entry</div>
          <div className="text-info font-semibold">₹{s.entry_price_low}–{s.entry_price_high}</div>
          <div className="text-muted">Stop</div>
          <div className="text-bear font-semibold">₹{s.stop_loss} (−{(((entry - s.stop_loss) / entry) * 100).toFixed(1)}%)</div>
          <div className="text-muted">Target 1</div>
          <div className="text-bull font-semibold">₹{s.target_1} (+{(((s.target_1 - entry) / entry) * 100).toFixed(1)}%)</div>
          {s.target_2 && <>
            <div className="text-muted">Target 2</div>
            <div className="text-bull font-semibold">₹{s.target_2} (+{(((s.target_2 - entry) / entry) * 100).toFixed(1)}%)</div>
          </>}
          <div className="text-muted">R:R Ratio</div>
          <div className={clsx('font-bold', (s.rr_ratio ?? 0) >= 2 ? 'text-bull' : 'text-amber')}>
            1:{s.rr_ratio?.toFixed(1) ?? '—'} {(s.rr_ratio ?? 0) >= 2 ? '✓' : '⚠'}
          </div>
        </div>
      </div>

      {/* Your numbers */}
      {s.quantity && (
        <div className="space-y-1.5">
          <div className="text-[10px] text-muted uppercase tracking-widest">Your Numbers</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            <div className="text-muted">Shares</div>
            <div className="text-text font-semibold">{s.quantity}</div>
            <div className="text-muted">Capital</div>
            <div className="text-text font-semibold">₹{s.capital_deployed?.toLocaleString('en-IN') ?? '—'}</div>
            <div className="text-muted">Risk</div>
            <div className="text-bear font-semibold">₹{risk.toFixed(0)} ({((s.risk_pct ?? 0) * 100).toFixed(1)}%)</div>
            <div className="text-muted">T1 Gain</div>
            <div className="text-bull font-semibold">+₹{t1Gain.toFixed(0)}</div>
            {t2Gain > 0 && <>
              <div className="text-muted">T2 Gain</div>
              <div className="text-bull font-semibold">+₹{t2Gain.toFixed(0)}</div>
            </>}
          </div>
        </div>
      )}

      {/* Historical edge */}
      <div className="space-y-1.5">
        <div className="text-[10px] text-muted uppercase tracking-widest">Historical Edge</div>
        <div className="space-y-1.5">
          <div className="flex justify-between">
            <span className="text-muted">Win Rate</span>
            <span className={clsx('font-bold', histWR >= 60 ? 'text-bull' : histWR >= 45 ? 'text-amber' : 'text-bear')}>{histWR}%</span>
          </div>
          <MeterBar value={histWR} color={histWR >= 60 ? '#00FF88' : '#FFB020'} />
          <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 mt-1">
            <div className="text-muted">Avg Win</div>
            <div className="text-bull">{avgWin.toFixed(1)}R</div>
            <div className="text-muted">Avg Loss</div>
            <div className="text-bear">{avgLoss.toFixed(1)}R</div>
            <div className="text-muted">Expectancy</div>
            <div className={expectancy > 0 ? 'text-bull' : 'text-bear'}>+{expectancy.toFixed(1)}R / trade</div>
            <div className="text-muted">Sample</div>
            <div className="text-text">{count} trades</div>
          </div>
        </div>
      </div>
    </div>
  )
}
