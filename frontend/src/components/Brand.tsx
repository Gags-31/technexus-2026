import { Link, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowUpRight, Cpu } from 'lucide-react'
import { useEffect, useState } from 'react'
import { get } from '../lib/api'

export function Logo({ className = 'h-12 w-12', title = 'AWS Student Builder Group' }: { className?: string; title?: string }) {
  return (
    <img
      src="/assets/awssbg-logo.png"
      alt={title}
      title={title}
      className={`${className} object-contain mix-blend-screen`}
    />
  )
}

export function SiteHeader() {
  const location = useLocation()
  const links = [
    { to: '/', label: 'Home' },
    { to: '/#about', label: 'About' },
    { to: '/#schedule', label: 'Schedule' },
    { to: '/register', label: 'Register' },
  ]
  return (
    <header className="sticky top-0 z-40 border-b border-white/5 bg-[#030711]/80 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5 lg:px-8">
        <Link to="/" className="flex items-center gap-3">
          <Logo className="h-10 w-10" />
          <div className="leading-tight">
            <div className="display text-sm font-bold tracking-[.18em] text-white">TECHNEXUS<span className="text-cyan"> 2026</span></div>
            <div className="font-mono text-[9px] tracking-[.22em] text-slate-500">BY AWSSBG</div>
          </div>
        </Link>
        <nav className="hidden items-center gap-7 md:flex">
          {links.map((link) => (
            <Link key={link.label} to={link.to}
              className={`text-[13px] font-medium transition hover:text-cyan ${location.pathname === link.to ? 'text-cyan' : 'text-slate-300'}`}>
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          <Link to="/login" className="btn btn-ghost hidden px-4 py-2 sm:inline-flex">Participant Login</Link>
          <Link to="/organiser/login" className="btn btn-primary px-4 py-2">Organiser <ArrowUpRight size={15} /></Link>
        </div>
      </div>
    </header>
  )
}

export function SiteFooter() {
  return (
    <footer className="relative mt-24 border-t border-white/5 bg-[#030711]/70">
      <div className="mx-auto grid max-w-7xl gap-10 px-6 py-14 md:grid-cols-3">
        <div>
          <div className="flex items-center gap-4">
            <Logo className="h-14 w-14" />
            <div>
              <p className="display text-lg font-bold tracking-wide text-white">AWS Student Builder Group</p>
              <p className="font-mono text-[11px] tracking-widest text-cyan">AWSSBG · OFFICIAL ORGANISER</p>
            </div>
          </div>
          <p className="mt-5 max-w-sm text-sm leading-relaxed text-slate-400">
            A student-led community building cloud, AI and systems skills through hands-on events.
            TECHNEXUS is our flagship technical quiz.
          </p>
        </div>
        <div>
          <p className="eyebrow mb-4">Navigate</p>
          <div className="grid gap-2 text-sm text-slate-400">
            <Link className="hover:text-cyan" to="/">Home</Link>
            <Link className="hover:text-cyan" to="/register">Team Registration</Link>
            <Link className="hover:text-cyan" to="/login">Participant Login</Link>
            <Link className="hover:text-cyan" to="/organiser/login">Organiser Console</Link>
          </div>
        </div>
        <div>
          <p className="eyebrow mb-4">Event Identity</p>
          <p className="display text-2xl font-bold gradient-text">CONNECT. THINK. CONQUER.</p>
          <p className="mt-3 text-sm text-slate-400">TECHNEXUS 2026 · THE ULTIMATE TECH QUIZ</p>
          <div className="mt-5 flex gap-2">
            {['AI', 'CLOUD', 'OS', 'DBMS'].map((tag) => <span key={tag} className="chip">{tag}</span>)}
          </div>
        </div>
      </div>
      <div className="border-t border-white/5 py-5 text-center font-mono text-[11px] tracking-widest text-slate-600">
        © 2026 AWS STUDENT BUILDER GROUP · BUILT FOR TECHNEXUS
      </div>
    </footer>
  )
}

const TERMS = [
  'ARTIFICIAL INTELLIGENCE', 'CLOUD COMPUTING', 'OPERATING SYSTEMS', 'DATABASE MANAGEMENT',
  'MACHINE LEARNING', 'GENERATIVE AI', 'AWS', 'SQL', 'NETWORKING', 'ALGORITHMS',
]

export function Marquee() {
  const content = (
    <>
      {TERMS.map((term) => <span key={term}>{term}<b>◆</b></span>)}
    </>
  )
  return (
    <div className="marquee-wrap" aria-label={TERMS.join(', ')}>
      <div className="marquee-track">
        <div className="flex">{content}</div>
        <div className="flex" aria-hidden>{content}</div>
      </div>
    </div>
  )
}

export function Countdown({ date, time }: { date?: string; time?: string }) {
  const [remaining, setRemaining] = useState<number | null>(null)
  useEffect(() => {
    if (!date) return
    const target = new Date(`${date}T${time || '11:00'}:00`).getTime()
    if (Number.isNaN(target)) return
    const tick = () => setRemaining(Math.max(0, target - Date.now()))
    tick()
    const timer = setInterval(tick, 1000)
    return () => clearInterval(timer)
  }, [date, time])
  if (remaining === null) return null
  const parts = [
    { label: 'DAYS', value: Math.floor(remaining / 86400000) },
    { label: 'HRS', value: Math.floor(remaining / 3600000) % 24 },
    { label: 'MIN', value: Math.floor(remaining / 60000) % 60 },
    { label: 'SEC', value: Math.floor(remaining / 1000) % 60 },
  ]
  return (
    <div className="flex gap-3">
      {parts.map((p) => (
        <motion.div key={p.label} whileHover={{ y: -3 }} className="glass min-w-[72px] rounded-xl px-3 py-3 text-center">
          <div className="display text-2xl font-bold text-white tabular-nums">{String(p.value).padStart(2, '0')}</div>
          <div className="font-mono text-[9px] tracking-[.2em] text-cyan/70">{p.label}</div>
        </motion.div>
      ))}
    </div>
  )
}

export function SectionHeading({ eyebrow, title, accent }: { eyebrow: string; title: string; accent?: string }) {
  return (
    <div className="mb-10">
      <p className="eyebrow mb-3">{eyebrow}</p>
      <h2 className="display text-3xl font-bold text-white md:text-4xl">{title} {accent && <span className="gradient-text">{accent}</span>}</h2>
      <div className="mt-4 h-px w-24 bg-gradient-to-r from-cyan to-transparent" />
    </div>
  )
}

export function StatusPill({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'text-emerald-300 border-emerald-400/30 bg-emerald-400/10',
    approved: 'text-emerald-300 border-emerald-400/30 bg-emerald-400/10',
    paused: 'text-amber-300 border-amber-400/30 bg-amber-400/10',
    locked: 'text-slate-400 border-slate-500/30 bg-slate-500/10',
    ended: 'text-violet-300 border-violet-400/30 bg-violet-400/10',
    pending: 'text-amber-300 border-amber-400/30 bg-amber-400/10',
    confirmed: 'text-cyan border-cyan/30 bg-cyan/10',
    rejected: 'text-rose-300 border-rose-400/30 bg-rose-400/10',
  }
  return <span className={`chip ${colors[status] || colors.locked}`}><Cpu size={11} />{status.replace('_', ' ')}</span>
}
