import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  api,
  ApiError,
  type DocumentAlert,
  type NotificationItem,
  type ProbationAlert,
  type Role,
  type StalledApplication,
} from '../lib/api'
import { useAuth } from '../lib/auth-context'
import { IconBell, IconCheck } from './icons'

const HOME_BY_ROLE: Record<Role, string> = {
  hr: '/hr/demandes',
  dg: '/dg/conges',
  employee: '/mon-conge',
}

function formatRelative(iso: string): string {
  const minutes = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (minutes < 1) return "à l'instant"
  if (minutes < 60) return `il y a ${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `il y a ${hours} h`
  return `il y a ${Math.floor(hours / 24)} j`
}

/** A row in the bell: either a real, persisted Notification (mark-read-able)
 * or a read-time computed alert (probation/document/stalled-candidacy —
 * this app has no cron, so these are recomputed on every load, never
 * stored, and have no "read" state of their own — see NotificationType
 * in the backend for why). Merging both here gives HR one place to check
 * everything (HR-38) without inventing a duplicate-detection/expiry system
 * for the computed side. */
interface MergedItem {
  key: string
  kind: 'event' | 'alert'
  title: string
  body: string
  is_read: boolean
  createdAt: string
  urgenceRank: number
  path: string
  notificationId?: number
}

const URGENCE_RANK: Record<'retard' | 'urgent' | 'semaine', number> = {
  retard: 0,
  urgent: 1,
  semaine: 2,
}

function eventToItem(n: NotificationItem): MergedItem {
  return {
    key: `event-${n.id}`,
    kind: 'event',
    title: n.title,
    body: n.body,
    is_read: n.is_read,
    createdAt: n.created_at,
    urgenceRank: 0,
    path: HOME_BY_ROLE.hr,
    notificationId: n.id,
  }
}

function probationToItem(a: ProbationAlert): MergedItem {
  return {
    key: `probation-${a.employee_id}`,
    kind: 'alert',
    title: `Période d'essai — ${a.employee_nom}`,
    body: `Fin d'essai le ${a.date_fin_periode_essai}, évaluation à statuer.`,
    is_read: false,
    createdAt: a.date_fin_periode_essai,
    urgenceRank: URGENCE_RANK[a.urgence],
    path: `/hr/collaborateurs/${a.employee_id}`,
  }
}

function documentToItem(a: DocumentAlert): MergedItem {
  return {
    key: `document-${a.document_id}`,
    kind: 'alert',
    title: `Document à renouveler — ${a.employee_nom}`,
    body: `${a.type_document} expire le ${a.date_expiration}.`,
    is_read: false,
    createdAt: a.date_expiration,
    urgenceRank: URGENCE_RANK[a.urgence],
    path: `/hr/collaborateurs/${a.employee_id}`,
  }
}

function stalledToItem(a: StalledApplication): MergedItem {
  return {
    key: `stalled-${a.application_id}`,
    kind: 'alert',
    title: `Candidature stagnante — ${a.candidate_nom}`,
    body: `${a.job_offer_titre} · ${a.stage_libelle ?? '—'} depuis ${a.jours_stagnation} jours.`,
    is_read: false,
    createdAt: a.date_dernier_mouvement,
    urgenceRank: a.jours_stagnation >= 21 ? 0 : 1,
    path: '/hr/recrutement/pipeline',
  }
}

function sortItems(items: MergedItem[]): MergedItem[] {
  const bucket = (i: MergedItem) =>
    i.kind === 'event' && !i.is_read ? 0 : i.kind === 'alert' ? 1 : 2
  return [...items].sort((a, b) => {
    const diff = bucket(a) - bucket(b)
    if (diff !== 0) return diff
    if (a.kind === 'alert' && b.kind === 'alert') return a.urgenceRank - b.urgenceRank
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  })
}

export function NotificationBell({ align = 'right' }: { align?: 'left' | 'right' }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<MergedItem[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    try {
      const notifications = await api.get<NotificationItem[]>('/notifications')
      let merged = notifications.map(eventToItem)

      if (user?.role === 'hr') {
        const [probation, documents, stalled] = await Promise.all([
          api.get<ProbationAlert[]>('/employees/periode-essai/alertes'),
          api.get<DocumentAlert[]>('/employees/documents/alertes'),
          api.get<StalledApplication[]>('/recruitment/applications/stagnantes'),
        ])
        merged = merged.concat(
          probation.map(probationToItem),
          documents.map(documentToItem),
          stalled.map(stalledToItem),
        )
      }

      setItems(sortItems(merged))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  useEffect(() => {
    if (!user) return
    load()
    const interval = setInterval(load, 60000)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user])

  if (!user) return null

  const unreadCount = items.filter((n) => (n.kind === 'event' ? !n.is_read : true)).length

  const markRead = async (n: MergedItem) => {
    if (n.kind !== 'event' || n.is_read || n.notificationId === undefined) return
    setItems((prev) => prev.map((it) => (it.key === n.key ? { ...it, is_read: true } : it)))
    try {
      await api.post(`/notifications/${n.notificationId}/read`)
    } catch {
      // best-effort — a failed mark-as-read just means it reappears as unread next load
    }
  }

  const markAllRead = async () => {
    const unread = items.filter((n) => n.kind === 'event' && !n.is_read)
    setItems((prev) => prev.map((it) => (it.kind === 'event' ? { ...it, is_read: true } : it)))
    await Promise.all(
      unread.map((n) => api.post(`/notifications/${n.notificationId}/read`).catch(() => {})),
    )
  }

  const openItem = async (n: MergedItem) => {
    setOpen(false)
    await markRead(n)
    navigate(n.path)
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Notifications"
        className="relative rounded-lg p-1.5 text-slate-500 hover:bg-slate-100"
      >
        <IconBell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-accent-600 px-1 text-[10px] font-bold text-white">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div
            className={`absolute z-50 mt-2 w-80 max-w-[90vw] origin-top rounded-xl border border-slate-200 bg-white shadow-lg animate-[scaleIn_150ms_ease-out] ${
              align === 'right' ? 'right-0' : 'left-0'
            }`}
          >
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
              <span className="text-sm font-semibold text-slate-800">Notifications</span>
              {items.some((n) => n.kind === 'event' && !n.is_read) && (
                <button
                  onClick={markAllRead}
                  className="flex items-center gap-1 text-xs font-medium text-brand-700 hover:underline"
                >
                  <IconCheck className="h-3.5 w-3.5" />
                  Tout marquer comme lu
                </button>
              )}
            </div>
            <div className="max-h-80 overflow-y-auto">
              {error && <div className="px-4 py-3 text-sm text-red-600">{error}</div>}
              {!error && items.length === 0 && (
                <div className="px-4 py-6 text-center text-sm text-slate-400">
                  Aucune notification.
                </div>
              )}
              {items.map((n) => (
                <button
                  key={n.key}
                  onClick={() => openItem(n)}
                  className={`block w-full border-b border-slate-50 px-4 py-3 text-left last:border-0 hover:bg-slate-50 ${
                    n.kind === 'event' && !n.is_read ? 'bg-brand-50/60' : ''
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <span
                      className={`mt-1.5 h-1.5 w-1.5 flex-none rounded-full ${
                        n.kind === 'alert' ? 'bg-amber-500' : !n.is_read ? 'bg-accent-600' : ''
                      }`}
                    />
                    <div>
                      <div className="text-sm font-semibold text-slate-800">{n.title}</div>
                      <div className="mt-0.5 text-xs text-slate-500">{n.body}</div>
                      {n.kind === 'event' && (
                        <div className="mt-1 text-[11px] text-slate-400">
                          {formatRelative(n.createdAt)}
                        </div>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
