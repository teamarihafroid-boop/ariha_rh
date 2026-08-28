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
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <div className="flex items-baseline gap-2">
            <span className="text-sm font-semibold text-blue-800">ARIHA AI</span>
            {user && (
              <span className="text-xs text-slate-500">
                {ROLE_LABELS[user.role] ?? user.role} · {user.email}
              </span>
            )}
          </div>
          {user && (
            <Button variant="secondary" onClick={() => logout()}>
              Se déconnecter
            </Button>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
    </div>
  )
}
