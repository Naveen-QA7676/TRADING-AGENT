import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Wifi, WifiOff, LogIn, LogOut, RefreshCw,
  AlertTriangle, CheckCircle, ExternalLink, ShieldOff
} from 'lucide-react'
import { authApi, type AuthStatus } from '../api/auth'

function StatusBadge({ connected }: { connected: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium ${
      connected ? 'bg-[#00FF88]/10 text-[#00FF88]' : 'bg-[#FF3355]/10 text-[#FF3355]'
    }`}>
      {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
      {connected ? 'Connected' : 'Disconnected'}
    </span>
  )
}

export function Settings() {
  const [status, setStatus] = useState<AuthStatus | null>(null)
  const [loginUrl, setLoginUrl] = useState<string | null>(null)
  const [loadingUrl, setLoadingUrl] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  async function fetchStatus() {
    try {
      const s = await authApi.getStatus()
      setStatus(s)
    } catch {
      setStatus(null)
    }
  }

  useEffect(() => {
    fetchStatus()
    const id = setInterval(fetchStatus, 10_000)
    return () => clearInterval(id)
  }, [])

  async function handleGetLoginUrl() {
    setLoadingUrl(true)
    setError(null)
    try {
      const { login_url } = await authApi.getLoginUrl()
      setLoginUrl(login_url)
    } catch (e: any) {
      setError('Failed to generate login URL. Check that API key & secret are set in .env')
    } finally {
      setLoadingUrl(false)
    }
  }

  async function handleLogout() {
    setLoggingOut(true)
    try {
      await authApi.logout()
      setSuccessMsg('Logged out successfully.')
      setLoginUrl(null)
      await fetchStatus()
    } catch {
      setError('Logout failed.')
    } finally {
      setLoggingOut(false)
    }
  }

  async function handleResetLimits() {
    setResetting(true)
    try {
      await authApi.resetDailyLimits()
      setSuccessMsg('Daily trading limit reset — trading re-enabled.')
    } catch {
      setError('Reset failed.')
    } finally {
      setResetting(false)
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-white">Settings</h1>

      {/* Connection card */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-xl border border-[#1E2535] bg-[#141824] p-6 space-y-5"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Zerodha Kite Connection</h2>
          {status && <StatusBadge connected={status.kite_connected} />}
        </div>

        {status?.kite_connected && (
          <div className="flex items-center gap-3 rounded-lg bg-[#00FF88]/5 border border-[#00FF88]/20 px-4 py-3">
            <CheckCircle size={18} className="text-[#00FF88] shrink-0" />
            <div>
              <p className="text-sm text-white font-medium">{status.user_name}</p>
              <p className="text-xs text-gray-400">User ID: {status.user_id}</p>
            </div>
          </div>
        )}

        {!status?.kite_connected && (
          <div className="space-y-4">
            <p className="text-sm text-gray-400">
              Kite Connect OAuth login is required before the platform can stream prices,
              place orders, or run analysis.
            </p>

            {!loginUrl ? (
              <button
                onClick={handleGetLoginUrl}
                disabled={loadingUrl}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#4488FF] hover:bg-[#4488FF]/80
                           text-white text-sm font-medium transition-colors disabled:opacity-50"
              >
                {loadingUrl ? (
                  <RefreshCw size={16} className="animate-spin" />
                ) : (
                  <LogIn size={16} />
                )}
                Generate Login URL
              </button>
            ) : (
              <div className="space-y-3">
                <p className="text-xs text-gray-400">
                  Open the link below in your browser, log in with Zerodha, then return here.
                  The platform detects the callback automatically.
                </p>
                <a
                  href={loginUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#00FF88] hover:bg-[#00FF88]/80
                             text-black text-sm font-semibold transition-colors w-fit"
                >
                  <ExternalLink size={16} />
                  Open Zerodha Login
                </a>
                <button
                  onClick={handleGetLoginUrl}
                  className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
                >
                  Regenerate URL
                </button>
              </div>
            )}
          </div>
        )}

        {status?.kite_connected && (
          <button
            onClick={handleLogout}
            disabled={loggingOut}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg border border-[#FF3355]/40
                       hover:border-[#FF3355] text-[#FF3355] text-sm font-medium transition-colors disabled:opacity-50"
          >
            {loggingOut ? <RefreshCw size={16} className="animate-spin" /> : <LogOut size={16} />}
            Logout
          </button>
        )}
      </motion.div>

      {/* Trading status card */}
      {status && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.08 }}
          className="rounded-xl border border-[#1E2535] bg-[#141824] p-6 space-y-4"
        >
          <h2 className="text-lg font-semibold text-white">Trading Status</h2>

          {status.trading_disabled ? (
            <div className="flex items-start gap-3 rounded-lg bg-[#FFB020]/5 border border-[#FFB020]/20 px-4 py-3">
              <AlertTriangle size={18} className="text-[#FFB020] shrink-0 mt-0.5" />
              <div className="space-y-2">
                <p className="text-sm text-[#FFB020] font-medium">Trading disabled for today</p>
                <p className="text-xs text-gray-400">
                  Daily loss limit reached. Trading will re-enable automatically tomorrow,
                  or you can reset it manually below.
                </p>
                <button
                  onClick={handleResetLimits}
                  disabled={resetting}
                  className="flex items-center gap-1.5 text-xs text-[#FFB020] hover:text-white
                             transition-colors disabled:opacity-50"
                >
                  {resetting ? <RefreshCw size={12} className="animate-spin" /> : <ShieldOff size={12} />}
                  Reset daily limit
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-[#00FF88]">
              <CheckCircle size={16} />
              Trading enabled
            </div>
          )}
        </motion.div>
      )}

      {/* Platform info */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.16 }}
        className="rounded-xl border border-[#1E2535] bg-[#141824] p-6 space-y-3"
      >
        <h2 className="text-lg font-semibold text-white">Platform</h2>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          {[
            ['Version', '1.0.0'],
            ['AI Model', 'claude-opus-4-8'],
            ['Agents', '21'],
            ['Architecture', 'Decision-support (user confirms every trade)'],
          ].map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-gray-500">{k}</dt>
              <dd className="text-white">{v}</dd>
            </div>
          ))}
        </dl>
      </motion.div>

      {/* Toast messages */}
      {(error || successMsg) && (
        <div className={`fixed bottom-6 right-6 px-4 py-3 rounded-lg text-sm font-medium shadow-lg
          ${error ? 'bg-[#FF3355]/90 text-white' : 'bg-[#00FF88]/90 text-black'}`}>
          {error || successMsg}
          <button
            onClick={() => { setError(null); setSuccessMsg(null) }}
            className="ml-3 opacity-70 hover:opacity-100"
          >✕</button>
        </div>
      )}
    </div>
  )
}
