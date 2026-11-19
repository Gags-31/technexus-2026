import { useEffect, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { Download, Pause, Play, Radio, RefreshCw, Search, Square } from 'lucide-react'
import { StatusPill } from '../components/Brand'
import { Panel, ConfirmDialog } from '../components/AdminParts'
import { ApiError, downloadUrl, post } from '../lib/api'

export function RoundManagement({ data, reload, refreshAll }: any) {
  const [confirm, setConfirm] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const run = async () => {
    setBusy(true); setError('')
    try {
      await post(`/admin/rounds/${confirm.round.id}/${confirm.action}`, {})
      setConfirm(null)
      await Promise.all([reload(), refreshAll()])
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Operation failed')
      setConfirm(null)
    } finally { setBusy(false) }
  }
  const labels: Record<string, string> = { start: 'START ROUND', pause: 'PAUSE ROUND', resume: 'RESUME ROUND', end: 'END ROUND' }
  const colors: Record<number, string> = {
    1: 'from-cyan/80 to-blue-500/20', 2: 'from-blue-400/80 to-violet-500/20',
    3: 'from-violet-400/80 to-fuchsia-500/20', 4: 'from-amber-300/80 to-rose-500/20',
  }
  return (
    <>
      {error && <div className="mb-4 rounded-xl border border-rose-400/30 bg-rose-400/10 p-4 text-sm text-rose-300">{error}</div>}
      <div className="grid gap-5 lg:grid-cols-2">
        {(data || []).map((r: any) => (
          <div key={r.id} className="glass relative overflow-hidden rounded-2xl p-6">
            <div className={`absolute inset-x-0 top-0 h-1 bg-gradient-to-r ${colors[r.id]}`} />
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="eyebrow mb-1">Round 0{r.id}</p>
                <h3 className="display text-xl font-bold text-white">{r.name}</h3>
                <p className="mt-1 text-xs text-slate-500">{r.duration_minutes} minutes · {r.question_count} questions</p>
              </div>
              <StatusPill status={r.status} />
            </div>
            <div className="mt-6 grid grid-cols-3 gap-2 text-center">
              {[['Eligible teams', r.registered_teams], ['Active', r.active_teams], ['Completed', r.completed_teams]].map(([label, value]) => (
                <div key={String(label)} className="rounded-lg border border-white/5 bg-white/[.02] px-2 py-3">
                  <p className="display text-xl font-bold text-white">{value as any}</p>
                  <p className="font-mono text-[9px] tracking-wider text-slate-500">{String(label).toUpperCase()}</p>
                </div>
              ))}
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <button className="btn btn-primary flex-1" disabled={busy || r.status !== 'locked'} onClick={() => setConfirm({ round: r, action: 'start' })}><Play size={15} /> Start round</button>
              <button className="btn btn-ghost" disabled={busy || r.status !== 'active'} onClick={() => setConfirm({ round: r, action: 'pause' })}><Pause size={15} /> Pause</button>
              <button className="btn btn-ghost" disabled={busy || r.status !== 'paused'} onClick={() => setConfirm({ round: r, action: 'resume' })}><Play size={15} /> Resume</button>
              <button className="btn btn-danger" disabled={busy || !['active', 'paused'].includes(r.status)} onClick={() => setConfirm({ round: r, action: 'end' })}><Square size={15} /> End</button>
            </div>
          </div>
        ))}
      </div>
      <AnimatePresence>{confirm && <ConfirmDialog
        title={`${labels[confirm.action]} — Round ${confirm.round.id}`}
        body={confirm.action === 'start'
          ? `This activates ${confirm.round.name} for all eligible teams at once using authoritative server time. Future rounds remain locked. Continue?`
          : confirm.action === 'end'
            ? 'This closes the round for every team and automatically submits all saved answers. Continue?'
            : 'This applies globally to every connected team. Continue?'}
        confirmLabel={labels[confirm.action]} danger={confirm.action === 'end'} onCancel={() => setConfirm(null)} onConfirm={run}
      />}</AnimatePresence>
    </>
  )
}

export function Monitor({ data, reload }: any) {
  return (
    <Panel title="Live competition monitor" subtitle={`${data?.connected_count || 0} teams connected via WebSocket`}
      action={<button onClick={reload} className="btn btn-ghost px-3 py-2"><RefreshCw size={14} /> Refresh</button>}>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {(data?.teams || []).map((team: any) => (
          <div key={team.team_id} className="glass-hover rounded-xl border border-white/10 bg-white/[.02] p-4">
            <div className="flex items-center justify-between">
              <p className="display font-bold text-white">{team.team_name}</p>
              <span className={`h-2.5 w-2.5 rounded-full ${team.connected ? 'bg-emerald-400 pulse-dot text-emerald-400' : 'bg-slate-600'}`} />
            </div>
            <p className="mt-1 text-[11px] text-slate-500">{team.members.join(' · ')}</p>
            <div className="mt-4 grid grid-cols-3 gap-2 text-center">
              {[['Saved', team.answers_saved], ['Submitted', team.answers_submitted], ['Violations', team.violations]].map(([label, value]) => (
                <div key={String(label)} className="rounded-lg bg-white/[.03] p-2">
                  <p className="text-sm font-bold text-white">{value as any}</p>
                  <p className="font-mono text-[9px] text-slate-500">{String(label).toUpperCase()}</p>
                </div>
              ))}
            </div>
            <div className="mt-3 flex gap-2">
              <StatusPill status={team.active_session || team.status} />
              {team.review_required && <span className="chip text-rose-300">REVIEW</span>}
            </div>
          </div>
        ))}
      </div>
    </Panel>
  )
}

export function Scoreboard({ data, reload }: any) {
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('rank')
  const [status, setStatus] = useState('all')
  const [round, setRound] = useState('')
  useEffect(() => { const timer = setInterval(reload, 10000); return () => clearInterval(timer) }, [reload])
  const rows = (data?.rows || []).filter((r: any) => {
    if (search && !(r.team_name + r.college + r.public_id).toLowerCase().includes(search.toLowerCase())) return false
    if (status === 'completed' && !r.completed) return false
    if (status === 'in_progress' && r.completed) return false
    if (round && r.rounds[round]?.status === 'not_started') return false
    return true
  }).sort((a: any, b: any) => sort === 'name' ? a.team_name.localeCompare(b.team_name) : sort === 'total' ? b.total - a.total : a.rank - b.rank)
  return (
    <Panel title="Private live scoreboard" subtitle="Organisers only · updates on every answer submission"
      action={<div className="flex flex-wrap gap-2">
        <a className="btn btn-ghost px-3 py-2" href={downloadUrl('/admin/export/scoreboard.csv')}><Download size={14} /> CSV</a>
        <a className="btn btn-ghost px-3 py-2" href={downloadUrl('/admin/export/scoreboard.pdf')}><Download size={14} /> PDF</a>
      </div>}>
      <div className="mb-4 flex flex-wrap gap-2">
        <div className="relative min-w-[220px] flex-1">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input className="field py-2 pl-10" placeholder="Search team or college…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <select className="field w-auto py-2" value={sort} onChange={(e) => setSort(e.target.value)}><option value="rank">Sort: Rank</option><option value="total">Sort: Total</option><option value="name">Sort: Team name</option></select>
        <select className="field w-auto py-2" value={status} onChange={(e) => setStatus(e.target.value)}><option value="all">All teams</option><option value="completed">Completed</option><option value="in_progress">In progress</option></select>
        <select className="field w-auto py-2" value={round} onChange={(e) => setRound(e.target.value)}><option value="">All rounds</option><option value="1">Round 1</option><option value="2">Round 2</option><option value="3">Round 3</option><option value="4">Round 4</option></select>
      </div>
      <div className="scroll-thin overflow-x-auto">
        <table className="table-dark">
          <thead><tr><th>Rank</th><th>Team</th><th>R1</th><th>R2</th><th>R3</th><th>R4</th><th>Total</th><th>Correct</th><th>Wrong</th><th>Unans.</th><th>Status</th><th>Review</th></tr></thead>
          <tbody>{rows.map((r: any) => (
            <tr key={r.team_id}>
              <td className="display text-lg font-bold text-cyan">#{r.rank}</td>
              <td><p className="font-semibold text-white">{r.team_name}</p><p className="font-mono text-[10px] text-slate-500">{r.college}</p></td>
              {[1, 2, 3, 4].map((n) => <td key={n} className="font-mono">{r.rounds[String(n)].score}</td>)}
              <td className="display font-bold text-white">{r.total}</td>
              <td className="text-emerald-300">{r.correct}</td><td className="text-rose-300">{r.incorrect}</td><td>{r.unanswered}</td>
              <td>{r.completed ? <span className="chip text-emerald-300">Complete</span> : r.active ? <span className="chip text-cyan">Active</span> : <span className="chip">Idle</span>}</td>
              <td>{r.pending_review ? <span className="chip text-rose-300">Pending</span> : '—'}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <p className="mt-4 font-mono text-[10px] text-slate-600">Last updated {data?.updated_at || '—'} · auto-refresh every 10s</p>
    </Panel>
  )
}
