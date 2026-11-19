import { useEffect, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { CalendarClock, CheckCircle2, Download, Megaphone, RefreshCw, Search, Settings2, Trophy } from 'lucide-react'
import { Panel, ConfirmDialog } from '../components/AdminParts'
import { ApiError, downloadUrl, get, patch, post } from '../lib/api'

export function QuestionBank({ data, answers }: any) {
  const [filters, setFilters] = useState({ domain: '', round: '', search: '' })
  const rows = (data || []).filter((q: any) =>
    (!filters.domain || q.domain === filters.domain) &&
    (!filters.round || q.round === Number(filters.round)) &&
    (!filters.search || (q.id + q.question).toLowerCase().includes(filters.search.toLowerCase())))
  return (
    <>
      <div className="mb-5 flex flex-wrap gap-2">
        <div className="relative min-w-[220px] flex-1"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" /><input className="field py-2 pl-10" placeholder="Search question ID or text…" value={filters.search} onChange={(e) => setFilters({ ...filters, search: e.target.value })} /></div>
        <select className="field w-auto py-2" value={filters.domain} onChange={(e) => setFilters({ ...filters, domain: e.target.value })}><option value="">All domains</option><option>Artificial Intelligence</option><option>Cloud Computing</option><option>Operating Systems</option><option>DBMS</option></select>
        <select className="field w-auto py-2" value={filters.round} onChange={(e) => setFilters({ ...filters, round: e.target.value })}><option value="">All rounds</option><option value="1">Round 1</option><option value="2">Round 2</option><option value="3">Round 3</option><option value="4">Round 4</option></select>
        <a className="btn btn-ghost px-3 py-2" href={downloadUrl('/admin/questions/export.csv')}><Download size={14} /> CSV</a>
        <a className="btn btn-ghost px-3 py-2" href={downloadUrl('/admin/questions/export.pdf')}><Download size={14} /> PDF</a>
      </div>
      <div className="grid gap-3">
        {rows.slice(0, 60).map((q: any) => <div key={q.id} className="glass-hover rounded-xl border border-white/10 bg-white/[.02] p-4">
          <div className="flex flex-wrap items-center gap-2"><span className="chip">{q.id}</span><span className="chip">{q.domain}</span><span className="chip">R{q.round}</span><span className="chip">{q.difficulty}</span><span className="chip">{q.marks} marks</span></div>
          <p className="mt-3 text-sm leading-relaxed text-slate-200">{q.question}</p>
          <div className="mt-3 grid gap-1.5 md:grid-cols-2">
            {q.options.map((option: string, i: number) => <p key={i} className={'rounded-lg border px-3 py-2 text-xs ' + (answers && q.correct_index === i ? 'border-emerald-400/40 bg-emerald-400/10 text-emerald-200' : 'border-white/5 bg-white/[.02] text-slate-400')}>{String.fromCharCode(65 + i)}. {option}{answers && q.correct_index === i ? ' ✓ CORRECT' : ''}</p>)}
          </div>
          {answers && <>
            <div className="mt-3 rounded-lg border border-violet/20 bg-violet/5 p-3 text-xs text-violet-100"><b>Explanation:</b> {q.explanation}</div>
            <div className="mt-2 rounded-lg border border-amber-400/20 bg-amber-400/5 p-3 text-xs text-amber-100"><b>Hint:</b> {q.hint}</div>
          </>}
          {q.reference && <p className="mt-2 font-mono text-[10px] text-slate-500">{q.reference}</p>}
        </div>)}
      </div>
      <p className="mt-4 font-mono text-[11px] text-slate-500">Showing {Math.min(60, rows.length)} of {rows.length} questions · {answers ? 'PRIVATE ANSWER KEY VIEW' : 'question bank (answers hidden)'}</p>
    </>
  )
}

export function Violations({ data, reload }: any) {
  const review = async (id: number, reinstate: boolean) => { try { await post('/admin/violations/' + id + '/review', { reinstate, note: '' }); await reload() } catch {} }
  const teamAction = async (teamId: number, action: string) => { try { await post('/admin/teams/' + teamId + '/' + action, {}); await reload() } catch {} }
  return (
    <Panel title="Anti-cheating monitor" subtitle="Browser visibility, focus and fullscreen events · manual review and reinstatement">
      <div className="scroll-thin overflow-x-auto">
        <table className="table-dark"><thead><tr><th>Time</th><th>Team</th><th>Event</th><th>Detail</th><th>Action</th><th>Status</th><th>Action</th></tr></thead>
          <tbody>{(data || []).map((v: any) => <tr key={v.id}>
            <td className="whitespace-nowrap font-mono text-[10px] text-slate-500">{new Date(v.created_at).toLocaleString()}</td>
            <td>Team #{v.team_id}</td><td><span className="chip text-amber-300">{v.kind}</span></td><td className="text-slate-400">{v.detail}</td>
            <td>{v.action}</td><td>{v.reviewed ? <span className="chip text-emerald-300">Reviewed</span> : <span className="chip text-rose-300">Open</span>}</td>
            <td className="flex gap-2">
              <button className="btn btn-ghost px-2 py-1 text-[10px]" onClick={() => review(v.id, true)}>Mark reviewed</button>
              {v.team_id && <button className="btn btn-ghost px-2 py-1 text-[10px]" onClick={() => teamAction(v.team_id, 'reinstate')}>Reinstate</button>}
              {v.team_id && <button className="btn btn-danger px-2 py-1 text-[10px]" onClick={() => teamAction(v.team_id, 'disqualify')}>Disqualify</button>}
            </td>
          </tr>)}</tbody>
        </table>
        {(data || []).length === 0 && <p className="py-8 text-center text-slate-500">No violations recorded.</p>}
      </div>
    </Panel>
  )
}

export function Breaks({ riddles, memes, reload }: any) {
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Panel title="Technology riddles" subtitle={(riddles?.length || 0) + ' original riddles · one displayed after each round'}
        action={<button onClick={reload} className="btn btn-ghost px-3 py-2"><RefreshCw size={14} /> Refresh</button>}>
        <div className="scroll-thin max-h-[560px] space-y-2 overflow-y-auto pr-2">
          {(riddles || []).map((r: any) => <div key={r.id} className="rounded-xl border border-white/10 bg-white/[.02] p-3">
            <div className="flex items-center justify-between"><span className="chip">{r.category}</span><span className="font-mono text-[10px] text-cyan">{r.id}</span></div>
            <p className="mt-2 text-sm text-slate-200">{r.question}</p><p className="mt-2 text-xs text-emerald-300">Answer: {r.answer}</p><p className="mt-1 text-[11px] text-slate-500">{r.explanation}</p>
          </div>)}
        </div>
      </Panel>
      <Panel title="Meme breaks" subtitle="Original text-based templates · no unreliable external images">
        <div className="grid gap-3 sm:grid-cols-2">
          {(memes || []).map((m: any) => <div key={m.id} className="rounded-xl border border-white/10 bg-black/30 p-4 text-center">
            <p className="text-4xl">{m.glyph}</p><p className="display mt-3 text-sm font-bold text-white">{m.top}</p><p className="mt-2 text-xs text-cyan">{m.bottom}</p><p className="mt-3 font-mono text-[9px] text-slate-500">{m.category} · {m.id}</p>
          </div>)}
        </div>
      </Panel>
    </div>
  )
}

export function Results({ data, reload }: any) {
  const [confirm, setConfirm] = useState(false)
  const publish = async () => { await post('/admin/results/publish', {}); setConfirm(false); await reload() }
  return (
    <>
      <Panel title="Final results" subtitle="Tie-breakers: final round score, then lower completion time"
        action={<div className="flex gap-2">
          <a className="btn btn-ghost px-3 py-2" href={downloadUrl('/admin/export/scoreboard.csv')}><Download size={14} /> CSV</a>
          <a className="btn btn-ghost px-3 py-2" href={downloadUrl('/admin/export/scoreboard.pdf')}><Download size={14} /> PDF</a>
          <button className="btn btn-primary px-3 py-2" onClick={() => setConfirm(true)} disabled={data?.published}><Trophy size={14} /> {data?.published ? 'Published' : 'Publish results'}</button>
        </div>}>
        <div className="scroll-thin overflow-x-auto">
          <table className="table-dark"><thead><tr><th>Rank</th><th>Team</th><th>R1</th><th>R2</th><th>R3</th><th>R4</th><th>Total</th><th>Final score</th><th>Completion</th></tr></thead>
            <tbody>{(data?.rows || []).slice(0, 25).map((r: any) => <tr key={r.team_id}>
              <td className="display text-xl font-bold gradient-text">#{r.rank}</td><td className="font-semibold text-white">{r.team_name}</td>
              {[1, 2, 3, 4].map((n) => <td key={n}>{r.rounds[String(n)].score}</td>)}
              <td className="font-bold text-cyan">{r.total}</td><td>{r.rounds['4'].score}</td><td className="font-mono text-[10px] text-slate-500">{r.submission_time ? new Date(r.submission_time).toLocaleString() : '—'}</td>
            </tr>)}</tbody>
          </table>
        </div>
      </Panel>
      <AnimatePresence>{confirm && <ConfirmDialog title="Publish final results?" body="Participants will be able to see their own team score." confirmLabel="Publish results" onCancel={() => setConfirm(false)} onConfirm={publish} />}</AnimatePresence>
    </>
  )
}

export function Announcements({ data, reload }: any) {
  const [form, setForm] = useState({ title: '', body: '', audience: 'all' })
  const [error, setError] = useState('')
  const create = async (e: React.FormEvent) => {
    e.preventDefault(); setError('')
    try { await post('/admin/announcements', form); setForm({ title: '', body: '', audience: 'all' }); await reload() }
    catch (err) { setError(err instanceof ApiError ? err.detail : 'Failed') }
  }
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <Panel title="Broadcast announcement" subtitle="Sent instantly to participants over WebSocket">
        <form onSubmit={create} className="grid gap-4">
          <div><label className="label">Title</label><input className="field" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required /></div>
          <div><label className="label">Message</label><textarea className="field min-h-[120px]" value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} required /></div>
          <div><label className="label">Audience</label><select className="field" value={form.audience} onChange={(e) => setForm({ ...form, audience: e.target.value })}><option value="all">Everyone</option><option value="participants">Participants only</option><option value="administrators">Administrators only</option></select></div>
          {error && <p className="text-sm text-rose-400">{error}</p>}
          <button className="btn btn-primary"><Megaphone size={15} /> Broadcast now</button>
        </form>
      </Panel>
      <Panel title="Announcement history" subtitle={(data?.length || 0) + ' messages'}>
        <div className="grid gap-2">
          {(data || []).map((a: any) => <div key={a.id} className="rounded-xl border border-white/10 bg-white/[.02] p-3">
            <div className="flex items-center justify-between"><p className="text-sm font-semibold text-cyan">{a.title}</p><span className="chip">{a.audience}</span></div>
            <p className="mt-1 text-xs text-slate-400">{a.body}</p><p className="mt-2 font-mono text-[10px] text-slate-600">{new Date(a.created_at).toLocaleString()}</p>
          </div>)}
        </div>
      </Panel>
    </div>
  )
}

export function Settings({ data, reload }: any) {
  const [form, setForm] = useState<any>(null)
  const [saved, setSaved] = useState(false)
  useEffect(() => { setForm(data) }, [data])
  if (!form) return <div className="glass p-8 text-slate-400">Loading settings…</div>
  const set = (key: string, value: any) => setForm({ ...form, [key]: value })
  const save = async () => {
    const payload: any = {}
    for (const key of ['event_date', 'event_start_time', 'hints_enabled', 'hint_cost_marks', 'hint_mode', 'hints_auto_show', 'marks_correct', 'marks_incorrect', 'final_shortlist_enabled', 'participant_score_visibility', 'violation_threshold', 'violation_auto_submit', 'break_enabled', 'riddle_bonus_marks', 'registration_open']) payload[key] = form[key]
    await patch('/admin/settings', payload)
    setSaved(true); setTimeout(() => setSaved(false), 2500); await reload()
  }
  const saveSchedule = async () => { await patch('/admin/settings', { schedule: form.schedule }); await reload() }
  return (
    <div className="grid gap-5">
      <Panel title="Competition settings" subtitle="All changes are applied server-side and immediately affect the competition"
        action={<button className="btn btn-primary px-4 py-2" onClick={save}>{saved ? <CheckCircle2 size={15} /> : <Settings2 size={15} />} {saved ? 'Saved' : 'Save settings'}</button>}>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <div><label className="label">Event date</label><input className="field" type="date" value={form.event_date} onChange={(e) => set('event_date', e.target.value)} /></div>
          <div><label className="label">Event start time</label><input className="field" type="time" value={form.event_start_time} onChange={(e) => set('event_start_time', e.target.value)} /></div>
          <div><label className="label">Marks per correct answer</label><input className="field" type="number" value={form.marks_correct} onChange={(e) => set('marks_correct', Number(e.target.value))} /></div>
          <div><label className="label">Marks per incorrect answer</label><input className="field" type="number" value={form.marks_incorrect} onChange={(e) => set('marks_incorrect', Number(e.target.value))} /></div>
          <div><label className="label">Hint cost (marks)</label><input className="field" type="number" value={form.hint_cost_marks} onChange={(e) => set('hint_cost_marks', Number(e.target.value))} /></div>
          <div><label className="label">Hint availability</label><select className="field" value={form.hint_mode} onChange={(e) => set('hint_mode', e.target.value)}><option value="once">Once per question</option><option value="multiple">Multiple times</option></select></div>
          <div><label className="label">Violation threshold</label><input className="field" type="number" value={form.violation_threshold} onChange={(e) => set('violation_threshold', Number(e.target.value))} /></div>
          <div><label className="label">Riddle bonus marks</label><input className="field" type="number" value={form.riddle_bonus_marks} onChange={(e) => set('riddle_bonus_marks', Number(e.target.value))} /></div>
          <div><label className="label">Final round eligibility</label><select className="field" value={String(form.final_shortlist_enabled)} onChange={(e) => set('final_shortlist_enabled', e.target.value === 'true')}><option value="true">Shortlisted teams only</option><option value="false">All approved teams</option></select></div>
          {[['hints_enabled', 'Hints enabled'], ['hints_auto_show', 'Show hints automatically'], ['violation_auto_submit', 'Auto-submit at threshold'], ['break_enabled', 'Riddle & meme breaks enabled'], ['participant_score_visibility', 'Show own score to participants'], ['registration_open', 'Registration open']].map(([key, label]) => (
            <label key={key} className="flex cursor-pointer items-center justify-between rounded-xl border border-white/10 bg-white/[.02] px-4 py-3">
              <span className="text-xs text-slate-300">{label}</span><input type="checkbox" className="h-4 w-4 accent-cyan" checked={!!form[key]} onChange={(e) => set(key, e.target.checked)} />
            </label>
          ))}
        </div>
      </Panel>
      <Panel title="Event schedule editor" subtitle="All 12 activities · times in 24-hour format"
        action={<button className="btn btn-primary px-4 py-2" onClick={saveSchedule}><CalendarClock size={15} /> Save schedule</button>}>
        <div className="scroll-thin overflow-x-auto">
          <table className="table-dark"><thead><tr><th>Activity</th><th>Start</th><th>End</th><th>Type</th></tr></thead>
            <tbody>{(form.schedule || []).map((slot: any, index: number) => <tr key={slot.id}>
              <td><input className="field py-1.5" value={slot.label} onChange={(e) => { const s = [...form.schedule]; s[index] = { ...slot, label: e.target.value }; set('schedule', s) }} /></td>
              <td><input className="field w-24 py-1.5 font-mono" value={slot.start} onChange={(e) => { const s = [...form.schedule]; s[index] = { ...slot, start: e.target.value }; set('schedule', s) }} /></td>
              <td><input className="field w-24 py-1.5 font-mono" value={slot.end} onChange={(e) => { const s = [...form.schedule]; s[index] = { ...slot, end: e.target.value }; set('schedule', s) }} /></td>
              <td><span className="chip">{slot.kind}</span></td>
            </tr>)}</tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}

export function AuditLogs({ data, reload }: any) {
  return (
    <Panel title="Audit logs" subtitle="Every privileged and participant action is recorded"
      action={<button onClick={reload} className="btn btn-ghost px-3 py-2"><RefreshCw size={14} /> Refresh</button>}>
      <div className="scroll-thin max-h-[680px] overflow-auto">
        <table className="table-dark"><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Target</th><th>IP</th><th>Metadata</th></tr></thead>
          <tbody>{(data || []).map((log: any) => <tr key={log.id}>
            <td className="whitespace-nowrap font-mono text-[10px] text-slate-500">{new Date(log.created_at).toLocaleString()}</td>
            <td>{log.actor_type} #{log.actor_id}</td><td className="text-cyan">{log.action}</td><td>{log.target_type} {log.target_id}</td>
            <td className="font-mono text-[10px]">{log.ip}</td><td className="max-w-xs truncate font-mono text-[10px] text-slate-500">{JSON.stringify(log.metadata || {})}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </Panel>
  )
}
