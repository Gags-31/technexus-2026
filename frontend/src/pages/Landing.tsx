import { motion } from 'framer-motion'
import { ArrowRight, Brain, Cloud, Database, Cpu, Radio, ShieldCheck, Users, Zap, Clock, Trophy, Terminal } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Countdown, Logo, Marquee, SectionHeading, SiteFooter, SiteHeader } from '../components/Brand'
import { get } from '../lib/api'

const domains = [
  { icon: Brain, name: 'Artificial Intelligence', detail: 'Machine learning, neural networks, generative AI and model reasoning.', color: 'from-cyan/70 to-blue-500/20' },
  { icon: Cloud, name: 'Cloud Computing', detail: 'AWS services, architecture, virtualization and serverless design.', color: 'from-blue-400/70 to-violet-500/20' },
  { icon: Cpu, name: 'Operating Systems', detail: 'Scheduling, memory, concurrency, deadlocks and virtualization.', color: 'from-violet-400/70 to-fuchsia-500/20' },
  { icon: Database, name: 'Database Management', detail: 'SQL, normalization, transactions, indexing and query tuning.', color: 'from-emerald-400/70 to-cyan-500/20' },
]

const roundData = [
  { n: '01', name: 'TECH BLITZ', time: '11:30 – 11:55', duration: '25 MIN', desc: 'Rapid-fire fundamentals across all four domains.', icon: Zap },
  { n: '02', name: 'DECODE THE DOMAIN', time: '12:00 – 12:25', duration: '25 MIN', desc: 'Identify models, architectures, schedules and schemas.', icon: Terminal },
  { n: '03', name: 'TECH TROUBLESHOOTER', time: '12:40 – 13:15', duration: '35 MIN', desc: 'Diagnose realistic technical failures under pressure.', icon: ShieldCheck },
  { n: '04', name: 'NEXUS SHOWDOWN', time: '13:20 – 13:50', duration: '30 MIN', desc: 'The advanced cross-domain final for qualified teams.', icon: Trophy },
]

export default function Landing() {
  const [config, setConfig] = useState<any>(null)
  useEffect(() => { get('/public/config').then(setConfig).catch(() => {}) }, [])

  return (
    <div className="relative min-h-screen">
      <div className="cosmos" />
      <div className="circuit" />
      <SiteHeader />

      {/* HERO */}
      <section className="relative overflow-hidden px-5 pb-16 pt-16 lg:pt-24">
        <div className="mx-auto max-w-7xl">
          <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .7 }}
            className="mx-auto max-w-4xl text-center">
            <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-cyan/25 bg-cyan/5 px-4 py-2 font-mono text-[10px] tracking-[.22em] text-cyan">
              <Radio size={12} className="pulse-dot" /> OFFICIAL EVENT · AWS STUDENT BUILDER GROUP
            </div>
            <h1 className="display text-[clamp(3.6rem,12vw,9.5rem)] font-bold leading-[.84]">
              <span className="gradient-text">TECHNEXUS</span>
              <span className="block text-[.34em] tracking-[.35em] text-white/90">2026</span>
            </h1>
            <p className="mx-auto mt-7 max-w-2xl text-base leading-relaxed text-slate-300 md:text-lg">
              <span className="font-semibold text-cyan">CONNECT. THINK. CONQUER.</span><br />
              The ultimate technical quiz. Four rounds. Four domains. Two minds per team. One champion.
            </p>
            <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
              <Link to="/register" className="btn btn-primary px-7 py-4">Register your team <ArrowRight size={17} /></Link>
              <Link to="/login" className="btn btn-ghost px-7 py-4">Team login</Link>
            </div>
            <div className="mt-12 flex justify-center"><Countdown date={config?.event_date} time={config?.event_start_time} /></div>
            <p className="mt-3 font-mono text-[10px] tracking-[.2em] text-slate-500">
              {config?.event_date ? new Date(config.event_date + 'T00:00:00').toDateString().toUpperCase() : 'EVENT DATE'} · 11:00 AM ONWARDS
            </p>
          </motion.div>

          <motion.div initial={{ opacity: 0, scale: .9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: .35, duration: .9 }}
            className="relative mx-auto mt-16 max-w-5xl">
            <div className="glow-ring glass scanline overflow-hidden rounded-3xl p-2">
              <div className="grid gap-px overflow-hidden rounded-2xl bg-white/5 md:grid-cols-4">
                {domains.map((domain, i) => (
                  <motion.div key={domain.name} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: .5 + i * .12 }} className="bg-[#060d1e] px-5 py-7">
                    <domain.icon size={26} className="mb-4 text-cyan" />
                    <p className="display text-sm font-bold text-white">{domain.name}</p>
                    <p className="mt-2 text-xs leading-relaxed text-slate-500">{domain.detail}</p>
                  </motion.div>
                ))}
              </div>
            </div>
            <div className="float absolute -right-4 -top-6 hidden h-20 w-20 items-center justify-center rounded-2xl border border-violet/30 bg-violet/10 backdrop-blur lg:flex">
              <Brain className="text-violet" size={30} />
            </div>
            <div className="float absolute -bottom-6 -left-4 hidden h-16 w-16 items-center justify-center rounded-2xl border border-cyan/30 bg-cyan/10 backdrop-blur lg:flex" style={{ animationDelay: '1.5s' }}>
              <Database className="text-cyan" size={24} />
            </div>
          </motion.div>
        </div>
      </section>

      <Marquee />

      {/* DOMAINS */}
      <section id="about" className="mx-auto max-w-7xl px-5 py-24 lg:px-8">
        <SectionHeading eyebrow="01 / Competition Domains" title="Four disciplines." accent="One arena." />
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          {domains.map((domain, i) => (
            <motion.div key={domain.name} whileHover={{ y: -8 }} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
              transition={{ delay: i * .08 }} className="glass glass-hover relative overflow-hidden rounded-2xl p-6">
              <div className={`absolute -right-10 -top-10 h-32 w-32 rounded-full bg-gradient-to-br ${domain.color} blur-2xl`} />
              <div className="relative">
                <div className="mb-5 inline-flex rounded-xl border border-white/10 bg-white/5 p-3"><domain.icon size={24} className="text-cyan" /></div>
                <h3 className="display text-lg font-bold text-white">{domain.name}</h3>
                <p className="mt-3 text-sm leading-relaxed text-slate-400">{domain.detail}</p>
                <div className="mt-5 font-mono text-[10px] tracking-widest text-cyan/60">DOMAIN 0{i + 1}</div>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ROUNDS */}
      <section id="schedule" className="mx-auto max-w-7xl px-5 py-10 lg:px-8">
        <SectionHeading eyebrow="02 / The Format" title="Built to test" accent="every layer." />
        <div className="grid gap-4 lg:grid-cols-2">
          {roundData.map((round, i) => (
            <motion.div key={round.n} initial={{ opacity: 0, x: i % 2 ? 24 : -24 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }}
              className="glass glass-hover group flex gap-5 rounded-2xl p-6">
              <div className="display flex h-14 w-14 shrink-0 items-center justify-center rounded-xl border border-cyan/20 bg-cyan/5 text-2xl font-bold gradient-text">{round.n}</div>
              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-3">
                  <h3 className="display text-lg font-bold text-white">{round.name}</h3>
                  <span className="chip">{round.duration}</span>
                </div>
                <p className="mt-2 text-sm text-slate-400">{round.desc}</p>
                <p className="mt-3 font-mono text-[11px] tracking-wider text-violet/80"><Clock size={12} className="mr-1 inline" />{round.time}</p>
              </div>
              <round.icon size={22} className="text-slate-600 transition group-hover:text-cyan" />
            </motion.div>
          ))}
        </div>
      </section>

      {/* TIMELINE */}
      <section className="mx-auto max-w-7xl px-5 py-20 lg:px-8">
        <SectionHeading eyebrow="03 / Event Day" title="The complete" accent="timeline." />
        <div className="glass overflow-hidden rounded-2xl p-3">
          <div className="scroll-thin overflow-x-auto">
            <table className="table-dark">
              <thead><tr><th>Time</th><th>Activity</th><th>Type</th></tr></thead>
              <tbody>
                {(config?.schedule || []).map((slot: any) => (
                  <tr key={slot.id}>
                    <td className="whitespace-nowrap font-mono text-cyan">{slot.start} – {slot.end}</td>
                    <td className="text-slate-200">{slot.label}</td>
                    <td><span className="chip">{slot.kind}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <p className="mt-4 font-mono text-[11px] text-slate-500">All timings are configurable by the organisers from the admin console.</p>
      </section>

      {/* TEAM + ORGANISER */}
      <section className="mx-auto max-w-7xl px-5 py-10 lg:px-8">
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="glass glow-ring rounded-3xl p-8">
            <Users className="mb-5 text-cyan" size={30} />
            <h3 className="display text-2xl font-bold text-white">Exactly two. Always.</h3>
            <p className="mt-3 text-sm leading-relaxed text-slate-400">
              Every team has one leader and one member with separate accounts, one shared access code and a
              live collaborative workspace. Solo and three-person teams are rejected by the platform.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              {['1 LEADER', '1 MEMBER', '1 TEAM CODE', 'SHARED WORKSPACE'].map((x) => <span key={x} className="chip">{x}</span>)}
            </div>
          </div>
          <div className="glass rounded-3xl p-8">
            <div className="flex items-center gap-5">
              <Logo className="h-20 w-20" />
              <div>
                <p className="eyebrow mb-1">Organised by</p>
                <h3 className="display text-2xl font-bold text-white">AWS Student Builder Group</h3>
                <p className="font-mono text-[11px] tracking-widest text-cyan">AWSSBG</p>
              </div>
            </div>
            <p className="mt-5 text-sm leading-relaxed text-slate-400">
              The AWSSBG inauguration ceremony opens the day at 11:00 AM, followed by the TECHNEXUS
              introduction, four synchronised rounds, riddle breaks and the final awards.
            </p>
            <p id="about-awssbg" className="mt-4 text-sm leading-relaxed text-slate-400">
              Our mission is to help students build, experiment and ship real technology. TECHNEXUS brings
              that spirit to a competitive stage where reasoning matters more than memorisation.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-7xl px-5 py-20 lg:px-8">
        <div className="glass relative overflow-hidden rounded-3xl px-8 py-14 text-center">
          <div className="circuit" />
          <div className="relative">
            <p className="eyebrow mb-4">Ready?</p>
            <h2 className="display text-4xl font-bold text-white md:text-5xl">Two minds. <span className="gradient-text">One victory.</span></h2>
            <p className="mx-auto mt-4 max-w-xl text-sm text-slate-400">Register your team of exactly two and enter the waiting lobby before the ceremony begins.</p>
            <Link to="/register" className="btn btn-primary mt-8 px-8 py-4">Register now <ArrowRight size={17} /></Link>
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  )
}
