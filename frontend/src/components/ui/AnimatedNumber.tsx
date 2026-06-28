import { useEffect, useRef } from 'react'
import { animate } from 'framer-motion'

interface AnimatedNumberProps {
  value: number
  prefix?: string
  suffix?: string
  decimals?: number
  className?: string
}

export function AnimatedNumber({ value, prefix = '', suffix = '', decimals = 2, className = '' }: AnimatedNumberProps) {
  const ref = useRef<HTMLSpanElement>(null)
  const prevRef = useRef(0)

  useEffect(() => {
    const from = prevRef.current
    prevRef.current = value
    const ctrl = animate(from, value, {
      duration: 0.6,
      onUpdate: (v) => {
        if (ref.current) ref.current.textContent = prefix + v.toFixed(decimals) + suffix
      },
    })
    return () => ctrl.stop()
  }, [value, prefix, suffix, decimals])

  return (
    <span ref={ref} className={className}>
      {prefix}{value.toFixed(decimals)}{suffix}
    </span>
  )
}
