import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import { Download, AlertTriangle, CheckCircle } from 'lucide-react'
import { taxApi, TaxSummary, MonthlyBreakdown } from '../api/tax'
import { Card, CardHeader, SectionTitle } from '../components/ui/Card'
import { AnimatedNumber } from '../components/ui/AnimatedNumber'
import clsx from 'clsx'

// ─── Mock data ────────────────────────────────────────────────────────────────

const MOCK_SUMMARY: TaxSummary = {
  fy: '2025-26',
  pnl_report: {
    speculative_income: 218450,
    speculative_loss:   34200,
    net_speculative:    184250,
    stcg:               42000,
    ltcg:               28000,
    total_net_pnl:      254250,
    estimated_tax:      76275,
    net_after_tax:      177975,
    advance_tax_sep:    57206,
  },
  turnover: {
    speculative: 4280000,
    delivery:    1850000,
    total:       6130000,
    audit_required: false,
    gst_required: false,
  },
  charges: {
    brokerage:        12480,
    stt:              8640,
    exchange_charges: 3250,
    gst:              2880,
    stamp_duty:       1820,
    total:            29070,
  },
}

const MOCK_MONTHLY: MonthlyBreakdown = {
  fy: '2025-26',
  monthly: {
    Apr: 22400,
    May: 38700,
    Jun: 45200,
    Jul: 28900,
    Aug: 51400,
    Sep: -12500,
    Oct: 34800,
    Nov: 42600,
    Dec: 18900,
    Jan: 29800,
    Feb: 33600,
    Mar: 20450,
  },
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(n: number, prefix = '₹') {
  const abs = Math.abs(n)
  const str = abs >= 100000
    ? (abs / 100000).toFixed(2) + 'L'
    : abs.toLocaleString('en-IN')
  return (n < 0 ? '−' : '') + prefix + str
}

// ─── Summary Sidebar ──────────────────────────────────────────────────────────

function TaxSidebar({ s }: { s: TaxSummary }) {
  const r = s.pnl_report
  const taxRate = (r.estimated_tax / r.total_net_pnl * 100).toFixed(1)

  const items = [
    { label: 'Speculative Income',    value: r.speculative_income, color: '#00FF88' },
    { label: 'Speculative Loss',      value: -r.speculative_loss,  color: '#FF3355' },
    { label: 'Net Speculative P&L',   value: r.net_speculative,    color: r.net_speculative >= 0 ? '#00FF88' : '#FF3355', bold: true },
    { label: 'STCG (Delivery ≤1yr)',  value: r.stcg,               color: '#00FF88' },
    { label: 'LTCG (Delivery >1yr)',  value: r.ltcg,               color: '#00FF88' },
    { label: 'Total Net P&L',         value: r.total_net_pnl,      color: r.total_net_pnl >= 0 ? '#00FF88' : '#FF3355', bold: true, divider: true },
    { label: `Estimated Tax (${taxRate}%)`, value: -r.estimated_tax, color: '#FFB020', bold: true },
    { label: 'Net After Tax',         value: r.net_after_tax,      color: '#4488FF', bold: true },
    { label: 'Advance Tax (Sep 15)',  value: r.advance_tax_sep,    color: '#FFB020' },
  ]

  return (
    <Card>
      <CardHeader>
        <SectionTitle>FY {s.fy} Summary</SectionTitle>
      </CardHeader>
      <div className="space-y-2 text-xs">
        {items.map((it) => (
          <div key={it.label}>
            {it.divider && <div className="border-t border-border my-2" />}
            <div className="flex justify-between items-center">
              <span className={clsx('text-muted', it.bold && 'text-text font-semibold')}>{it.label}</span>
              <span className="font-mono font-bold" style={{ color: it.color }}>
                {fmt(it.value)}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-border space-y-2 text-xs">
        <div className="text-muted font-semibold text-[10px] uppercase tracking-wide mb-2">Turnover</div>
        <div className="flex justify-between">
          <span className="text-muted">Speculative (Intraday)</span>
          <span className="font-mono">{fmt(s.turnover.speculative)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted">Delivery</span>
          <span className="font-mono">{fmt(s.turnover.delivery)}</span>
        </div>
        <div className="flex justify-between font-bold">
          <span className="text-text">Total</span>
          <span className="font-mono">{fmt(s.turnover.total)}</span>
        </div>
        <div className="mt-2 flex flex-col gap-1">
          <div className="flex items-center gap-1.5">
            {s.turnover.audit_required ? <AlertTriangle size={12} className="text-bear" /> : <CheckCircle size={12} className="text-bull" />}
            <span className={s.turnover.audit_required ? 'text-bear' : 'text-bull'}>
              Audit {s.turnover.audit_required ? 'required' : 'not required'}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            {s.turnover.gst_required ? <AlertTriangle size={12} className="text-amber" /> : <CheckCircle size={12} className="text-bull" />}
            <span className={s.turnover.gst_required ? 'text-amber' : 'text-bull'}>
              GST registration {s.turnover.gst_required ? 'required' : 'not required'}
            </span>
          </div>
        </div>
      </div>
    </Card>
  )
}

// ─── Monthly bar chart ────────────────────────────────────────────────────────

function MonthlyChart({ monthly }: { monthly: Record<string, number> }) {
  const data = Object.entries(monthly).map(([month, pnl]) => ({ month, pnl }))

  return (
    <Card>
      <CardHeader>
        <SectionTitle>Monthly P&L</SectionTitle>
        <span className="text-xs text-muted">Green = profitable months</span>
      </CardHeader>
      <ResponsiveContainer width="100%" height={170}>
        <BarChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 50 }}>
          <XAxis dataKey="month" tick={{ fill: '#6B7280', fontSize: 11 }} />
          <YAxis
            tickFormatter={(v: number) => (v >= 0 ? '+' : '') + (v / 1000).toFixed(0) + 'K'}
            tick={{ fill: '#6B7280', fontSize: 10 }}
          />
          <Tooltip
            contentStyle={{ background: '#141824', border: '1px solid #1E2535', fontSize: 11 }}
            formatter={(v: number) => [fmt(v), 'P&L']}
          />
          <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
            {data.map((d) => (
              <Cell key={d.month} fill={d.pnl >= 0 ? '#00FF88' : '#FF3355'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  )
}

// ─── Charges pie ─────────────────────────────────────────────────────────────

const CHARGE_COLORS = ['#4488FF', '#FFB020', '#00FF88', '#FF3355', '#A855F7']

function ChargesPie({ charges }: { charges: TaxSummary['charges'] }) {
  const data = [
    { name: 'Brokerage',   value: charges.brokerage },
    { name: 'STT',         value: charges.stt },
    { name: 'Exchange',    value: charges.exchange_charges },
    { name: 'GST',         value: charges.gst },
    { name: 'Stamp Duty',  value: charges.stamp_duty },
  ]

  return (
    <Card>
      <CardHeader>
        <SectionTitle>Trading Charges Breakdown</SectionTitle>
        <span className="text-bear font-bold text-sm">{fmt(charges.total)} total</span>
      </CardHeader>
      <ResponsiveContainer width="100%" height={160}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%" cy="50%"
            innerRadius={45}
            outerRadius={72}
            paddingAngle={2}
          >
            {data.map((_, i) => <Cell key={i} fill={CHARGE_COLORS[i % CHARGE_COLORS.length]} />)}
          </Pie>
          <Legend
            formatter={(value) => <span style={{ fontSize: 11, color: '#9CA3AF' }}>{value}</span>}
          />
          <Tooltip
            contentStyle={{ background: '#141824', border: '1px solid #1E2535', fontSize: 11 }}
            formatter={(v: number) => [fmt(v), '']}
          />
        </PieChart>
      </ResponsiveContainer>
    </Card>
  )
}

// ─── Download buttons ─────────────────────────────────────────────────────────

function DownloadCard({ fy }: { fy: string }) {
  return (
    <Card>
      <CardHeader><SectionTitle>Downloads</SectionTitle></CardHeader>
      <div className="space-y-2">
        <a
          href={taxApi.downloadPnL(fy)}
          download
          className="flex items-center justify-between p-2.5 rounded-lg border border-border hover:border-info/40 hover:bg-info/5 transition-colors text-xs group"
        >
          <div>
            <div className="font-medium text-text">P&L Report (CSV)</div>
            <div className="text-muted">All trades · ITR-3 compatible</div>
          </div>
          <Download size={16} className="text-muted group-hover:text-info transition-colors" />
        </a>
        <a
          href={taxApi.downloadITR(fy)}
          download
          className="flex items-center justify-between p-2.5 rounded-lg border border-border hover:border-bull/40 hover:bg-bull/5 transition-colors text-xs group"
        >
          <div>
            <div className="font-medium text-text">ITR Summary (PDF)</div>
            <div className="text-muted">Schedule P & CYLA · CA-ready</div>
          </div>
          <Download size={16} className="text-muted group-hover:text-bull transition-colors" />
        </a>
      </div>
      <div className="mt-3 p-2 rounded bg-amber/5 border border-amber/20 text-[10px] text-amber flex items-start gap-1.5">
        <AlertTriangle size={12} className="shrink-0 mt-0.5" />
        This is an estimate only. Consult your CA before filing.
      </div>
    </Card>
  )
}

// ─── Key metrics strip ────────────────────────────────────────────────────────

function KeyMetric({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-card rounded-lg p-3 border border-border text-center"
    >
      <div className="text-xs text-muted mb-1">{label}</div>
      <div className="text-base font-bold" style={{ color }}>
        <AnimatedNumber value={value} prefix="₹" suffix="" decimals={0} />
      </div>
    </motion.div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export function TaxDashboard() {
  const [fy, setFy] = useState('2025-26')
  const [summary, setSummary] = useState<TaxSummary>(MOCK_SUMMARY)
  const [monthly, setMonthly] = useState<MonthlyBreakdown>(MOCK_MONTHLY)

  useEffect(() => {
    Promise.allSettled([taxApi.getSummary(fy), taxApi.getMonthly(fy)]).then(([s, m]) => {
      if (s.status === 'fulfilled') setSummary(s.value)
      if (m.status === 'fulfilled') setMonthly(m.value)
    })
  }, [fy])

  const r = summary.pnl_report

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold">📊 Tax Dashboard</h1>
          <p className="text-xs text-muted">Income tax estimates · FY {fy}</p>
        </div>
        <select
          value={fy}
          onChange={(e) => setFy(e.target.value)}
          className="bg-card border border-border rounded-md px-3 py-1.5 text-xs text-text"
        >
          <option value="2025-26">FY 2025-26</option>
          <option value="2024-25">FY 2024-25</option>
        </select>
      </div>

      {/* Key metrics strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KeyMetric label="Net P&L"        value={r.total_net_pnl}  color={r.total_net_pnl >= 0 ? '#00FF88' : '#FF3355'} />
        <KeyMetric label="Estimated Tax"  value={r.estimated_tax}  color="#FFB020" />
        <KeyMetric label="Net After Tax"  value={r.net_after_tax}  color="#4488FF" />
        <KeyMetric label="Advance Tax Due" value={r.advance_tax_sep} color="#FFB020" />
      </div>

      {/* Main layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: summary sidebar */}
        <div className="space-y-4">
          <TaxSidebar s={summary} />
          <DownloadCard fy={fy} />
        </div>

        {/* Right: charts */}
        <div className="lg:col-span-2 space-y-4">
          <MonthlyChart monthly={monthly.monthly} />
          <ChargesPie charges={summary.charges} />
        </div>
      </div>
    </div>
  )
}
