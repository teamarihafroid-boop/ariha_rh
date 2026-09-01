import { useState, type ComponentType, type ReactNode, type SVGProps } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../lib/auth-context'
import type { Role } from '../lib/api'
import { NotificationBell } from './NotificationBell'
import {
  IconCalendar,
  IconClipboard,
  IconClose,
  IconFlag,
  IconLogout,
  IconMenu,
  IconTag,
  IconUsers,
} from './icons'

const ROLE_LABELS: Record<string, string> = {
  hr: 'RH',
  dg: 'Direction Générale',
  employee: 'Espace collaborateur',
}

interface NavItem {
  to: string
  label: string
  icon: ComponentType<SVGProps<SVGSVGElement>>
}

interface NavSection {
  title?: string
  items: NavItem[]
}

const NAV_BY_ROLE: Record<Role, NavSection[]> = {
  hr: [
    {
      title: 'Congés',
      items: [
        { to: '/hr/demandes', label: 'Demandes de congé', icon: IconClipboard },
        { to: '/hr/calendrier', label: 'Calendrier', icon: IconCalendar },
      ],
    },
    {
      title: 'Paramètres',
      items: [
        { to: '/hr/parametres/responsables', label: 'Responsables congés', icon: IconUsers },
        { to: '/hr/parametres/types-conge', label: 'Types de congé', icon: IconTag },
        { to: '/hr/parametres/feries', label: 'Jours fériés', icon: IconFlag },
      ],
    },
  ],
  dg: [{ items: [{ to: '/dg/conges', label: 'Congés', icon: IconCalendar }] }],
  employee: [{ items: [{ to: '/mon-conge', label: 'Mon congé', icon: IconCalendar }] }],
}

function BrandMark() {
  return (
    <Link to="/" className="flex items-center gap-2.5">
      <img src="/logo.png" alt="" className="h-8 w-8 flex-none rounded-lg" />
      <span className="text-sm font-extrabold tracking-tight text-brand-700">ARIHA AI</span>
    </Link>
  )
}

function NavContent({ onNavigate, bell = false }: { onNavigate?: () => void; bell?: boolean }) {
  const { user, logout } = useAuth()
  const location = useLocation()
  const sections = user ? NAV_BY_ROLE[user.role] : []

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-5 py-5">
        <BrandMark />
        {bell && <NotificationBell />}
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto px-3 pb-4">
        {sections.map((section, i) => (
          <div key={section.title ?? i}>
            {section.title && (
              <div className="mb-1.5 px-2.5 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                {section.title}
              </div>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const active = location.pathname === item.to
                const ItemIcon = item.icon
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    onClick={onNavigate}
                    className={`flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors ${
                      active
                        ? 'bg-brand-50 text-brand-700'
                        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                    }`}
                  >
                    <ItemIcon
                      className={`h-[18px] w-[18px] flex-none ${active ? 'text-brand-700' : 'text-slate-400'}`}
                    />
                    {item.label}
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      {user && (
        <div className="border-t border-slate-100 p-3">
          <div className="rounded-lg bg-slate-50 px-3 py-2.5">
            <div className="text-xs font-semibold text-slate-700">
              {ROLE_LABELS[user.role] ?? user.role}
            </div>
            <div className="truncate text-xs text-slate-500">{user.email}</div>
            <button
              onClick={() => logout()}
              className="mt-2 flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-red-600"
            >
              <IconLogout className="h-3.5 w-3.5" />
              Se déconnecter
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export function AppShell({ children }: { children: ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Desktop sidebar */}
      <aside className="hidden w-64 flex-none border-r border-slate-200 bg-white lg:block">
        <div className="fixed h-screen w-64">
          <NavContent bell />
        </div>
      </aside>

      {/* Mobile drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => setDrawerOpen(false)} />
          <div className="relative flex h-full w-72 max-w-[85vw] flex-col bg-white shadow-xl">
            <button
              onClick={() => setDrawerOpen(false)}
              aria-label="Fermer le menu"
              className="absolute right-3 top-3 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
            >
              <IconClose className="h-5 w-5" />
            </button>
            <NavContent onNavigate={() => setDrawerOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile top bar */}
        <header className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setDrawerOpen(true)}
              aria-label="Ouvrir le menu"
              className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100"
            >
              <IconMenu className="h-5 w-5" />
            </button>
            <BrandMark />
          </div>
          <NotificationBell />
        </header>

        <main className="flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:px-10 lg:py-10">
          <div className="mx-auto max-w-5xl">{children}</div>
        </main>
      </div>
    </div>
  )
}
