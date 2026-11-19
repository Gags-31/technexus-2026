import { useEffect, useState } from 'react'
import { get } from '../lib/api'

export function useServerClock() {
  const [now, setNow] = useState(Date.now())
  const [offset, setOffset] = useState(0)
  useEffect(() => {
    const sync = async () => {
      try {
        const t0 = Date.now()
        const response = await get('/time')
        const t1 = Date.now()
        setOffset(new Date(response.now).getTime() - (t0 + t1) / 2)
      } catch { /* local fallback */ }
    }
    sync()
    const a = setInterval(sync, 60000)
    const b = setInterval(() => setNow(Date.now()), 250)
    return () => { clearInterval(a); clearInterval(b) }
  }, [])
  return now + offset
}

export function Timer({ start, ends, paused, pausedAt }: any) {
  const now = useServerClock()
  const end = ends ? new Date(ends).getTime() : 0
  const from = paused && pausedAt ? new Date(pausedAt).getTime() : start ? new Date(start).getTime() : 0
  const remaining = Math.max(0, Math.floor((end - now) / 1000))
  const elapsed = Math.max(0, Math.floor((now - from) / 1000))
  return (
    <div className="flex items-center gap-4">
      <div className={`font-mono text-4xl font-bold tabular-nums ${remaining <= 60 ? 'timer-critical' : 'text-white'}`}>
        {String(Math.floor(remaining / 60)).padStart(2, '0')}:{String(remaining % 60).padStart(2, '0')}
      </div>
      <div className="text-[10px] leading-tight text-slate-500">
        <div className={paused ? 'text-amber-300' : 'text-emerald-300'}>{paused ? 'PAUSED' : 'LIVE'}</div>
        <div>ELAPSED {Math.floor(elapsed / 60)}m</div>
      </div>
    </div>
  )
}
