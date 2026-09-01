import { useState, type FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../lib/auth-context'
import { ApiError } from '../lib/api'
import { Button, ErrorBanner, Field, Input } from '../components/ui'

const HOME_BY_ROLE: Record<string, string> = {
  hr: '/hr/demandes',
  dg: '/dg/conges',
  employee: '/mon-conge',
}

const BRAND_POINTS = [
  'Un accès dédié pour chaque rôle',
  'Données hébergées et protégées',
  'Votre espace personnel en libre-service',
]

export function Login() {
  const { user, login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to={HOME_BY_ROLE[user.role] ?? '/'} replace />

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email, password)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Une erreur est survenue.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen bg-white">
      {/* Brand panel — hidden below lg, the form alone covers small/medium screens. */}
      <div className="relative hidden w-[42%] flex-none flex-col justify-between overflow-hidden bg-gradient-to-br from-brand-900 via-brand-700 to-brand-600 p-10 lg:flex xl:p-14">
        <div className="flex items-center gap-3">
          <img src="/logo.png" alt="Ariha Froid" className="h-11 w-11 rounded-xl" />
          <div className="flex flex-col">
            <span className="text-lg font-extrabold tracking-tight text-white">ARIHA AI</span>
            <span className="text-xs font-medium text-brand-100">Cockpit RH — Ariha Froid</span>
          </div>
        </div>

        <div className="max-w-sm">
          <h1 className="text-3xl font-extrabold leading-tight text-white text-balance">
            La plateforme RH d'Ariha Froid, en un seul endroit.
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-brand-100">
            Collaborateurs, congés, présence et performance — un espace unique pour toute l'équipe.
          </p>
          <ul className="mt-8 flex flex-col gap-3.5">
            {BRAND_POINTS.map((point) => (
              <li key={point} className="flex items-center gap-3 text-sm text-white">
                <svg
                  className="h-[18px] w-[18px] flex-none text-accent-500"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M20 6L9 17l-5-5" />
                </svg>
                {point}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-xs text-brand-100/80">© 2026 Ariha Froid — usage interne</p>
      </div>

      {/* Form panel */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 sm:px-10">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <img src="/logo.png" alt="Ariha Froid" className="h-9 w-9 rounded-lg" />
            <span className="text-base font-extrabold text-brand-700">ARIHA AI</span>
          </div>

          <h2 className="text-2xl font-extrabold text-slate-900">Bon retour</h2>
          <p className="mt-1.5 text-sm text-slate-500">Connectez-vous à votre espace ARIHA AI.</p>

          <ErrorBanner message={error} />

          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <Field label="Email" htmlFor="email">
              <Input
                id="email"
                type="email"
                required
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </Field>
            <Field label="Mot de passe" htmlFor="password">
              <Input
                id="password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Field>
            <Button type="submit" disabled={submitting} className="w-full">
              {submitting ? 'Connexion…' : 'Se connecter'}
            </Button>
          </form>

          <div className="mt-8 flex items-center gap-3">
            <div className="h-px flex-1 bg-slate-200" />
            <span className="text-[11px] font-medium tracking-wide text-slate-400">
              BESOIN D'AIDE ?
            </span>
            <div className="h-px flex-1 bg-slate-200" />
          </div>
          <p className="mt-4 text-center text-sm text-slate-500">Contactez le service RH.</p>
        </div>
      </div>
    </div>
  )
}
