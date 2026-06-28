import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, XCircle, Clock, AlertTriangle } from 'lucide-react'
import type { Suggestion } from '../../api/suggestions'
import { suggestionsApi } from '../../api/suggestions'
import { useStore } from '../../store/useStore'
import clsx from 'clsx'

interface Panel5DecisionProps {
  suggestion: Suggestion
}

function useCountdown(expiresAt: string | null) {
  const [remaining, setRemaining] = useState(0)

  useEffect(() => {
    if (!expiresAt) return
    const expiry = new Date(expiresAt).getTime()
    const tick = () => {
      const diff = Math.max(0, Math.floor((expiry - Date.now()) / 1000))
      setRemaining(diff)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [expiresAt])

  const m = Math.floor(remaining / 60)
  const s = remaining % 60
  return { remaining, label: `${m}:${s.toString().padStart(2, '0')}` }
}

export function Panel5Decision({ suggestion }: Panel5DecisionProps) {
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<'YES' | 'NO' | null>(null)
  const [error, setError] = useState('')
  const { removeSuggestion } = useStore()
  const { remaining, label } = useCountdown(suggestion.expires_at)

  const entry = (suggestion.entry_price_low + suggestion.entry_price_high) / 2
  const expired = remaining === 0 && !!suggestion.expires_at
  const disabled = submitting || !!result || expired

  async function decide(decision: 'YES' | 'NO') {
    setSubmitting(true)
    setError('')
    try {
      await suggestionsApi.decide(suggestion.id, decision)
      setResult(decision)
      setTimeout(() => removeSuggestion(suggestion.id), 2000)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(msg || 'Failed to submit decision')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="border-t border-border bg-card">
      {/* Summary bar */}
      <div className="px-4 py-2 border-b border-border text-xs flex flex-wrap items-center gap-x-6 gap-y-1 text-muted">
        <span>
          <span className="font-bold text-text">{suggestion.symbol}</span>
          {' '}
          <span className={suggestion.direction === 'LONG' ? 'text-bull font-bold' : 'text-bear font-bold'}>
            {suggestion.direction}
          </span>
          {' '}at{' '}
          <span className="text-info font-semibold">₹{suggestion.entry_price_low}–{suggestion.entry_price_high}</span>
        </span>
        <span>SL <span className="text-bear font-semibold">₹{suggestion.stop_loss}</span></span>
        <span>T1 <span className="text-bull font-semibold">₹{suggestion.target_1}</span></span>
        {suggestion.target_2 && <span>T2 <span className="text-bull font-semibold">₹{suggestion.target_2}</span></span>}
        <span>Confidence <span className={clsx('font-bold', suggestion.confidence_score >= 80 ? 'text-bull' : 'text-amber')}>{suggestion.confidence_score}/100</span></span>
        <span>Win Rate <span className="text-bull font-semibold">{Math.round((suggestion.historical_win_rate ?? 0.67) * 100)}%</span></span>
        <span>R:R <span className={clsx('font-semibold', (suggestion.rr_ratio ?? 0) >= 2 ? 'text-bull' : 'text-amber')}>1:{suggestion.rr_ratio?.toFixed(1)}</span></span>
        <span>Risk <span className="text-bear font-semibold">₹{suggestion.risk_amount?.toFixed(0)} ({((suggestion.risk_pct ?? 0) * 100).toFixed(1)}%)</span></span>
        {/* Countdown */}
        {remaining > 0 && (
          <span className={clsx('flex items-center gap-1', remaining < 120 ? 'text-bear' : 'text-amber')}>
            <Clock size={10} />
            Valid for {label}
          </span>
        )}
        {expired && (
          <span className="flex items-center gap-1 text-bear">
            <AlertTriangle size={10} /> EXPIRED
          </span>
        )}
      </div>

      {/* Decision buttons */}
      <div className="px-4 py-3 flex items-center gap-4">
        <AnimatePresence mode="wait">
          {result === 'YES' && (
            <motion.div
              key="yes-done"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center gap-2 text-bull font-bold"
            >
              <CheckCircle2 size={20} /> Trade submitted for execution
            </motion.div>
          )}
          {result === 'NO' && (
            <motion.div
              key="no-done"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center gap-2 text-muted font-bold"
            >
              <XCircle size={20} /> Setup skipped
            </motion.div>
          )}
          {!result && (
            <motion.div key="buttons" className="flex items-center gap-4 flex-1">
              {/* YES */}
              <motion.button
                whileHover={disabled ? {} : { scale: 1.02 }}
                whileTap={disabled ? {} : { scale: 0.98 }}
                onClick={() => !disabled && decide('YES')}
                disabled={disabled}
                className={clsx(
                  'flex-1 flex items-center justify-center gap-2 py-3 rounded-lg font-bold text-base transition-all',
                  disabled
                    ? 'opacity-40 cursor-not-allowed bg-border text-muted'
                    : 'bg-bull/10 hover:bg-bull/20 text-bull border-2 border-bull glow-bull'
                )}
              >
                <CheckCircle2 size={18} />
                {submitting ? 'Submitting…' : '✅  YES — EXECUTE TRADE'}
              </motion.button>

              {/* NO */}
              <motion.button
                whileHover={disabled ? {} : { scale: 1.02 }}
                whileTap={disabled ? {} : { scale: 0.98 }}
                onClick={() => !disabled && decide('NO')}
                disabled={disabled}
                className={clsx(
                  'flex-1 flex items-center justify-center gap-2 py-3 rounded-lg font-bold text-base transition-all',
                  disabled
                    ? 'opacity-40 cursor-not-allowed bg-border text-muted'
                    : 'bg-bear/10 hover:bg-bear/20 text-bear border-2 border-bear'
                )}
              >
                <XCircle size={18} />
                ❌  NO — SKIP SETUP
              </motion.button>
            </motion.div>
          )}
        </AnimatePresence>

        {error && (
          <span className="text-bear text-xs">{error}</span>
        )}
      </div>
    </div>
  )
}
