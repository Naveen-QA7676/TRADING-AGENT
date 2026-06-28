import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Zap, Monitor, Briefcase, Search,
  TrendingUp, Newspaper, BookOpen, Receipt, Bot, Settings
} from 'lucide-react'
import { useStore } from '../../store/useStore'
import clsx from 'clsx'

const NAV = [
  { to: '/',          icon: LayoutDashboard, label: 'Morning Brief',    short: 'Brief'   },
  { to: '/signals',   icon: Zap,             label: 'Signals',          short: 'Signals', badge: true },
  { to: '/terminal',  icon: Monitor,         label: 'Terminal',         short: 'Term'    },
  { to: '/positions', icon: Briefcase,       label: 'Positions',        short: 'Pos'     },
  { to: '/explore',   icon: Search,          label: 'Stock Explorer',   short: 'Explore' },
  { to: '/predict',   icon: TrendingUp,      label: 'Prediction Board', short: 'Predict' },
  { to: '/news',      icon: Newspaper,       label: 'News',             short: 'News'    },
  { to: '/journal',   icon: BookOpen,        label: 'Journal',          short: 'Journal' },
  { to: '/tax',       icon: Receipt,         label: 'Tax Dashboard',    short: 'Tax'     },
  { to: '/agents',    icon: Bot,             label: 'Agent Monitor',    short: 'Agents'  },
  { to: '/settings',  icon: Settings,        label: 'Settings',         short: 'Setup'   },
]

export function Sidebar() {
  const suggestions = useStore((s) => s.suggestions)
  const isConnected = useStore((s) => s.isConnected)

  return (
    <aside className="flex flex-col w-16 lg:w-52 h-full bg-card border-r border-border shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2 px-3 py-4 border-b border-border">
        <div className="w-8 h-8 rounded-md bg-info/20 flex items-center justify-center shrink-0">
          <Bot size={16} className="text-info" />
        </div>
        <span className="hidden lg:block text-xs font-bold text-text leading-tight">
          AI Trading<br />
          <span className="text-muted font-normal">Intelligence</span>
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-2">
        {NAV.map(({ to, icon: Icon, label, short, badge }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 mx-1 rounded-md transition-colors text-sm',
                isActive
                  ? 'bg-info/10 text-info border border-info/20'
                  : 'text-muted hover:text-text hover:bg-border/50'
              )
            }
          >
            <div className="relative shrink-0">
              <Icon size={16} />
              {badge && suggestions.length > 0 && (
                <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-bull text-bg text-[9px] font-bold flex items-center justify-center">
                  {suggestions.length}
                </span>
              )}
            </div>
            <span className="hidden lg:block truncate">{label}</span>
            <span className="lg:hidden text-[10px]">{short}</span>
          </NavLink>
        ))}
      </nav>

      {/* Connection status */}
      <div className="px-3 py-3 border-t border-border">
        <div className="flex items-center gap-2">
          <span className={clsx('w-2 h-2 rounded-full shrink-0', isConnected ? 'bg-bull live-pulse' : 'bg-bear')} />
          <span className="hidden lg:block text-xs text-muted">
            {isConnected ? 'Kite Connected' : 'Disconnected'}
          </span>
        </div>
      </div>
    </aside>
  )
}
