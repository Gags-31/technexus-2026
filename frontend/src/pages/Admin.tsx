import { useCallback, useEffect, useState } from 'react'
import {
  Activity, Award, BookOpen, ChevronRight, Eye, FileText, KeyRound, LayoutDashboard,
  LogOut, Megaphone, RefreshCw, Settings2, Shield, ShieldAlert, Sparkles, Timer, Trophy, Users,
} from 'lucide-react'
import { Logo } from '../components/Brand'
import { ApiError, get, post } from '../lib/api'
import { useSocket } from '../lib/socket'
import { Overview, Registrations, Teams } from './AdminOverview'
import { Monitor, RoundManagement, Scoreboard } from './AdminLive'
import {
  Announcements, AuditLogs, Breaks, QuestionBank, Results, Settings, Violations,
} from './AdminSectionsB'

const SECTIONS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'registrations', label: 'Participant Registrations', icon: Users },
  { id: 'teams', label: 'Team Management', icon: KeyRound },
  { id: 'questions', label: 'Question Bank', icon: BookOpen },
  { id: 'answers', label: 'Answer Key & Explanations', icon: Eye },
  { id: 'rounds', label: 'Round Management', icon: Timer },
  { id: 'monitor', label: 'Live Competition Monitor', icon: Activity },
  { id: 'scoreboard', label: 'Live Scoreboard', icon: Trophy },
  { id: 'violations', label: 'Anti-Cheating Monitor', icon: ShieldAlert },
  { id: 'breaks', label: 'Riddle & Meme Management', icon: Sparkles },
  { id: 'results', label: 'Results', icon: Award },
  { id: 'announcements', label: 'Announcements', icon: Megaphone },
  { id: 'settings', label: 'Admin Settings', icon: Settings2 },
  { id: 'audit', label: 'Audit Logs', icon: FileText },
]

export default function AdminDashboard() {
  const [section, setSection] = useState('overview')
  const [auth, setAuth] = useState<any>(null)
  const [data, setData] = useState<Record<string, any>>({})
  const [toast, setToast] = useState('')

  const loaders: Record<string, () => Promise<any>> = {
    overview: () => get('/admin/overview'),
    registrations: () => get('/admin/registrations'),
    teams: () => get('/admin/teams'),
    questions: () => get('/admin/questions'),
    answers: () => get('/admin/questions'),
    rounds: () => get('/admin/rounds'),
    monitor: () => get('/admin/monitor'),
    scoreboard: () => get('/admin/scoreboard'),
    violations: () => get('/admin/violations'),
    breaks: async () => ({ riddles: await get('/admin/riddles'), memes: await get('/admin/memes') }),
    results: () => get('/admin/results'),
    announcements: () => get('/admin/announcements'),
    settings: () => get('/admin/settings'),
    audit: () => get('/admin/audit-logs'),
  }

  const load = useCallback(async (key = section) => {
    try {
      const value = await loaders[key]()
      setData((prev) => ({ ...prev, [key]: value }))
    }
    catch (err) {
      if (err instanceof ApiError && err.status === 401) window.location.href = '/organiser/login'
    }
  }, [section])

  const refreshAll = useCallback(async () => {
    await Promise.all(Object.keys(loaders).map(async (key) => {
      try { const value = await loaders[key](); setData((prev) => ({ ...prev, [key]: value })) }
      catch { /* individual failures are non-fatal */ }
    }))
  }, [])

  useEffect(() => {
    get('/auth/me').then((result) => {
      if (!result.authenticated || result.kind !== 'administrator') { window.location.href = '/organiser/login'; return }
      if (result.must_change_password) { window.location.href = '/change-password'; return }
      setAuth(result)
    }).catch(() => { window.location.href = '/organiser/login' })
    refreshAll()
  }, [refreshAll])

  useEffect(() => { if (section && !data[section]) load(section) }, [section, data, load])

  const onSocketEvent = useCallback((message: any) => {
    const { event, payload } = message
    if (event === 'violation.alert') {
      setToast(`${payload.team_name}: ${payload.kind} (${payload.count})`)
      setTimeout(() => setToast(''), 4000)
    }
    if (['round.changed', 'scoreboard.updated', 'results.published', 'round.ended', 'event.reset', 'event.restarted'].includes(event)) {
      load('overview'); load('rounds')
      if (section === 'scoreboard') load('scoreboard')
      if (section === 'monitor') load('monitor')
      if (section === 'results') load('results')
    }
  }, [load, section])
  useSocket(!!auth, onSocketEvent)

  const logout = async () => { await post('/auth/logout', {}); window.location.href = '/organiser/login' }
  const current = SECTIONS.find((s) => s.id === section) || SECTIONS[0]

  return (
    <div className="relative min-h-screen">
      <div className="cosmos" /><div className="circuit" />
      <div className="relative flex">
        <aside className="sticky top-0 hidden h-screen w-72 shrink-0 flex-col border-r border-white/5 bg-[#040a18]/90 p-5 backdrop-blur-xl lg:flex">
          <div className="mb-7 flex items-center gap-3 border-b border-white/5 pb-5">
            <Logo className="h-11 w-11" />
            <div>
              <p className="display text-xs font-bold tracking-widest text-white">TECHNEXUS 2026</p>
              <p className="font-mono text-[9px] tracking-widest text-cyan">ORGANISER COMMAND</p>
            </div>
          </div>
          <nav className="scroll-thin flex-1 space-y-1 overflow-y-auto">
            {SECTIONS.map((item) => (
              <button key={item.id} onClick={() => setSection(item.id)}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-xs font-medium transition ${section === item.id ? 'bg-cyan/10 text-cyan shadow-[inset_2px_0_0_#22e6ff]' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}>
                <item.icon size={15} /> {item.label} <ChevronRight size={12} className="ml-auto opacity-40" />
              </button>
            ))}
          </nav>
          <div className="mt-4 border-t border-white/5 pt-4">
            <p className="font-mono text-[10px] text-slate-500">SIGNED IN AS</p>
            <p className="mt-1 text-sm font-semibold text-white">{auth?.name || 'Organiser'}</p>
            <p className="font-mono text-[10px] text-cyan">{auth?.role || 'administrator'}</p>
            <button onClick={logout} className="btn btn-ghost mt-4 w-full py-2"><LogOut size={14} /> Sign out</button>
          </div>
        </aside>

        <main className="min-w-0 flex-1 px-5 py-7 lg:px-8">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="eyebrow mb-2">TECHNEXUS 2026 · Organiser dashboard</p>
              <h1 className="display text-2xl font-bold text-white md:text-3xl">{current.label}</h1>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className="chip text-emerald-300"><Shield size={12} /> RBAC VERIFIED</span>
              <button onClick={refreshAll} className="btn btn-ghost px-3 py-2"><RefreshCw size={14} /> Sync all</button>
            </div>
          </div>
          <div className="mb-5 flex gap-1 overflow-x-auto pb-2 lg:hidden">
            {SECTIONS.map((item) => (
              <button key={item.id} onClick={() => setSection(item.id)} className={`chip whitespace-nowrap ${section === item.id ? 'text-cyan' : ''}`}>{item.label}</button>
            ))}
          </div>
          {toast && <div className="mb-5 rounded-xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-200"><ShieldAlert size={14} className="mr-2 inline" />{toast}</div>}

          {section === 'overview' && <Overview data={data.overview} reload={() => load('overview')} />}
          {section === 'registrations' && <Registrations data={data.registrations} reload={() => load('registrations')} />}
          {section === 'teams' && <Teams data={data.teams} reload={() => load('teams')} />}
          {(section === 'questions' || section === 'answers') && <QuestionBank data={data.questions} answers={section === 'answers'} />}
          {section === 'rounds' && <RoundManagement data={data.rounds} reload={() => load('rounds')} refreshAll={refreshAll} />}
          {section === 'monitor' && <Monitor data={data.monitor} reload={() => load('monitor')} />}
          {section === 'scoreboard' && <Scoreboard data={data.scoreboard} reload={() => load('scoreboard')} />}
          {section === 'violations' && <Violations data={data.violations} reload={() => load('violations')} />}
          {section === 'breaks' && <Breaks riddles={data.breaks?.riddles} memes={data.breaks?.memes} reload={() => load('breaks')} />}
          {section === 'results' && <Results data={data.results} reload={() => load('results')} />}
          {section === 'announcements' && <Announcements data={data.announcements} reload={() => load('announcements')} />}
          {section === 'settings' && <Settings data={data.settings} reload={() => load('settings')} />}
          {section === 'audit' && <AuditLogs data={data.audit} reload={() => load('audit')} />}
        </main>
      </div>
    </div>
  )
}
