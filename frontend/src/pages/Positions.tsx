import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Briefcase, TrendingUp, TrendingDown, AlertTriangle, CheckCircle2, Minus } from 'lucide-react'
import { useStore } from '../store/useStore'
import { positionsApi, type Position } from '../api/positions'
import { AnimatedNumber } from '../components/ui/AnimatedNumber'
import { Card, CardHeader, SectionTitle } from '../components/ui/Card'
import clsx from 'clsx'

// Demo positions when none are live
const DEMO_POSITIONS: Position[] = [
  {
    id: 1, symbol: 'HDFCBANK', direction: 'LONG', quantity: 61,
    avg_price: 1648, current_price: 1673, unrealized_pnl: 1525, unrealized_pnl_pct: 1.52,
    stop_loss: 1628, target_1: 1692, target_2: 1720, mae: 8, mfe: 27,
    entry_time: new Date(Date.now() - 22 * 60 * 1000).toISOString(),
  },
  {
    id: 2, symbol: 'INFY', direction: 'LONG', quantity: 28,
    avg_price: 1842, current_price: 1891, unrealized_pnl: 1372, unrealized_pnl_pct: 2.66,
    stop_loss: 1820, target_1: 1920, target_2: 1960, mae: 5, mfe: 52,
    entry_time: new Date(Date.now() - 48 * 60 * 1000).toISOString(),
  },
]

function minutes(isoStr: string) {
  return Math.floor((Date.now() - new Date(isoStr).getTime()) / 60000)
}

function PositionCard({ pos, onAction }: { pos: Position; onAction: () => void }) {
  const [loading, setLoading] = useState<string | null>(null)
  const [msg, setMsg] = useState('')

  const range = pos.target_2
    ? pos.target_2 - pos.stop_loss
    : pos.target_1 - pos.stop_loss
  const currentOffset = pos.current_price - pos.stop_loss
  const pctProgress = Math.min(100, Math.max(0, (currentOffset / range) * 100))
  const t1Pct = ((pos.target_1 - pos.stop_loss) / range) * 100
  const entryPct = ((pos.avg_price - pos.stop_loss) / range) * 100

  const distToSL = pos.current_price - pos.stop_loss
  const distToT1 = pos.target_1 - pos.current_price
  const isWinning = pos.unrealized_pnl >= 0

  async function action(type: 'sl-entry' | 'partial' | 'exit') {
    setLoading(type)
    setMsg('')
    try {
      if (type === 'sl-entry') {
        await positionsApi.moveSlToEntry(pos.id)
        setMsg('SL moved to entry')
      } else if (type === 'partial') {
        const half = Math.floor(pos.quantity / 2)
        await positionsApi.partialExit(pos.id, half)
        setMsg(`Partial exit: ${half} shares`)
      } else {
        await positionsApi.partialExit(pos.id, pos.quantity)
        setMsg('Exit submitted')
      }
      setTimeout(() => { setMsg(''); onAction() }, 3000)
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : 'Action failed')
    } finally {
      setLoading(null)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        'rounded-lg border bg-card p-4 space-y-3',
        isWinning ? 'border-bull/20' : 'border-bear/20'
      )}
    >
      {/* Header row */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-text text-base">{pos.symbol}</span>
            <span className={clsx('px-2 py-0.5 rounded text-xs font-bold',
              pos.direction === 'LONG' ? 'bg-bull/10 text-bull' : 'bg-bear/10 text-bear')}>
              {pos.direction}
            </span>
            <span className="text-muted text-xs">{pos.quantity} shares</span>
          </div>
          <div className="text-xs text-muted mt-0.5">
            Avg ₹{pos.avg_price} · {minutes(pos.entry_time)} min in trade
          </div>
        </div>
        <div className="text-right">
          <div className={clsx('text-lg font-bold', isWinning ? 'text-bull' : 'text-bear')}>
            {isWinning ? '+' : ''}
            <AnimatedNumber value={pos.unrealized_pnl} prefix="₹" decimals={0} />
          </div>
          <div className={clsx('text-xs', isWinning ? 'text-bull' : 'text-bear')}>
            {isWinning ? '+' : ''}{pos.unrealized_pnl_pct.toFixed(2)}%
          </div>
        </div>
      </div>

      {/* Live price */}
      <div className="flex items-center gap-4 text-sm">
        <div>
          <span className="text-muted text-xs">Now </span>
          <AnimatedNumber value={pos.current_price} prefix="₹" decimals={2} className="font-bold text-text" />
        </div>
        <div className="text-xs text-muted">
          MAE: −₹{pos.mae} · MFE: +₹{pos.mfe}
        </div>
      </div>

      {/* Progress bar: SL → Entry → Current → T1 → T2 */}
      <div className="space-y-1">
        <div className="relative h-3 rounded-full bg-border overflow-visible">
          {/* Filled portion */}
          <motion.div
            className="absolute inset-y-0 left-0 rounded-full"
            style={{ backgroundColor: isWinning ? '#00FF88' : '#FF3355' }}
            initial={{ width: 0 }}
            animate={{ width: `${pctProgress}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          />
          {/* Entry marker */}
          <div className="absolute top-1/2 -translate-y-1/2 w-0.5 h-5 bg-info rounded-full"
            style={{ left: `${Math.min(99, entryPct)}%` }} />
          {/* T1 marker */}
          <div className="absolute top-1/2 -translate-y-1/2 w-0.5 h-5 bg-bull/70 rounded-full"
            style={{ left: `${Math.min(99, t1Pct)}%` }} />
        </div>
        <div className="flex justify-between text-[10px] text-muted">
          <span className="text-bear">SL ₹{pos.stop_loss}</span>
          <span className="text-info">Avg ₹{pos.avg_price}</span>
          <span className="text-bull">T1 ₹{pos.target_1}</span>
          {pos.target_2 && <span className="text-bull">T2 ₹{pos.target_2}</span>}
        </div>
      </div>

      {/* Distance callouts */}
      <div className="flex gap-4 text-xs">
        <div className={clsx(distToSL < pos.avg_price * 0.005 ? 'text-bear' : 'text-muted')}>
          To SL: <span className="font-semibold">₹{distToSL.toFixed(2)} below</span>
          {distToSL < pos.avg_price * 0.005 && <span className="text-bear ml-1">⚠ tight</span>}
        </div>
        <div className={clsx(distToT1 < pos.avg_price * 0.01 ? 'text-amber' : 'text-muted')}>
          To T1: <span className="font-semibold">₹{distToT1.toFixed(2)} above</span>
          {distToT1 < pos.avg_price * 0.01 && <span className="text-amber ml-1">● close</span>}
        </div>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2 pt-1">
        <button onClick={() => action('partial')} disabled={!!loading}
          className="flex-1 py-1.5 rounded text-xs border border-amber/30 text-amber hover:bg-amber/10 transition-colors disabled:opacity-40">
          {loading === 'partial' ? '…' : 'Partial Exit 50%'}
        </button>
        <button onClick={() => action('sl-entry')} disabled={!!loading || pos.avg_price <= pos.stop_loss}
          className="flex-1 py-1.5 rounded text-xs border border-info/30 text-info hover:bg-info/10 transition-colors disabled:opacity-40">
          {loading === 'sl-entry' ? '…' : 'Move SL to Entry'}
        </button>
        <button onClick={() => action('exit')} disabled={!!loading}
          className="flex-1 py-1.5 rounded text-xs border border-bear/30 text-bear hover:bg-bear/10 transition-colors disabled:opacity-40">
          {loading === 'exit' ? '…' : 'Exit at Market'}
        </button>
      </div>

      {msg && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          className="text-[11px] text-bull flex items-center gap-1">
          <CheckCircle2 size={11} /> {msg}
        </motion.div>
      )}

      {/* AI update bar */}
      <div className="bg-info/5 border border-info/20 rounded px-3 py-2 text-xs text-info">
        <span className="text-muted mr-1">AI:</span>
        {pos.symbol} holding above VWAP. CVD +52,400 still rising. Setup intact.
        {distToT1 < pos.avg_price * 0.01 ? ' T1 approaching — consider locking partial profits.' : ' Hold for T1.'}
      </div>
    </motion.div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function Positions() {
  const livePositions = useStore((s) => s.positions)
  const dailyPnL      = useStore((s) => s.dailyPnL)
  const [refresh, setRefresh] = useState(0)

  const positions = livePositions.length > 0 ? livePositions : DEMO_POSITIONS
  const isDemo    = livePositions.length === 0

  const totalPnL  = positions.reduce((s, p) => s + p.unrealized_pnl, 0)
  const totalCap  = positions.reduce((s, p) => s + p.avg_price * p.quantity, 0)
  const totalPnLPct = totalCap > 0 ? (totalPnL / totalCap) * 100 : 0

  return (
    <div className="space-y-4 max-w-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold flex items-center gap-2">
            <Briefcase size={18} className="text-info" />
            Open Positions
            {isDemo && <span className="text-xs text-amber/60 font-normal italic">(demo)</span>}
          </h1>
          <p className="text-xs text-muted">{positions.length} open · live P&amp;L tracking</p>
        </div>
        {/* Summary */}
        <div className="text-right">
          <div className={clsx('text-xl font-bold', totalPnL >= 0 ? 'text-bull' : 'text-bear')}>
            {totalPnL >= 0 ? '+' : ''}
            <AnimatedNumber value={totalPnL} prefix="₹" decimals={0} />
          </div>
          <div className={clsx('text-xs', totalPnL >= 0 ? 'text-bull' : 'text-bear')}>
            {totalPnL >= 0 ? '+' : ''}{totalPnLPct.toFixed(2)}% unrealized
          </div>
          {dailyPnL && (
            <div className="text-xs text-muted mt-0.5">
              Today net: <span className={dailyPnL.total_pnl >= 0 ? 'text-bull' : 'text-bear'}>
                ₹{dailyPnL.total_pnl.toFixed(0)}
              </span>
              {' · '}{dailyPnL.win_count}W / {dailyPnL.loss_count}L
            </div>
          )}
        </div>
      </div>

      {/* Daily P&L stats strip */}
      {dailyPnL && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: 'Realized P&L', value: `₹${dailyPnL.gross_pnl?.toFixed(0) ?? 0}`, color: 'text-bull' },
            { label: 'Charges',      value: `₹${dailyPnL.charges?.toFixed(0) ?? 0}`,  color: 'text-bear' },
            { label: 'Net P&L',      value: `₹${dailyPnL.total_pnl?.toFixed(0) ?? 0}`, color: dailyPnL.total_pnl >= 0 ? 'text-bull' : 'text-bear' },
            { label: 'Trades',       value: `${dailyPnL.trade_count}`,                 color: 'text-text' },
          ].map((s) => (
            <Card key={s.label} className="text-center py-2">
              <div className="text-[10px] text-muted mb-1">{s.label}</div>
              <div className={clsx('font-bold text-sm', s.color)}>{s.value}</div>
            </Card>
          ))}
        </div>
      )}

      {/* Position cards */}
      {positions.length > 0 ? (
        <div className="space-y-4">
          <AnimatePresence>
            {positions.map((pos) => (
              <PositionCard key={pos.id} pos={pos} onAction={() => setRefresh((r) => r + 1)} />
            ))}
          </AnimatePresence>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center h-48 text-muted gap-2">
          <Briefcase size={32} className="text-muted/30" />
          <p className="text-sm">No open positions</p>
          <p className="text-xs">Signals will appear when the scanner finds setups</p>
        </div>
      )}

      {/* Emergency squareoff */}
      {positions.length > 0 && (
        <div className="flex justify-end pt-2">
          <button
            onClick={() => { if (confirm('Square off ALL positions at market price?')) positionsApi.squareoffAll() }}
            className="flex items-center gap-2 px-4 py-2 rounded border border-bear text-bear hover:bg-bear/10 text-xs font-bold transition-colors"
          >
            <AlertTriangle size={12} />
            EMERGENCY SQUARE OFF ALL
          </button>
        </div>
      )}
    </div>
  )
}
