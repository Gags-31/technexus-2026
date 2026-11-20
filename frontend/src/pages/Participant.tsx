import { useCallback, useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import {
  KeyRound, LogOut, Maximize2, Radio, ShieldAlert, Trophy, Users, Wifi, WifiOff,
} from 'lucide-react'
import { SiteHeader, StatusPill } from '../components/Brand'
import { ApiError, get, post } from '../lib/api'
import { useSocket } from '../lib/socket'
import { QuizView } from '../components/QuizView'
import { BreakView } from '../components/BreakView'

function WaitingRoom({ me, state, onSubmit }: any) {
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [joined, setJoined] = useState(false)
  const [busy, setBusy] = useState(false)
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setBusy(true)
    try { await post('/participant/lobby', { code }); setJoined(true); await onSubmit() }
    catch (err) { setError(err instanceof ApiError ? err.detail : 'Code validation failed') }
    finally { setBusy(false) }
  }
  return (
    <div className="glass relative overflow-hidden rounded-3xl p-8 text-center md:p-12">
      <div className="circuit" />
      <div className="relative">
        <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-2xl border border-cyan/25 bg-cyan/5"><Radio size={34} className="pulse-dot text-cyan" /></div>
        <p className="eyebrow mb-3">Virtual waiting lobby</p>
        <h2 className="display text-3xl font-bold text-white">{joined ? 'You are in. Stay connected.' : 'Enter your team access code'}</h2>
        <p className="mx-auto mt-3 max-w-lg text-sm text-slate-400">
          {joined
            ? `Welcome ${me.participant.full_name}. All rounds are centrally controlled. Watch for the organiser START signal.`
            : 'Both members share one code. It is required to join a round and is not a substitute for individual login.'}
        </p>
        {!joined && (
          <form onSubmit={submit} className="mx-auto mt-8 max-w-md">
            <div className="relative">
              <KeyRound size={17} className="absolute left-4 top-1/2 -translate-y-1/2 text-cyan" />
              <input className="field code-text py-4 pl-12 text-center text-xl uppercase" placeholder="TNX-XXXXXX" value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} maxLength={10} required />
            </div>
            {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}
            <button className="btn btn-primary mt-4 w-full" disabled={busy}>{busy ? 'Verifying…' : 'Join waiting lobby'}</button>
          </form>
        )}
        <div className="mx-auto mt-10 grid max-w-2xl gap-3 sm:grid-cols-4">
          {(state?.rounds || []).map((r: any) => (
            <div key={r.id} className={`rounded-xl border p-4 ${r.status === 'active' ? 'border-cyan/40 bg-cyan/10' : 'border-white/10 bg-white/[.02]'}`}>
              <p className="font-mono text-[10px] tracking-widest text-slate-500">ROUND {r.id}</p>
              <p className="mt-2 text-xs font-semibold text-white">{r.short_name}</p>
              <p className="mt-2"><StatusPill status={r.status} /></p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function ResultsMini() {
  const [result, setResult] = useState<any>(null)
  useEffect(() => { get('/participant/results').then(setResult).catch(() => {}) }, [])
  if (!result?.available || !result.results) return null
  return (
    <div className="glass mt-6 rounded-2xl p-6">
      <div className="flex items-center gap-3"><Trophy className="text-amber-300" /><p className="display text-xl font-bold text-white">Your official result · Rank #{result.results.rank}</p></div>
      <p className="mt-2 text-sm text-slate-400">Total {result.results.total} · Correct {result.results.correct} · Incorrect {result.results.incorrect} · Unanswered {result.results.unanswered}</p>
    </div>
  )
}

export default function ParticipantDashboard() {
  const [me, setMe] = useState<any>(null)
  const [state, setState] = useState<any>(null)
  const [announcements, setAnnouncements] = useState<any[]>([])
  const [toast, setToast] = useState('')
  const [loading, setLoading] = useState(true)
  const [violations, setViolations] = useState(0)
  const [fullscreen, setFullscreen] = useState(false)
  const [socketInfo, setSocketInfo] = useState('connecting')
  const activeRound = !!state?.active_round && ['active', 'paused'].includes(state.active_round.status)
  const showBreak = !activeRound && state?.latest_ended_round && state?.break_enabled

  const refreshMe = useCallback(async () => { try { setMe(await get('/participant/me')) } catch { /* ignore */ } }, [])
  const refreshState = useCallback(async () => { try { setState(await get('/participant/state')) } catch { /* ignore */ } }, [])

  useEffect(() => {
    Promise.all([get('/auth/me'), refreshMe(), refreshState(), get('/participant/announcements').then(setAnnouncements)])
      .then(([auth]) => { if (!auth.authenticated || auth.kind !== 'participant') window.location.href = '/login' })
      .catch(() => { window.location.href = '/login' })
      .finally(() => setLoading(false))
  }, [refreshMe, refreshState])

  const onSocketEvent = useCallback((message: any) => {
    const { event, payload } = message
    if (['round.started', 'round.paused', 'round.resumed', 'round.ended', 'results.published', 'team.reinstated', 'team.disqualified', 'event.reset', 'event.restarted'].includes(event)) {
      setToast(payload?.message || `Event: ${event.replace('.', ' ')}`)
      setTimeout(() => setToast(''), 5000)
      refreshState(); refreshMe()
    }
    if (event === 'announcement') { setAnnouncements((prev) => [payload, ...prev].slice(0, 10)); setToast(payload.title) }
    if (event === 'answer.updated' || event === 'answer.submitted') refreshState()
    if (event === 'violation.warning') {
      setViolations(payload.count)
      setToast(`Monitoring warning ${payload.count}/${payload.threshold} — ${payload.action.replace('_', ' ')}`)
    }
  }, [refreshState, refreshMe])
  const { connected } = useSocket(!!me, onSocketEvent)
  useEffect(() => { setSocketInfo(connected ? 'connected' : 'reconnecting') }, [connected])

  const reportViolation = useCallback((kind: string, detail: string) => {
    post('/participant/violations', { kind, detail }).then((result: any) => setViolations(result.count)).catch(() => {})
  }, [])
  const lastExit = useRef(0)
  useEffect(() => {
    if (!activeRound) return
    const report = (kind: string, detail: string) => {
      const stamp = Date.now()
      if (kind === 'fullscreen_exit' && stamp - lastExit.current < 1500) return
      if (kind === 'fullscreen_exit') lastExit.current = stamp
      reportViolation(kind, detail)
    }
    const visibility = () => { if (document.hidden) report('tab_hidden', 'Browser tab became hidden') }
    const blur = () => report('window_blur', 'Browser window lost focus')
    const fullscreen = () => { if (!document.fullscreenElement) report('fullscreen_exit', 'Fullscreen exited') }
    document.addEventListener('visibilitychange', visibility)
    window.addEventListener('blur', blur)
    document.addEventListener('fullscreenchange', fullscreen)
    return () => {
      document.removeEventListener('visibilitychange', visibility)
      window.removeEventListener('blur', blur)
      document.removeEventListener('fullscreenchange', fullscreen)
    }
  }, [activeRound, reportViolation])
  useEffect(() => {
    const handler = () => setFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', handler)
    return () => document.removeEventListener('fullscreenchange', handler)
  }, [])

  if (loading) return <div className="flex min-h-screen items-center justify-center text-cyan">Loading participant workspace…</div>
  if (!me) return null
  const team = me.team

  return (
    <div className="relative min-h-screen">
      <div className="cosmos" /><div className="circuit" />
      <SiteHeader />
      <main className="relative mx-auto max-w-7xl px-5 pb-16 pt-8">
        <div className="mb-7 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="eyebrow mb-2">Participant workspace</p>
            <h1 className="display text-3xl font-bold text-white">Welcome back, <span className="gradient-text">{me.participant.full_name}</span></h1>
            <p className="mt-1 text-sm text-slate-400">{team.name} · {team.college} · {me.participant.role === 'leader' ? 'Team Leader' : 'Team Member'}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`chip ${connected ? 'text-emerald-300' : 'text-amber-300'}`}>{connected ? <Wifi size={12} /> : <WifiOff size={12} />} {socketInfo}</span>
            {activeRound && <span className={`chip ${fullscreen ? 'text-emerald-300' : 'text-amber-300'}`}><Maximize2 size={12} /> {fullscreen ? 'FULLSCREEN' : 'FULLSCREEN OFF'}</span>}
            <a className="btn btn-ghost px-3 py-2" href="/"><LogOut size={15} /></a>
          </div>
        </div>
        {toast && <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className="mb-5 flex items-center gap-3 rounded-xl border border-cyan/30 bg-cyan/10 px-5 py-3 text-sm text-cyan"><Radio size={16} />{toast}</motion.div>}

        <div className="mb-6 grid gap-4 lg:grid-cols-4">
          <div className="glass glow-ring rounded-2xl p-5 lg:col-span-2">
            <div className="flex items-center justify-between">
              <div>
                <p className="eyebrow mb-1">Team identity</p>
                <p className="display text-xl font-bold text-white">{team.name}</p>
                <p className="font-mono text-xs text-cyan">{team.public_id}</p>
              </div>
              <StatusPill status={team.status} />
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              {team.members.map((member: any) => <span key={member.id} className="chip"><Users size={11} />{member.full_name} · {member.role}{member.confirmed ? ' ✓' : ' pending'}</span>)}
            </div>
            <div className="mt-6 rounded-xl border border-cyan/25 bg-cyan/5 p-4">
              <p className="eyebrow mb-2">Unique team access code</p>
              <p className="code-text display text-3xl font-bold text-cyan">{team.code?.value || '—'}</p>
              <p className="mt-2 text-[11px] text-slate-500">Shown identically to both members. Keep it confidential.</p>
            </div>
          </div>
          <div className="glass rounded-2xl p-5">
            <p className="eyebrow mb-4">Round progress</p>
            <div className="grid gap-2">
              {(state?.rounds || []).map((r: any) => (
                <div key={r.id} className="flex items-center justify-between rounded-lg border border-white/5 bg-white/[.02] px-3 py-2">
                  <span className="text-xs text-slate-300">R{r.id} · {r.short_name}</span><StatusPill status={r.status} />
                </div>
              ))}
            </div>
          </div>
          <div className="glass rounded-2xl p-5">
            <p className="eyebrow mb-4">Monitoring</p>
            <div className="flex items-center gap-4">
              <ShieldAlert size={28} className={violations ? 'text-amber-300' : 'text-emerald-300'} />
              <div><p className="display text-2xl font-bold text-white">{violations}/{state?.violation_threshold ?? 3}</p><p className="text-[11px] text-slate-500">browser violations</p></div>
            </div>
            <p className="mt-4 text-[11px] leading-relaxed text-slate-500">Fullscreen, tab focus and visibility are monitored. Policy disclosed before competition.</p>
            {activeRound && !fullscreen && <button className="btn btn-ghost mt-4 w-full py-2" onClick={() => document.documentElement.requestFullscreen?.()}>Enter fullscreen</button>}
          </div>
        </div>

        {announcements.length > 0 && (
          <div className="glass mb-6 rounded-2xl p-5">
            <p className="eyebrow mb-3">Announcements</p>
            <div className="grid gap-2 md:grid-cols-2">
              {announcements.slice(0, 4).map((a: any) => <div key={a.id} className="rounded-xl border border-white/5 bg-white/[.02] p-3"><p className="text-sm font-semibold text-cyan">{a.title}</p><p className="mt-1 text-xs text-slate-400">{a.body}</p></div>)}
            </div>
          </div>
        )}

        {activeRound ? <QuizView state={state} onState={refreshState} /> : showBreak ? <BreakView onRefresh={refreshState} /> : <WaitingRoom me={me} state={state} onSubmit={refreshState} />}
        {state?.participant_score_visibility && state?.results_published && <ResultsMini />}
      </main>
    </div>
  )
}
