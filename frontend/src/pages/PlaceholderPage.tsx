import { Clock } from 'lucide-react'

export function PlaceholderPage({ title, phase }: { title: string; phase: number }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center gap-4">
      <Clock size={40} className="text-info/50" />
      <h2 className="text-xl font-bold text-text">{title}</h2>
      <p className="text-muted text-sm">Coming in Phase {phase} of the build plan.</p>
      <div className="px-4 py-2 rounded-md border border-info/30 bg-info/5 text-info text-xs">
        Phase {phase} — implementation in progress
      </div>
    </div>
  )
}
