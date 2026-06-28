import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, TrendingUp, TrendingDown, AlertCircle, CheckCircle2 } from 'lucide-react'
import {
  createChart, ColorType, CrosshairMode,
  type IChartApi, type ISeriesApi, type CandlestickData,
} from 'lightweight-charts'
import { terminalApi, type LiveQuote, type Margins } from '../api/terminal'
import { SectionTitle } from '../components/ui/Card'
import { AnimatedNumber } from '../components/ui/AnimatedNumber'
import clsx from 'clsx'

const INTERVALS = [
  { label: '1m',  kite: 'minute'   },
  { label: '3m',  kite: '3minute'  },
  { label: '5m',  kite: '5minute'  },
  { label: '15m', kite: '15minute' },
  { label: '30m', kite: '30minute' },
  { label: '1H',  kite: '60minute' },
  { label: '1D',  kite: 'day'      },
]

const PRODUCT_TYPES = ['MIS', 'CNC', 'NRML'] as const
const ORDER_TYPES   = ['LIMIT', 'MARKET', 'SL', 'SL-M'] as const

function buildMockDepth(ltp: number) {
  const asks = Array.from({ length: 5 }, (_, i) => ({
    price: +(ltp + (i + 1) * 0.2).toFixed(2),
    quantity: Math.floor(Math.random() * 400 + 80),
    orders: Math.floor(Math.random() * 5 + 1),
  }))
  const bids = Array.from({ length: 5 }, (_, i) => ({
    price: +(ltp - (i + 1) * 0.2).toFixed(2),
    quantity: Math.floor(Math.random() * 600 + 100),
    orders: Math.floor(Math.random() * 8 + 1),
  }))
  return { buy: bids, sell: asks }
}

function buildMockCandles(center: number, count = 120) {
  const bars = []
  let price = center * 0.97
  const now = Math.floor(Date.now() / 1000)
  for (let i = count; i >= 0; i--) {
    const o = price
    const c = o + (Math.random() - 0.47) * center * 0.003
    bars.push({
      time: now - i * 300,
      open: +o.toFixed(2), high: +(Math.max(o, c) + Math.random() * center * 0.002).toFixed(2),
      low:  +(Math.min(o, c) - Math.random() * center * 0.002).toFixed(2), close: +c.toFixed(2),
    })
    price = c
  }
  return bars
}

// ─── Order Book ───────────────────────────────────────────────────────────────

function OrderBook({ quote }: { quote: LiveQuote | null }) {
  if (!quote) return <div className="text-muted text-xs text-center py-8">Search a symbol</div>

  const depth = quote.depth ?? buildMockDepth(quote.ltp)
  const asks = [...(depth.sell ?? [])].reverse()
  const bids = depth.buy ?? []
  const maxQty = Math.max(...[...asks, ...bids].map((d) => d.quantity))

  const Row = ({ side, price, qty }: { side: 'ask' | 'bid'; price: number; qty: number }) => (
    <div className="relative flex items-center justify-between px-2 py-0.5 text-[11px]">
      <div
        className="absolute inset-y-0 right-0"
        style={{
          width: `${(qty / maxQty) * 100}%`,
          backgroundColor: side === 'ask' ? 'rgba(255,51,85,0.08)' : 'rgba(0,255,136,0.08)',
        }}
      />
      <span className={side === 'ask' ? 'text-bear relative z-10' : 'text-bull relative z-10'}>
        {price.toFixed(2)}
      </span>
      <span className="text-muted relative z-10">{qty.toLocaleString('en-IN')}</span>
    </div>
  )

  const totalBid = bids.reduce((s, d) => s + d.quantity, 0)
  const totalAsk = asks.reduce((s, d) => s + d.quantity, 0)
  const bidAskRatio = totalAsk > 0 ? (totalBid / totalAsk).toFixed(2) : '—'

  return (
    <div className="text-xs">
      <div className="text-[10px] text-bear uppercase tracking-wide px-2 py-1 border-b border-border">SELL (Ask)</div>
      {asks.map((d, i) => <Row key={i} side="ask" price={d.price} qty={d.quantity} />)}

      <div className="flex items-center justify-center gap-3 py-1.5 border-y border-border my-0.5 bg-card">
        <span className="text-text font-bold">{quote.ltp.toFixed(2)}</span>
        <span className={clsx('text-xs', quote.change >= 0 ? 'text-bull' : 'text-bear')}>
          {quote.change >= 0 ? '+' : ''}{quote.change.toFixed(2)}%
        </span>
      </div>

      <div className="text-[10px] text-bull uppercase tracking-wide px-2 py-1 border-b border-border">BUY (Bid)</div>
      {bids.map((d, i) => <Row key={i} side="bid" price={d.price} qty={d.quantity} />)}

      <div className="px-2 pt-2 space-y-1 text-[11px] border-t border-border mt-1">
        <div className="flex justify-between"><span className="text-muted">Bid/Ask</span><span className="text-text">{bidAskRatio}×</span></div>
        <div className="flex justify-between">
          <span className="text-muted">Spread</span>
          <span className="text-text">₹{asks.length && bids.length ? Math.abs(asks[0].price - bids[0].price).toFixed(2) : '—'}</span>
        </div>
        <div className="flex justify-between"><span className="text-muted">Volume</span><span className="text-text">{(quote.volume / 1000).toFixed(1)}K</span></div>
      </div>
    </div>
  )
}

// ─── AI Recommendation sidebar ───────────────────────────────────────────────

function AIReco({ symbol: _symbol }: { symbol: string }) {
  return (
    <div className="border-t border-border mt-2 pt-2 text-xs space-y-1">
      <div className="text-[10px] text-info uppercase tracking-widest">AI Recommendation</div>
      <div className="text-muted text-[11px]">Based on last signal:</div>
      <div className="text-bull text-[11px]">Enter: 1645–1652</div>
      <div className="text-bear text-[11px]">SL: 1628</div>
      <div className="text-bull text-[11px]">Target: 1692 / 1720</div>
      <div className="text-amber text-[11px] pt-1">Confidence: 88/100</div>
    </div>
  )
}

// ─── Place Order panel ────────────────────────────────────────────────────────

function PlaceOrderPanel({ symbol, ltp, margins }: { symbol: string; ltp: number; margins: Margins | null }) {
  const [product, setProduct] = useState<typeof PRODUCT_TYPES[number]>('MIS')
  const [orderType, setOrderType] = useState<typeof ORDER_TYPES[number]>('LIMIT')
  const [qty, setQty] = useState(1)
  const [price, setPrice] = useState(ltp)
  const [trigger, setTrigger] = useState(0)
  const [status, setStatus] = useState<'idle' | 'loading' | 'ok' | 'err'>('idle')
  const [msg, setMsg] = useState('')

  // Keep price updated when ltp changes (for LIMIT default)
  useEffect(() => { if (orderType === 'LIMIT') setPrice(ltp) }, [ltp, orderType])

  const requiredMargin = qty * price * (product === 'MIS' ? 0.25 : 1)

  async function submit(side: 'BUY' | 'SELL') {
    setStatus('loading')
    setMsg('')
    try {
      await terminalApi.placeOrder({
        symbol,
        transaction_type: side,
        quantity: qty,
        price: orderType === 'MARKET' ? 0 : price,
        trigger_price: trigger || undefined,
        product,
        order_type: orderType,
      })
      setStatus('ok')
      setMsg(`${side} order placed`)
      setTimeout(() => setStatus('idle'), 3000)
    } catch (e: unknown) {
      setStatus('err')
      setMsg(e instanceof Error ? e.message : 'Order failed')
      setTimeout(() => setStatus('idle'), 4000)
    }
  }

  const [slPrice, setSlPrice] = useState(0)
  const [tgtPrice, setTgtPrice] = useState(0)

  async function submitGTT() {
    if (!slPrice || !tgtPrice) return
    setStatus('loading')
    try {
      await terminalApi.setGTT({ symbol, direction: 'LONG', quantity: qty, stop_loss: slPrice, target: tgtPrice, ltp })
      setStatus('ok')
      setMsg('GTT set')
      setTimeout(() => setStatus('idle'), 3000)
    } catch (e: unknown) {
      setStatus('err')
      setMsg(e instanceof Error ? e.message : 'GTT failed')
      setTimeout(() => setStatus('idle'), 4000)
    }
  }

  return (
    <div className="space-y-3 text-xs">
      {/* Controls row */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="flex rounded overflow-hidden border border-border">
          {PRODUCT_TYPES.map((p) => (
            <button key={p} onClick={() => setProduct(p)}
              className={clsx('px-2 py-1 text-[11px]', product === p ? 'bg-info/20 text-info' : 'text-muted hover:text-text')}>
              {p}
            </button>
          ))}
        </div>
        <div className="flex rounded overflow-hidden border border-border">
          {ORDER_TYPES.map((t) => (
            <button key={t} onClick={() => setOrderType(t)}
              className={clsx('px-2 py-1 text-[11px]', orderType === t ? 'bg-info/20 text-info' : 'text-muted hover:text-text')}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Inputs */}
      <div className="grid grid-cols-3 gap-2">
        <label className="space-y-1">
          <span className="text-muted text-[10px]">Qty</span>
          <input type="number" min={1} value={qty} onChange={(e) => setQty(+e.target.value)}
            className="w-full bg-bg border border-border rounded px-2 py-1 text-text text-xs focus:outline-none focus:border-info/50" />
        </label>
        {orderType !== 'MARKET' && (
          <label className="space-y-1">
            <span className="text-muted text-[10px]">Price ₹</span>
            <input type="number" step="0.05" value={price} onChange={(e) => setPrice(+e.target.value)}
              className="w-full bg-bg border border-border rounded px-2 py-1 text-text text-xs focus:outline-none focus:border-info/50" />
          </label>
        )}
        {(orderType === 'SL' || orderType === 'SL-M') && (
          <label className="space-y-1">
            <span className="text-muted text-[10px]">Trigger ₹</span>
            <input type="number" step="0.05" value={trigger} onChange={(e) => setTrigger(+e.target.value)}
              className="w-full bg-bg border border-border rounded px-2 py-1 text-text text-xs focus:outline-none focus:border-info/50" />
          </label>
        )}
      </div>

      {/* BUY / SELL */}
      <div className="flex gap-2">
        <motion.button whileTap={{ scale: 0.97 }} onClick={() => submit('BUY')} disabled={status === 'loading'}
          className="flex-1 py-2 rounded font-bold bg-bull/10 hover:bg-bull/20 text-bull border border-bull/30 transition-colors disabled:opacity-40">
          BUY
        </motion.button>
        <motion.button whileTap={{ scale: 0.97 }} onClick={() => submit('SELL')} disabled={status === 'loading'}
          className="flex-1 py-2 rounded font-bold bg-bear/10 hover:bg-bear/20 text-bear border border-bear/30 transition-colors disabled:opacity-40">
          SELL
        </motion.button>
      </div>

      {/* Margin info */}
      <div className="flex justify-between text-[11px] text-muted">
        <span>Margin required: <span className="text-text">₹{requiredMargin.toFixed(0)}</span></span>
        {margins && <span>Available: <span className="text-bull">₹{margins.available.toLocaleString('en-IN')}</span></span>}
      </div>

      {/* GTT */}
      <div className="border-t border-border pt-2 space-y-2">
        <div className="text-[10px] text-amber uppercase tracking-wide">GTT Orders (Stop + Target)</div>
        <div className="flex items-center gap-2">
          <label className="flex-1 space-y-1">
            <span className="text-muted text-[10px]">SL ₹</span>
            <input type="number" step="0.05" value={slPrice || ''} onChange={(e) => setSlPrice(+e.target.value)}
              placeholder={ltp ? (ltp * 0.99).toFixed(2) : ''}
              className="w-full bg-bg border border-border rounded px-2 py-1 text-bear text-xs focus:outline-none focus:border-bear/50" />
          </label>
          <label className="flex-1 space-y-1">
            <span className="text-muted text-[10px]">Target ₹</span>
            <input type="number" step="0.05" value={tgtPrice || ''} onChange={(e) => setTgtPrice(+e.target.value)}
              placeholder={ltp ? (ltp * 1.02).toFixed(2) : ''}
              className="w-full bg-bg border border-border rounded px-2 py-1 text-bull text-xs focus:outline-none focus:border-bull/50" />
          </label>
          <button onClick={submitGTT} disabled={!slPrice || !tgtPrice || status === 'loading'}
            className="mt-4 px-3 py-1 rounded border border-amber/30 text-amber hover:bg-amber/10 text-[11px] transition-colors disabled:opacity-40">
            SET GTT
          </button>
        </div>
      </div>

      {/* Status */}
      <AnimatePresence>
        {status !== 'idle' && (
          <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className={clsx('flex items-center gap-2 text-[11px] px-2 py-1.5 rounded border',
              status === 'ok'  ? 'text-bull border-bull/30 bg-bull/5' :
              status === 'err' ? 'text-bear border-bear/30 bg-bear/5' : 'text-muted border-border')}>
            {status === 'ok' ? <CheckCircle2 size={12} /> : status === 'err' ? <AlertCircle size={12} /> : null}
            {msg || 'Placing order…'}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function Terminal() {
  const [symbol, setSymbol] = useState('HDFCBANK')
  const [input, setInput]   = useState('HDFCBANK')
  const [quote, setQuote]   = useState<LiveQuote | null>(null)
  const [margins, setMargins] = useState<Margins | null>(null)
  const [tfInterval, setTfInterval] = useState('15minute')
  const chartRef  = useRef<HTMLDivElement>(null)
  const chartInst = useRef<IChartApi | null>(null)
  const candleSeries = useRef<ISeriesApi<'Candlestick'> | null>(null)

  // Fetch quote every 2s
  const fetchQuote = useCallback(async () => {
    try {
      const q = await terminalApi.getQuote(symbol)
      setQuote(q)
    } catch {
      // mock while backend is offline
      setQuote({
        symbol,
        ltp: 1648.40,
        ohlc: { open: 1640, high: 1658, low: 1635, close: 1648 },
        volume: 1240000,
        change: +0.42,
        depth: buildMockDepth(1648.4),
      })
    }
  }, [symbol])

  useEffect(() => {
    fetchQuote()
    const id = window.setInterval(fetchQuote, 2000)
    return () => window.clearInterval(id)
  }, [fetchQuote])

  useEffect(() => {
    terminalApi.getMargins().then(setMargins).catch(() => {})
  }, [])

  // Chart
  useEffect(() => {
    if (!chartRef.current) return
    const chart = createChart(chartRef.current, {
      width: chartRef.current.clientWidth,
      height: chartRef.current.clientHeight,
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
    candleSeries.current = series
    series.setData(buildMockCandles(1648) as CandlestickData[])

    const ro = new ResizeObserver(() => {
      if (chartRef.current) chart.applyOptions({ width: chartRef.current.clientWidth, height: chartRef.current.clientHeight })
    })
    ro.observe(chartRef.current)
    return () => { ro.disconnect(); chart.remove() }
  }, [symbol])

  // Reload candles when tfInterval changes
  useEffect(() => {
    terminalApi.getCandles(symbol, tfInterval, 5)
      .then((data) => {
        const bars = (data?.candles ?? buildMockCandles(quote?.ltp ?? 1648)).map((c: number[]) => ({
          time: Math.floor(new Date(c[0]).getTime() / 1000),
          open: c[1], high: c[2], low: c[3], close: c[4],
        }))
        candleSeries.current?.setData(bars)
      })
      .catch(() => candleSeries.current?.setData(buildMockCandles(quote?.ltp ?? 1648) as CandlestickData[]))
  }, [tfInterval, symbol])

  function search() {
    const sym = input.trim().toUpperCase()
    if (sym) setSymbol(sym)
  }

  const ltp = quote?.ltp ?? 1648.4

  return (
    <div className="flex flex-col h-full -m-4">
      {/* Search bar */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-border bg-card shrink-0">
        <div className="flex items-center gap-2 bg-bg border border-border rounded-md px-3 py-1.5">
          <Search size={14} className="text-muted" />
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search()}
            placeholder="Search symbol…"
            className="bg-transparent text-text text-sm focus:outline-none w-32"
          />
          <button onClick={search} className="text-info text-xs hover:underline">Go</button>
        </div>
        {quote && (
          <div className="flex items-center gap-4 text-sm">
            <span className="font-bold text-text">{quote.symbol}</span>
            <AnimatedNumber value={quote.ltp} prefix="₹" decimals={2} className="font-bold text-text" />
            <span className={clsx('font-semibold flex items-center gap-1', quote.change >= 0 ? 'text-bull' : 'text-bear')}>
              {quote.change >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              {quote.change >= 0 ? '+' : ''}{quote.change.toFixed(2)}%
            </span>
            <span className="text-muted text-xs">O:{quote.ohlc?.open} H:{quote.ohlc?.high} L:{quote.ohlc?.low}</span>
          </div>
        )}
      </div>

      {/* Main layout */}
      <div className="flex flex-1 min-h-0 divide-x divide-border">

        {/* Left: Order book + AI reco */}
        <div className="w-48 shrink-0 flex flex-col overflow-y-auto">
          <div className="p-2 border-b border-border">
            <SectionTitle>Order Book</SectionTitle>
          </div>
          <div className="flex-1 overflow-y-auto">
            <OrderBook quote={quote} />
            {symbol && <AIReco symbol={symbol} />}
          </div>
        </div>

        {/* Center: Chart */}
        <div className="flex flex-col flex-1 min-w-0">
          {/* TF row */}
          <div className="flex items-center gap-1 px-3 py-1.5 border-b border-border bg-card/50 shrink-0 overflow-x-auto">
            {INTERVALS.map((iv) => (
              <button key={iv.kite} onClick={() => setTfInterval(iv.kite)}
                className={clsx('px-2 py-0.5 rounded text-xs whitespace-nowrap', tfInterval === iv.kite ? 'bg-info/20 text-info border border-info/30' : 'text-muted hover:text-text')}>
                {iv.label}
              </button>
            ))}
          </div>
          <div ref={chartRef} className="flex-1 min-h-0" />
        </div>

        {/* Right: Place order */}
        <div className="w-64 shrink-0 flex flex-col overflow-y-auto">
          <div className="p-3 border-b border-border">
            <SectionTitle>Place Order</SectionTitle>
          </div>
          <div className="p-3 flex-1">
            <PlaceOrderPanel symbol={symbol} ltp={ltp} margins={margins} />
          </div>
        </div>
      </div>
    </div>
  )
}
