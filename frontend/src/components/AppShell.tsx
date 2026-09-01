import type { ReactNode } from 'react'
import { useAuth } from '../lib/auth-context'
import { Button } from './ui'

const ROLE_LABELS: Record<string, string> = {
  hr: 'RH',
  dg: 'Direction Générale',
  employee: 'Espace collaborateur',
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-2.5">
            <img src="/logo.png" alt="" className="h-8 w-8 flex-none rounded-md" />
            <div className="flex min-w-0 flex-col leading-tight sm:flex-row sm:items-baseline sm:gap-2">
              <span className="text-sm font-bold text-brand-700">ARIHA AI</span>
              {user && (
                <span className="truncate text-xs text-slate-500">
                  {ROLE_LABELS[user.role] ?? user.role} · {user.email}
                </span>
              )}
            </div>
          </div>
          {user && (
            <Button variant="secondary" className="flex-none" onClick={() => logout()}>
              Se déconnecter
            </Button>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8">{children}</main>
    </div>
  )
}
