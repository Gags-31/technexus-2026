import { useState } from 'react'
import { Activity, CheckCircle2, Clock, Gauge, Radio, RefreshCw, RotateCcw, Square, Trophy, Users, X } from 'lucide-react'
import { StatusPill } from '../components/Brand'
import { Panel, Stat } from '../components/AdminParts'
import { patch, post } from '../lib/api'

export function Overview({ data, reload }: any) {
  const totals = data?.totals || {}
  return (
    <div className="grid gap-5">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="REGISTERED TEAMS" value={totals.teams ?? '—'} icon={Users} />
        <Stat label="PARTICIPANTS" value={totals.participants ?? '—'} icon={Activity} color="text-violet-300" />
        <Stat label="APPROVED TEAMS" value={totals.approved_teams ?? '—'} icon={CheckCircle2} color="text-emerald-300" />
        <Stat label="PENDING APPROVAL" value={totals.pending_teams ?? '—'} icon={Clock} color="text-amber-300" />
        <Stat label="ACTIVE TEAMS" value={totals.active_teams ?? '—'} icon={Radio} color="text-emerald-300" />
        <Stat label="COMPLETED SESSIONS" value={totals.completed_sessions ?? '—'} icon={Activity} />
        <Stat label="VIOLATIONS" value={totals.violations ?? '—'} icon={Square} color="text-rose-300" />
        <Stat label="LIVE CONNECTIONS" value={data?.live_connections ?? '—'} icon={Gauge} color="text-violet-300" />
      </div>
      <div className="grid gap-5 lg:grid-cols-3">
        <Panel title="Competition status" subtitle="Authoritative server state">
          <div className="flex items-center justify-between rounded-xl border border-cyan/20 bg-cyan/5 p-5">
            <div>
              <p className="eyebrow mb-2">Current round</p>
              <p className="display text-2xl font-bold text-white">{data?.current_round ? 'ROUND ' + data.current_round : 'WAITING'}</p>
              <p className="mt-1 font-mono text-xs text-cyan">{data?.competition_status || 'idle'}</p>
            </div>
            <Gauge size={40} className="text-cyan" />
          </div>
          <button onClick={reload} className="btn btn-ghost mt-4 w-full"><RefreshCw size={15} /> Refresh overview</button>
        </Panel>
        <Panel title="Event configuration" subtitle="Configurable from Admin Settings">
          <div className="space-y-3 text-sm">
            <div className="flex justify-between"><span className="text-slate-500">Event date</span><span className="text-white">{data?.event?.date || '—'}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Start time</span><span className="text-white">{data?.event?.start_time || '—'}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Schedule items</span><span className="text-white">{data?.event?.schedule?.length || 0}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">Admin WebSockets</span><span className="text-emerald-300">{data?.admin_connections ?? 0}</span></div>
          </div>
        </Panel>
        <Panel title="Round snapshot" subtitle="Live team counts">
          <div className="grid gap-2">
            {(data?.rounds || []).map((r: any) => (
              <div key={r.id} className="flex items-center justify-between rounded-lg border border-white/5 bg-white/[.02] px-3 py-2">
                <div>
                  <p className="text-xs font-semibold text-white">R{r.id} · {r.short_name}</p>
                  <p className="font-mono text-[10px] text-slate-500">{r.duration_minutes} min · {r.question_count} questions</p>
                </div>
                <StatusPill status={r.status} />
              </div>
            ))}
          </div>
        </Panel>
      </div>
      <Panel title="Event timeline" subtitle="Official schedule — edit in Admin Settings">
        <div className="scroll-thin overflow-x-auto">
          <table className="table-dark">
            <thead><tr><th>Time</th><th>Activity</th><th>Type</th></tr></thead>
            <tbody>{(data?.event?.schedule || []).map((slot: any) => (
              <tr key={slot.id}>
                <td className="whitespace-nowrap font-mono text-cyan">{slot.start}–{slot.end}</td>
                <td>{slot.label}</td><td><span className="chip">{slot.kind}</span></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}

export function Registrations({ data, reload }: any) {
  const [busy, setBusy] = useState<number | null>(null)
  const act = async (id: number, decision: string) => {
    setBusy(id)
    try { await post(`/admin/registrations/${id}/${decision}`, { notes: '' }); await reload() }
    finally { setBusy(null) }
  }
  return (
    <Panel title="Participant registrations" subtitle={`${data?.length || 0} applications · both members must confirm before approval`}
      action={<button onClick={reload} className="btn btn-ghost px-3 py-2"><RefreshCw size={14} /> Refresh</button>}>
      <div className="scroll-thin overflow-x-auto">
        <table className="table-dark">
          <thead><tr><th>Team</th><th>Institution</th><th>Members</th><th>Code</th><th>Decision</th><th>Action</th></tr></thead>
          <tbody>{(data || []).map((team: any) => (
            <tr key={team.id}>
              <td><p className="font-semibold text-white">{team.name}</p><p className="font-mono text-[10px] text-cyan">{team.public_id}</p></td>
              <td><p className="text-slate-300">{team.college}</p><p className="text-[11px] text-slate-500">{team.department} · Sem {team.semester}</p></td>
              <td>{team.members.map((m: any) => <p key={m.id} className="text-xs text-slate-300">{m.full_name} <span className={m.confirmed ? 'text-emerald-400' : 'text-amber-400'}>{m.confirmed ? '✓' : 'pending'}</span></p>)}</td>
              <td className="code-text text-xs text-cyan">{team.code?.value || '—'}</td>
              <td><StatusPill status={team.decision || team.status} /></td>
              <td><div className="flex gap-2">
                <button disabled={busy === team.id || team.status === 'approved'} className="btn btn-primary px-3 py-1.5 text-[11px]" onClick={() => act(team.id, 'approve')}>Approve</button>
                <button disabled={busy === team.id || team.status === 'rejected'} className="btn btn-danger px-3 py-1.5 text-[11px]" onClick={() => act(team.id, 'reject')}>Reject</button>
              </div></td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </Panel>
  )
}

export function Teams({ data, reload }: any) {
  const [busy, setBusy] = useState<number | null>(null)
  const act = async (id: number, action: string) => {
    setBusy(id)
    try { await post(`/admin/teams/${id}/${action}`, {}); await reload() }
    finally { setBusy(null) }
  }
  const toggle = async (team: any) => {
    try { await patch(`/admin/teams/${team.id}`, { shortlisted: !team.shortlisted }); await reload() } catch { /* ignore */ }
  }
  return (
    <Panel title="Team management" subtitle="Generate, revoke and shortlist teams"
      action={<button onClick={reload} className="btn btn-ghost px-3 py-2"><RefreshCw size={14} /> Refresh</button>}>
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {(data || []).map((team: any) => (
          <div key={team.id} className="glass-hover rounded-xl border border-white/10 bg-white/[.02] p-4">
            <div className="flex items-start justify-between">
              <div><p className="display font-bold text-white">{team.name}</p><p className="font-mono text-[10px] text-cyan">{team.public_id}</p></div>
              <StatusPill status={team.status} />
            </div>
            <p className="mt-3 text-xs text-slate-400">{team.college} · {team.department}</p>
            <div className="mt-3 rounded-lg border border-cyan/20 bg-cyan/5 p-3">
              <p className="font-mono text-[10px] text-slate-500">ACCESS CODE</p>
              <p className="code-text text-lg font-bold text-cyan">{team.code?.value || '—'}</p>
              {team.code?.revoked && <p className="text-[10px] text-rose-400">REVOKED</p>}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button disabled={busy === team.id} className="btn btn-ghost px-3 py-1.5 text-[11px]" onClick={() => act(team.id, 'regenerate-code')}><RotateCcw size={12} /> New code</button>
              <button disabled={busy === team.id} className="btn btn-danger px-3 py-1.5 text-[11px]" onClick={() => act(team.id, 'revoke-code')}><X size={12} /> Revoke</button>
              <button className={`btn px-3 py-1.5 text-[11px] ${team.shortlisted ? 'btn-primary' : 'btn-ghost'}`} onClick={() => toggle(team)}><Trophy size={12} /> {team.shortlisted ? 'Shortlisted' : 'Shortlist'}</button>
            </div>
          </div>
        ))}
      </div>
    </Panel>
  )
}
