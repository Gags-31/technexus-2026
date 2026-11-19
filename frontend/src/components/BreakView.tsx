import { useEffect, useState } from 'react'
import { ApiError, get, post } from '../lib/api'
import { Timer } from './Timer'

export function BreakView({ onRefresh }: any) {
  const [data, setData] = useState<any>(null)
  const [guess, setGuess] = useState('')
  const [result, setResult] = useState<any>(null)
  const load = () => get('/participant/break').then(setData).catch(() => {})
  useEffect(() => { load() }, [])
  if (!data) return <div className="glass rounded-2xl p-10 text-center text-slate-400">Loading break content…</div>
  if (!data.enabled) return <div className="glass rounded-2xl p-10 text-center text-slate-400">Breaks are disabled for this event.</div>
  const meme = data.memes?.[0]
  const send = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!data.riddle) return
    try { setResult(await post('/participant/riddle/' + data.riddle.id + '/guess', { guess })) } catch {}
  }
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <div className="glass glow-ring relative overflow-hidden rounded-2xl p-7">
        <div className="circuit" />
        <div className="relative">
          <div className="flex items-center justify-between"><p className="eyebrow">Fun riddle break</p><span className="chip">{data.riddle?.category || 'GENERAL'}</span></div>
          {data.riddle ? <>
            <p className="display mt-6 text-xl font-semibold leading-relaxed text-white">{data.riddle.question}</p>
            <div className="mt-5"><Timer start={null} ends={data.riddle.reveal_at} paused={false} pausedAt={null} /></div>
            {data.riddle.answer ? <div className="mt-6 rounded-xl border border-emerald-400/30 bg-emerald-400/5 p-5">
              <p className="eyebrow mb-2 text-emerald-300">Answer revealed</p>
              <p className="display text-2xl font-bold text-white">{data.riddle.answer}</p>
              <p className="mt-2 text-sm text-slate-400">{data.riddle.explanation}</p>
            </div> : <form onSubmit={send} className="mt-6 grid gap-3">
              <input className="field" placeholder="Your guess…" value={guess} onChange={(e) => setGuess(e.target.value)} required />
              <button className="btn btn-primary">Submit guess</button>
            </form>}
            {result && <p className={'mt-4 text-sm ' + (result.correct ? 'text-emerald-300' : 'text-amber-300')}>{result.correct ? 'Correct!' + (result.bonus_marks ? ' +' + result.bonus_marks + ' bonus marks' : '') : 'Not quite — wait for the reveal.'}</p>}
          </> : <p className="mt-6 text-slate-400">The next round begins shortly.</p>}
        </div>
      </div>
      <div className="glass relative overflow-hidden rounded-2xl p-7">
        <p className="eyebrow mb-5">Meme break</p>
        {meme ? <div className="flex min-h-[280px] flex-col items-center justify-center rounded-2xl border border-white/10 bg-black/30 p-6 text-center">
          <div className="text-7xl">{meme.glyph}</div>
          <p className="display mt-6 text-2xl font-bold text-white">{meme.top}</p>
          <div className="my-4 h-px w-24 bg-gradient-to-r from-transparent via-cyan to-transparent" />
          <p className="display text-xl text-cyan">{meme.bottom}</p>
          <p className="mt-7 font-mono text-[10px] tracking-widest text-slate-500">{meme.category} · {meme.title}</p>
        </div> : <p className="text-slate-400">No meme scheduled.</p>}
        <button onClick={() => { load(); onRefresh?.() }} className="btn btn-ghost mt-5 w-full">Refresh break content</button>
      </div>
    </div>
  )
}
