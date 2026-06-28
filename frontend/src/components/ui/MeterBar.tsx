import { motion } from 'framer-motion'

interface MeterBarProps {
  value: number      // 0–100
  color?: string     // tailwind bg class or hex
  label?: string
  animate?: boolean
}

export function MeterBar({ value, color = '#00FF88', label, animate = true }: MeterBarProps) {
  const pct = Math.min(100, Math.max(0, value))

  return (
    <div className="w-full">
      {label && <div className="text-xs text-muted mb-1">{label}</div>}
      <div className="h-2 rounded-full bg-border overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={animate ? { width: 0 } : { width: `${pct}%` }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}
