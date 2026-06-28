import { useEffect, useRef, useState } from 'react'
import {
  createChart,
  ColorType,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
} from 'lightweight-charts'
import type { Suggestion } from '../../api/suggestions'
import { api } from '../../api/client'

interface Bar {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume?: number
}

const TF = ['1m', '5m', '15m', '1H', 'Daily'] as const
type TFType = typeof TF[number]

interface Panel1ChartProps {
  suggestion: Suggestion
}

export function Panel1Chart({ suggestion }: Panel1ChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const [activeTF, setActiveTF] = useState<TFType>('15m')
  const [indicators, setIndicators] = useState({
    vwap: true, ema20: true, ema50: true, bb: false, rsi: true, volume: true,
  })

  // Fetch OHLCV from backend
  async function loadCandles(tf: TFType) {
    try {
      const res = await api.get<Bar[]>(`/terminal/candles/${suggestion.symbol}`, {
        params: { interval: tf, limit: 200 },
      })
      return res.data
    } catch {
      return generateMockCandles(suggestion.entry_price ?? suggestion.entry_price_low)
    }
  }

  // Mock candles centered around entry price
  function generateMockCandles(center: number): Bar[] {
    const bars: Bar[] = []
    let price = center * 0.985
    const now = Math.floor(Date.now() / 1000)
    for (let i = 80; i >= 0; i--) {
      const o = price
      const change = (Math.random() - 0.48) * center * 0.003
      const c = o + change
      const h = Math.max(o, c) + Math.random() * center * 0.002
      const l = Math.min(o, c) - Math.random() * center * 0.002
      bars.push({ time: now - i * 900, open: o, high: h, low: l, close: c })
      price = c
    }
    return bars
  }

  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
      layout: {
        background: { type: ColorType.Solid, color: '#141824' },
        textColor: '#6B7280',
      },
      grid: {
        vertLines: { color: '#1E2535' },
        horzLines: { color: '#1E2535' },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#1E2535' },
      timeScale: { borderColor: '#1E2535', timeVisible: true },
    })
    chartRef.current = chart

    const candles = chart.addCandlestickSeries({
      upColor: '#00FF88',
      downColor: '#FF3355',
      borderUpColor: '#00FF88',
      borderDownColor: '#FF3355',
      wickUpColor: '#00FF88',
      wickDownColor: '#FF3355',
    })
    candleRef.current = candles

    loadCandles(activeTF).then((bars) => {
      candles.setData(bars as CandlestickData[])

      // Draw key levels as price lines
      const entry = (suggestion.entry_price_low + suggestion.entry_price_high) / 2

      candles.createPriceLine({ price: entry,               color: '#4488FF', lineWidth: 2, lineStyle: 1, axisLabelVisible: true, title: 'Entry' })
      candles.createPriceLine({ price: suggestion.stop_loss, color: '#FF3355', lineWidth: 2, lineStyle: 2, axisLabelVisible: true, title: 'SL' })
      candles.createPriceLine({ price: suggestion.target_1,  color: '#00FF88', lineWidth: 1, lineStyle: 1, axisLabelVisible: true, title: 'T1' })
      if (suggestion.target_2)
        candles.createPriceLine({ price: suggestion.target_2, color: '#00FF88', lineWidth: 1, lineStyle: 1, axisLabelVisible: true, title: 'T2' })
      if (suggestion.invalidation_level)
        candles.createPriceLine({ price: suggestion.invalidation_level, color: '#FFB020', lineWidth: 1, lineStyle: 3, axisLabelVisible: true, title: 'Invalidation' })
    })

    const ro = new ResizeObserver(() => {
      if (containerRef.current)
        chart.applyOptions({ width: containerRef.current.clientWidth, height: containerRef.current.clientHeight })
    })
    ro.observe(containerRef.current)

    return () => {
      ro.disconnect()
      chart.remove()
    }
  }, [suggestion.id])   // re-mount only when suggestion changes

  // Reload candles on TF change
  useEffect(() => {
    if (!candleRef.current) return
    loadCandles(activeTF).then((bars) => {
      candleRef.current?.setData(bars as CandlestickData[])
    })
  }, [activeTF])

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
        {/* Price info */}
        <div className="flex items-center gap-3 text-xs">
          <span className="font-bold text-text text-sm">{suggestion.symbol}</span>
          <span className="text-bull font-semibold">
            ₹{((suggestion.entry_price_low + suggestion.entry_price_high) / 2).toFixed(2)}
          </span>
          <span className="text-muted live-pulse text-bull text-[10px]">● LIVE</span>
        </div>
        {/* TF toggle */}
        <div className="flex items-center gap-1">
          {TF.map((tf) => (
            <button
              key={tf}
              onClick={() => setActiveTF(tf)}
              className={`px-2 py-0.5 rounded text-xs transition-colors ${
                activeTF === tf ? 'bg-info/20 text-info border border-info/30' : 'text-muted hover:text-text'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
        {/* Indicator toggles */}
        <div className="hidden xl:flex items-center gap-2 text-[10px]">
          {Object.entries(indicators).map(([k, v]) => (
            <button
              key={k}
              onClick={() => setIndicators((p) => ({ ...p, [k]: !p[k as keyof typeof p] }))}
              className={`px-1.5 py-0.5 rounded transition-colors uppercase tracking-wide ${
                v ? 'text-info border border-info/30' : 'text-muted border border-border'
              }`}
            >
              {k.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div ref={containerRef} className="flex-1 min-h-0" />

      {/* Level legend */}
      <div className="flex items-center gap-4 px-3 py-1.5 border-t border-border text-[10px] shrink-0 flex-wrap">
        <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-info inline-block" /> Entry ₹{suggestion.entry_price_low}–{suggestion.entry_price_high}</span>
        <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-bear inline-block" /> SL ₹{suggestion.stop_loss}</span>
        <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-bull inline-block" /> T1 ₹{suggestion.target_1}</span>
        {suggestion.target_2 && <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-bull inline-block" /> T2 ₹{suggestion.target_2}</span>}
        {suggestion.invalidation_level && <span className="flex items-center gap-1"><span className="w-3 h-0.5 bg-amber inline-block" /> Inv ₹{suggestion.invalidation_level}</span>}
      </div>
    </div>
  )
}
