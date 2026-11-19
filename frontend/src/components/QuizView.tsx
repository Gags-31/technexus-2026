import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Check, ChevronLeft, ChevronRight, Lightbulb, Send, Sparkles } from 'lucide-react'
import { Timer } from './Timer'
import { ApiError, post, put } from '../lib/api'

export function QuizView({ state, onState }: any) {
  const active = state.active_round
  const questions: any[] = active?.questions || []
  const [index, setIndex] = useState(0)
  const [toast, setToast] = useState('')
  const [saving, setSaving] = useState(false)
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({})
  const question = questions[index]
  const flash = (message: string) => { setToast(message); setTimeout(() => setToast(''), 2800) }

  useEffect(() => { if (index >= questions.length && questions.length) setIndex(0) }, [questions.length, index])

  const select = (option: number) => {
    if (!question || question.answer?.submitted || active.status === 'paused') return
    const qid = question.id
    state.active_round.questions = state.active_round.questions.map((q: any) =>
      q.id === qid ? { ...q, answer: { ...q.answer, selected_index: option } } : q)
    clearTimeout(timers.current[qid])
    setSaving(true)
    timers.current[qid] = setTimeout(async () => {
      try { await put('/participant/answers/' + qid, { selected_index: option }) }
      catch (err) { flash(err instanceof ApiError ? err.detail : 'Save failed') }
      finally { setSaving(false) }
    }, 350)
  }

  const submit = async () => {
    if (!question || question.answer?.submitted) return
    clearTimeout(timers.current[question.id])
    try {
      await post('/participant/answers/' + question.id + '/submit', { selected_index: question.answer.selected_index ?? 0 })
      flash('Answer submitted. It can no longer be changed.')
      await onState()
    } catch (err) { flash(err instanceof ApiError ? err.detail : 'Submission failed') }
  }

  const hint = async () => {
    if (!question) return
    try {
      const result = await post('/participant/hints/' + question.id, {})
      state.active_round.questions[index].answer.hint = result.hint
      state.active_round.questions[index].answer.hint_used = true
      flash(result.hint_cost ? 'Hint revealed · ' + result.hint_cost + ' mark penalty' : 'Hint revealed')
      await onState()
    } catch (err) { flash(err instanceof ApiError ? err.detail : 'Hint unavailable') }
  }

  if (!question) return <div className="glass rounded-2xl p-10 text-center text-slate-400">No questions available.</div>
  const answered = questions.filter((q: any) => q.answer?.selected_index !== null).length
  const submitted = questions.filter((q: any) => q.answer?.submitted).length

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_260px]">
      <div className="glass relative overflow-hidden rounded-2xl p-6 md:p-8">
        <div className="circuit" />
        <div className="relative">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="eyebrow mb-2">Question {index + 1} of {questions.length}</p>
              <div className="flex flex-wrap gap-2">
                <span className="chip">{question.domain}</span>
                <span className="chip">{question.difficulty}</span>
                <span className="chip">{question.marks} marks</span>
              </div>
            </div>
            <Timer start={active.server_start_at} ends={active.ends_at} paused={active.status === 'paused'} pausedAt={active.paused_at} />
          </div>
          <AnimatePresence mode="wait">
            <motion.div key={question.id} initial={{ opacity: 0, x: 18 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -18 }}>
              <p className="display text-lg font-semibold leading-relaxed text-white md:text-xl">{question.question}</p>
              {question.reference && <div className="mt-4 rounded-xl border border-violet/20 bg-violet/5 p-4 font-mono text-xs leading-relaxed text-violet-200"><Sparkles size={13} className="mr-2 inline" />{question.reference}</div>}
              <div className="mt-7 grid gap-3">
                {question.options.map((option: string, i: number) => (
                  <button key={i} disabled={question.answer?.submitted || active.status === 'paused'} onClick={() => select(i)}
                    className={'option-btn flex items-start gap-4 ' + (question.answer?.selected_index === i ? 'option-selected' : '') + ' ' + (question.answer?.submitted ? 'option-submitted' : '')}>
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-white/15 bg-white/5 font-mono text-xs">{String.fromCharCode(65 + i)}</span>
                    <span>{option}</span>
                    {question.answer?.selected_index === i && question.answer?.submitted && <Check size={16} className="ml-auto shrink-0 text-violet-300" />}
                  </button>
                ))}
              </div>
            </motion.div>
          </AnimatePresence>
          {question.answer?.hint && <div className="mt-5 rounded-xl border border-amber-400/25 bg-amber-400/5 p-4 text-sm text-amber-100"><Lightbulb size={15} className="mr-2 inline text-amber-300" /><b>Hint:</b> {question.answer.hint}</div>}
          <div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-6">
            <div className="flex gap-2">
              <button className="btn btn-ghost px-4 py-2" disabled={index === 0} onClick={() => setIndex(index - 1)}><ChevronLeft size={16} /> Previous</button>
              <button className="btn btn-ghost px-4 py-2" disabled={index === questions.length - 1} onClick={() => setIndex(index + 1)}>Next <ChevronRight size={16} /></button>
            </div>
            <div className="flex gap-2">
              {state.hints_enabled && <button className="btn btn-ghost px-4 py-2" onClick={hint} disabled={question.answer?.submitted}><Lightbulb size={16} /> Hint</button>}
              <button className="btn btn-primary px-5 py-2" onClick={submit} disabled={question.answer?.submitted || question.answer?.selected_index === null || active.status === 'paused'}><Send size={15} /> {question.answer?.submitted ? 'Submitted' : 'Submit answer'}</button>
            </div>
          </div>
          {saving && <span className="mt-3 block text-right font-mono text-[10px] text-cyan/70">saving…</span>}
        </div>
      </div>
      <aside className="glass h-fit rounded-2xl p-5">
        <p className="eyebrow mb-4">Question navigator</p>
        <div className="grid grid-cols-5 gap-2">
          {questions.map((q: any, i: number) => (
            <button key={q.id} onClick={() => setIndex(i)}
              className={'h-9 rounded-lg border font-mono text-xs transition ' + (i === index ? 'border-cyan bg-cyan/15 text-cyan' : q.answer?.submitted ? 'border-violet/40 bg-violet/10 text-violet-200' : q.answer?.selected_index !== null ? 'border-emerald-400/40 bg-emerald-400/10 text-emerald-200' : 'border-white/10 bg-white/5 text-slate-500')}>{i + 1}</button>
          ))}
        </div>
        <div className="mt-6 space-y-2 border-t border-white/10 pt-5 text-xs text-slate-400">
          <div className="flex justify-between"><span>Selected</span><span className="text-emerald-300">{answered}</span></div>
          <div className="flex justify-between"><span>Submitted</span><span className="text-violet-300">{submitted}</span></div>
          <div className="flex justify-between"><span>Remaining</span><span>{questions.length - submitted}</span></div>
        </div>
        <p className="mt-6 rounded-xl border border-white/10 bg-white/[.03] p-3 text-[11px] leading-relaxed text-slate-500">Answers autosave for both team members. Only one final answer per question is recorded.</p>
      </aside>
      {toast && <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-xl border border-cyan/30 bg-[#07142c] px-5 py-3 text-sm text-cyan shadow-glow">{toast}</div>}
    </div>
  )
}
