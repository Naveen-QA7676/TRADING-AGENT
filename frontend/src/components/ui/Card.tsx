import { ReactNode } from 'react'
import clsx from 'clsx'

interface CardProps {
  children: ReactNode
  className?: string
  glow?: 'bull' | 'bear' | 'info' | 'none'
}

export function Card({ children, className, glow = 'none' }: CardProps) {
  return (
    <div
      className={clsx(
        'rounded-lg border border-border bg-card p-4',
        glow === 'bull' && 'glow-bull border-bull/30',
        glow === 'bear' && 'glow-bear border-bear/30',
        glow === 'info' && 'glow-info border-info/30',
        className
      )}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={clsx('flex items-center justify-between mb-3 pb-2 border-b border-border', className)}>
      {children}
    </div>
  )
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <h3 className="text-xs font-bold uppercase tracking-widest text-muted">{children}</h3>
}
