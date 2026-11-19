import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, ArrowRight, Eye, EyeOff, KeyRound, Lock, Mail, Shield, User, Users } from 'lucide-react'
import { Logo } from '../components/Brand'
import { ApiError, post } from '../lib/api'

function AuthShell({ title, subtitle, children, footer }: any) {
  return (
    <div className="relative flex min-h-screen items-center justify-center px-5 py-12">
      <div className="cosmos" /><div className="circuit" />
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="relative w-full max-w-lg">
        <Link to="/" className="mb-7 inline-flex items-center gap-2 text-xs text-slate-400 hover:text-cyan"><ArrowLeft size={14} /> Back to home</Link>
        <div className="glass glow-ring rounded-3xl p-7 md:p-9">
          <div className="mb-7 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Logo className="h-12 w-12" />
              <div>
                <p className="display text-sm font-bold tracking-widest text-white">TECHNEXUS 2026</p>
                <p className="font-mono text-[10px] tracking-[.18em] text-cyan">BY AWSSBG</p>
              </div>
            </div>
            <div className="rounded-xl border border-cyan/20 bg-cyan/5 p-2"><Shield size={20} className="text-cyan" /></div>
          </div>
          <h1 className="display text-3xl font-bold text-white">{title}</h1>
          <p className="mt-2 text-sm text-slate-400">{subtitle}</p>
          <div className="mt-7">{children}</div>
        </div>
        {footer && <div className="mt-5 text-center text-sm text-slate-400">{footer}</div>}
      </motion.div>
    </div>
  )
}

function PasswordField({ value, onChange, placeholder = 'Password', autoComplete = 'current-password' }: any) {
  const [show, setShow] = useState(false)
  return (
    <div className="relative">
      <Lock size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" />
      <input className="field pl-11 pr-12" type={show ? 'text' : 'password'} value={value}
        onChange={(e) => onChange(e.target.value)} placeholder={placeholder} autoComplete={autoComplete} required />
      <button type="button" onClick={() => setShow(!show)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-cyan" aria-label="Toggle password visibility">
        {show ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  )
}

export function ParticipantLogin() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [forgot, setForgot] = useState(false)
  const [resetEmail, setResetEmail] = useState('')
  const [token, setToken] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      await post('/auth/participant/login', { email, password })
      navigate('/dashboard')
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Login failed')
    } finally { setLoading(false) }
  }
  const requestReset = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      const result = await post('/auth/forgot-password', { email: resetEmail, actor_type: 'participant' })
      setToken(result.reset_token || '')
    } catch (err) { setError(err instanceof ApiError ? err.detail : 'Request failed') }
    finally { setLoading(false) }
  }

  return (
    <AuthShell title="Team login" subtitle="Each team member signs in with their own account."
      footer={<>New team? <Link className="font-semibold text-cyan" to="/register">Register here</Link> · <Link className="text-slate-400 hover:text-cyan" to="/organiser/login">Organiser login</Link></>}>
      {forgot ? (
        <form onSubmit={requestReset} className="grid gap-4">
          <p className="rounded-xl border border-cyan/20 bg-cyan/5 p-3 text-xs text-cyan">Enter the email used at registration. The single-use reset token is returned here for this offline event.</p>
          <div><label className="label">Email</label><div className="relative"><Mail size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" /><input className="field pl-11" type="email" value={resetEmail} onChange={(e) => setResetEmail(e.target.value)} required /></div></div>
          {error && <p className="text-sm text-rose-400">{error}</p>}
          <button className="btn btn-primary w-full" disabled={loading}>{loading ? 'Please wait…' : 'Issue reset token'}</button>
          {token && <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/5 p-4">
            <p className="text-xs text-emerald-300">Reset token (valid 30 minutes)</p>
            <code className="mt-2 block break-all font-mono text-xs text-white">{token}</code>
            <Link to={`/reset-password?token=${encodeURIComponent(token)}`} className="btn btn-ghost mt-3 w-full">Set a new password</Link>
          </div>}
          <button type="button" onClick={() => setForgot(false)} className="text-xs text-slate-400 hover:text-cyan">← Back to login</button>
        </form>
      ) : (
        <form onSubmit={submit} className="grid gap-4">
          <div><label className="label">Email address</label><div className="relative"><Mail size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" /><input className="field pl-11" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required /></div></div>
          <div><label className="label">Password</label><PasswordField value={password} onChange={setPassword} /></div>
          {error && <p className="text-sm text-rose-400">{error}</p>}
          <button className="btn btn-primary w-full py-4" disabled={loading}>{loading ? 'Signing in…' : 'Sign in'} <ArrowRight size={16} /></button>
          <button type="button" onClick={() => setForgot(true)} className="text-xs text-slate-400 hover:text-cyan">Forgot password?</button>
        </form>
      )}
    </AuthShell>
  )
}

export function AdminLogin() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [forgot, setForgot] = useState(false)
  const [resetEmail, setResetEmail] = useState('')
  const [token, setToken] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      const result = await post('/auth/admin/login', { username, password })
      navigate(result.must_change_password ? '/change-password' : '/organiser')
    } catch (err) { setError(err instanceof ApiError ? err.detail : 'Login failed') }
    finally { setLoading(false) }
  }
  const requestReset = async (e: React.FormEvent) => {
    e.preventDefault(); setLoading(true); setError('')
    try {
      const result = await post('/auth/forgot-password', { email: resetEmail, actor_type: 'administrator' })
      setToken(result.reset_token || '')
    } catch (err) { setError(err instanceof ApiError ? err.detail : 'Request failed') }
    finally { setLoading(false) }
  }

  return (
    <AuthShell title="Organiser console" subtitle="Restricted access · Authorised AWSSBG administrators only."
      footer={<Link className="text-slate-400 hover:text-cyan" to="/login">← Participant login</Link>}>
      {forgot ? (
        <form onSubmit={requestReset} className="grid gap-4">
          <div><label className="label">Admin email</label><input className="field" type="email" value={resetEmail} onChange={(e) => setResetEmail(e.target.value)} required /></div>
          {error && <p className="text-sm text-rose-400">{error}</p>}
          <button className="btn btn-primary w-full" disabled={loading}>Issue reset token</button>
          {token && <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/5 p-4">
            <p className="text-xs text-emerald-300">Reset token</p><code className="mt-2 block break-all font-mono text-xs text-white">{token}</code>
            <Link to={`/reset-password?token=${encodeURIComponent(token)}`} className="btn btn-ghost mt-3 w-full">Set a new password</Link>
          </div>}
          <button type="button" onClick={() => setForgot(false)} className="text-xs text-slate-400 hover:text-cyan">← Back</button>
        </form>
      ) : (
        <form onSubmit={submit} className="grid gap-4">
          <div><label className="label">Username or email</label><div className="relative"><User size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" /><input className="field pl-11" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required /></div></div>
          <div><label className="label">Password</label><PasswordField value={password} onChange={setPassword} /></div>
          {error && <p className="text-sm text-rose-400">{error}</p>}
          <button className="btn btn-primary w-full py-4" disabled={loading}>{loading ? 'Verifying…' : 'Access command centre'} <ArrowRight size={16} /></button>
          <button type="button" onClick={() => setForgot(true)} className="text-xs text-slate-400 hover:text-cyan">Forgot password?</button>
        </form>
      )}
    </AuthShell>
  )
}

export function ResetPassword() {
  const navigate = useNavigate()
  const params = new URLSearchParams(window.location.search)
  const [token, setToken] = useState(params.get('token') || '')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setError('')
    try { await post('/auth/reset-password', { token, new_password: password }); setDone(true) }
    catch (err) { setError(err instanceof ApiError ? err.detail : 'Reset failed') }
  }
  return (
    <AuthShell title="Reset password" subtitle="Choose a strong new password for your account.">
      {done ? <div className="text-center"><KeyRound size={36} className="mx-auto text-emerald-400" /><p className="mt-4 text-sm text-slate-300">Password updated.</p><button onClick={() => navigate('/login')} className="btn btn-primary mt-6">Continue to login</button></div> : (
        <form onSubmit={submit} className="grid gap-4">
          <div><label className="label">Reset token</label><input className="field font-mono text-xs" value={token} onChange={(e) => setToken(e.target.value)} required /></div>
          <div><label className="label">New password</label><PasswordField value={password} onChange={setPassword} placeholder="New password" autoComplete="new-password" /></div>
          <p className="text-xs text-slate-500">Minimum 10 characters with at least three character classes.</p>
          {error && <p className="text-sm text-rose-400">{error}</p>}
          <button className="btn btn-primary w-full">Update password</button>
        </form>
      )}
    </AuthShell>
  )
}

export function ChangePassword() {
  const navigate = useNavigate()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [error, setError] = useState('')
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setError('')
    try { await post('/auth/change-password', { current_password: current, new_password: next }); navigate('/organiser') }
    catch (err) { setError(err instanceof ApiError ? err.detail : 'Update failed') }
  }
  return (
    <AuthShell title="Change temporary password" subtitle="Security policy: every organiser must replace their temporary password before continuing.">
      <form onSubmit={submit} className="grid gap-4">
        <div><label className="label">Temporary password</label><PasswordField value={current} onChange={setCurrent} /></div>
        <div><label className="label">New password</label><PasswordField value={next} onChange={setNext} placeholder="New password" autoComplete="new-password" /></div>
        {error && <p className="text-sm text-rose-400">{error}</p>}
        <button className="btn btn-primary w-full">Set new password <ArrowRight size={16} /></button>
      </form>
    </AuthShell>
  )
}

export function Register() {
  const navigate = useNavigate()
  const [form, setForm] = useState<any>({
    team_name: '', college: '', department: '', semester: '',
    leader: { full_name: '', email: '', mobile: '', password: '' },
    member: { full_name: '', email: '', mobile: '', password: '' },
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [created, setCreated] = useState<any>(null)
  const set = (path: string[], value: string) => {
    setForm((prev: any) => {
      const copy = structuredClone(prev)
      let cursor = copy
      for (const key of path.slice(0, -1)) cursor = cursor[key]
      cursor[path[path.length - 1]] = value
      return copy
    })
  }
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      const result = await post('/registration', form)
      setCreated(result.team)
    } catch (err) { setError(err instanceof ApiError ? err.detail : 'Registration failed') }
    finally { setLoading(false) }
  }
  if (created) {
    return (
      <AuthShell title="Team registered" subtitle="Both members must sign in and confirm participation before approval.">
        <div className="text-center">
          <div className="mx-auto mb-5 inline-flex rounded-2xl border border-emerald-400/30 bg-emerald-400/10 p-4"><Users className="text-emerald-300" size={28} /></div>
          <p className="display text-xl font-bold text-white">{created.name}</p>
          <p className="mt-1 font-mono text-xs text-cyan">{created.public_id}</p>
          <div className="glow-ring mt-7 rounded-2xl border border-cyan/25 bg-cyan/5 p-6">
            <p className="eyebrow mb-2">Your unique team access code</p>
            <p className="code-text display text-3xl font-bold text-cyan">{created.code?.value}</p>
            <p className="mt-3 text-xs text-slate-400">Both members see this same code after signing in. Keep it private.</p>
          </div>
          <div className="mt-7 rounded-xl border border-white/10 bg-white/5 p-4 text-left">
            <p className="eyebrow mb-3">Next steps</p>
            <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-300">
              <li>Both members sign in separately.</li>
              <li>Both click <b>Confirm participation</b>.</li>
              <li>Wait for organiser approval.</li>
              <li>Enter the team code in the waiting lobby.</li>
            </ol>
          </div>
          <button onClick={() => navigate('/login')} className="btn btn-primary mt-7 w-full">Go to participant login <ArrowRight size={16} /></button>
        </div>
      </AuthShell>
    )
  }
  return (
    <div className="relative min-h-screen px-5 py-12">
      <div className="cosmos" /><div className="circuit" />
      <div className="relative mx-auto max-w-3xl">
        <Link to="/" className="mb-6 inline-flex items-center gap-2 text-xs text-slate-400 hover:text-cyan"><ArrowLeft size={14} /> Back to home</Link>
        <div className="glass rounded-3xl p-6 md:p-9">
          <div className="mb-8 flex items-center gap-4">
            <Logo className="h-14 w-14" />
            <div><h1 className="display text-3xl font-bold text-white">Register your team</h1><p className="text-sm text-slate-400">Exactly two members — one leader and one member.</p></div>
          </div>
          <form onSubmit={submit} className="grid gap-8">
            <section>
              <p className="eyebrow mb-4">01 / Team details</p>
              <div className="grid gap-4 md:grid-cols-2">
                {[['team_name', 'Team name'], ['college', 'College name'], ['department', 'Department'], ['semester', 'Semester']].map(([key, label]) => (
                  <div key={key}><label className="label">{label}</label><input className="field" value={form[key]} onChange={(e) => set([key], e.target.value)} required /></div>
                ))}
              </div>
            </section>
            {[['leader', 'Team Leader', '01'], ['member', 'Team Member', '02']].map(([key, label, num]) => (
              <section key={key} className="rounded-2xl border border-white/10 bg-white/[.02] p-5">
                <p className="eyebrow mb-4">{num} / {label}</p>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="md:col-span-2"><label className="label">Full name</label><div className="relative"><User size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" /><input className="field pl-11" value={form[key].full_name} onChange={(e) => set([key, 'full_name'], e.target.value)} required /></div></div>
                  <div><label className="label">Email</label><div className="relative"><Mail size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500" /><input className="field pl-11" type="email" value={form[key].email} onChange={(e) => set([key, 'email'], e.target.value)} required /></div></div>
                  <div><label className="label">Mobile number</label><input className="field" value={form[key].mobile} onChange={(e) => set([key, 'mobile'], e.target.value)} required /></div>
                  <div className="md:col-span-2"><label className="label">Password</label><PasswordField value={form[key].password} onChange={(v: string) => set([key, 'password'], v)} placeholder="At least 10 characters" autoComplete="new-password" /></div>
                </div>
              </section>
            ))}
            {error && <p className="rounded-xl border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-300">{error}</p>}
            <button className="btn btn-primary w-full py-4" disabled={loading}>{loading ? 'Creating team…' : 'Register team of two'} <ArrowRight size={16} /></button>
          </form>
        </div>
      </div>
    </div>
  )
}
