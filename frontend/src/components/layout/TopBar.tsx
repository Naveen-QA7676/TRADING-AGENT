import { useStore } from '../../store/useStore'
import { AnimatedNumber } from '../ui/AnimatedNumber'
import clsx from 'clsx'

export function TopBar() {
  const { dailyPnL, marketRegime, vixLevel, fiiFlow } = useStore()

  const pnl = dailyPnL?.total_pnl ?? 0
  const pnlPositive = pnl >= 0

  const regimeColor: Record<string, string> = {
    TRENDING_UP:   'text-bull',
    TRENDING_DOWN: 'text-bear',
    RANGE_BOUND:   'text-amber',
    VOLATILE:      'text-amber',
    COMPRESSING:   'text-muted',
    UNKNOWN:       'text-muted',
  }

  const regimeLabel: Record<string, string> = {
    TRENDING_UP:   'Trending Up',
    TRENDING_DOWN: 'Trending Down',
    RANGE_BOUND:   'Range Bound',
    VOLATILE:      'Volatile',
    COMPRESSING:   'Compressing',
    UNKNOWN:       '—',
  }

  return (
    <header className="flex items-center justify-between px-4 py-2 border-b border-border bg-card shrink-0 h-12">
      <div className="flex items-center gap-6 text-xs">
        {/* Regime */}
        <div className="flex items-center gap-1.5">
          <span className="text-muted">Regime</span>
          <span className={clsx('font-bold', regimeColor[marketRegime] ?? 'text-muted')}>
            {regimeLabel[marketRegime] ?? '—'}
          </span>
        </div>

        {/* VIX */}
        <div className="flex items-center gap-1.5 hidden sm:flex">
          <span className="text-muted">VIX</span>
          <span className={clsx('font-bold', vixLevel > 20 ? 'text-bear' : vixLevel > 15 ? 'text-amber' : 'text-bull')}>
            {vixLevel > 0 ? vixLevel.toFixed(1) : '—'}
          </span>
        </div>

        {/* FII */}
        <div className="flex items-center gap-1.5 hidden md:flex">
          <span className="text-muted">FII</span>
          <span className={clsx('font-bold', fiiFlow >= 0 ? 'text-bull' : 'text-bear')}>
            {fiiFlow !== 0 ? `₹${Math.abs(fiiFlow).toFixed(0)}Cr ${fiiFlow >= 0 ? 'BUY' : 'SELL'}` : '—'}
          </span>
        </div>
      </div>

      {/* Daily P&L */}
      <div className="flex items-center gap-2 text-xs">
        <span className="text-muted hidden sm:block">Today</span>
        <span className={clsx('font-bold text-sm', pnlPositive ? 'text-bull' : 'text-bear')}>
          {pnlPositive ? '+' : ''}
          <AnimatedNumber value={pnl} prefix="₹" decimals={0} />
        </span>
        {dailyPnL && (
          <span className="text-muted">
            ({dailyPnL.win_count}W / {dailyPnL.loss_count}L)
          </span>
        )}
      </div>
    </header>
  )
}
