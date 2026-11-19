import { motion } from 'framer-motion'
import { AlertOctagon, CircleHelp } from 'lucide-react'

export function Panel({ title, subtitle, action, children }: any) {
  return (
    <div className="glass rounded-2xl p-5 md:p-6">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="display text-lg font-bold text-white">{title}</h2>
          {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </div>
  )
}

export function Stat({ label, value, icon: Icon, color }: any) {
  return (
    <div className="glass glass-hover rounded-xl p-4">
      <div className="flex items-center justify-between">
        <p className="font-mono text-[10px] tracking-[.16em] text-slate-500">{label}</p>
        <Icon size={15} className={color || 'text-cyan'} />
      </div>
      <p className="display mt-3 text-3xl font-bold text-white">{value}</p>
    </div>
  )
}

export function ConfirmDialog({ title, body, confirmLabel, danger, onConfirm, onCancel }: any) {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-5 backdrop-blur-sm">
      <motion.div initial={{ scale: .94, y: 12 }} animate={{ scale: 1, y: 0 }} className="glass w-full max-w-md rounded-2xl p-7">
        <div className={`mb-4 inline-flex rounded-xl p-3 ${danger ? 'bg-rose-400/10 text-rose-300' : 'bg-cyan/10 text-cyan'}`}>
          {danger ? <AlertOctagon size={24} /> : <CircleHelp size={24} />}
        </div>
        <h3 className="display text-xl font-bold text-white">{title}</h3>
        <p className="mt-2 text-sm leading-relaxed text-slate-400">{body}</p>
        <div className="mt-7 flex gap-3">
          <button className="btn btn-ghost flex-1" onClick={onCancel}>Cancel</button>
          <button className={`btn flex-1 ${danger ? 'btn-danger' : 'btn-primary'}`} onClick={onConfirm}>{confirmLabel || 'Confirm'}</button>
        </div>
      </motion.div>
    </motion.div>
  )
}
