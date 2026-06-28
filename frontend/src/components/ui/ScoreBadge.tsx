import { motion } from 'framer-motion'

interface ScoreBadgeProps {
  score: number   // 0–100
  size?: 'sm' | 'md' | 'lg'
}

function scoreColor(s: number) {
  if (s >= 80) return '#00FF88'
  if (s >= 65) return '#FFB020'
  return '#FF3355'
}

export function ScoreBadge({ score, size = 'md' }: ScoreBadgeProps) {
  const color = scoreColor(score)
  const radius = size === 'lg' ? 38 : size === 'md' ? 28 : 20
  const stroke = size === 'lg' ? 4 : 3
  const circumference = 2 * Math.PI * radius
  const offset = circumference * (1 - score / 100)
  const dim = (radius + stroke) * 2
  const fontSize = size === 'lg' ? 'text-2xl' : size === 'md' ? 'text-base' : 'text-xs'

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: dim, height: dim }}>
      <svg width={dim} height={dim} className="-rotate-90">
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={radius}
          fill="none"
          stroke="#1E2535"
          strokeWidth={stroke}
        />
        <motion.circle
          cx={dim / 2}
          cy={dim / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: 'easeOut' }}
        />
      </svg>
      <span className={`absolute font-bold ${fontSize}`} style={{ color }}>
        {score}
      </span>
    </div>
  )
}
