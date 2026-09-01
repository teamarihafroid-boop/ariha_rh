import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError, type NotificationItem, type Role } from '../lib/api'
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

export function NotificationBell({ align = 'right' }: { align?: 'left' | 'right' }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<NotificationItem[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    try {
      const data = await api.get<NotificationItem[]>('/notifications')
      setItems(data)
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

  const unreadCount = items.filter((n) => !n.is_read).length

  const markRead = async (n: NotificationItem) => {
    if (n.is_read) return
    setItems((prev) => prev.map((it) => (it.id === n.id ? { ...it, is_read: true } : it)))
    try {
      await api.post(`/notifications/${n.id}/read`)
    } catch {
      // best-effort — a failed mark-as-read just means it reappears as unread next load
    }
  }

  const markAllRead = async () => {
    const unread = items.filter((n) => !n.is_read)
    setItems((prev) => prev.map((it) => ({ ...it, is_read: true })))
    await Promise.all(unread.map((n) => api.post(`/notifications/${n.id}/read`).catch(() => {})))
  }

  const openNotification = async (n: NotificationItem) => {
    setOpen(false)
    await markRead(n)
    navigate(HOME_BY_ROLE[user.role])
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
            className={`absolute z-50 mt-2 w-80 max-w-[90vw] rounded-xl border border-slate-200 bg-white shadow-lg ${
              align === 'right' ? 'right-0' : 'left-0'
            }`}
          >
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
              <span className="text-sm font-semibold text-slate-800">Notifications</span>
              {unreadCount > 0 && (
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
                  key={n.id}
                  onClick={() => openNotification(n)}
                  className={`block w-full border-b border-slate-50 px-4 py-3 text-left last:border-0 hover:bg-slate-50 ${
                    n.is_read ? '' : 'bg-brand-50/60'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <span
                      className={`mt-1.5 h-1.5 w-1.5 flex-none rounded-full ${n.is_read ? '' : 'bg-accent-600'}`}
                    />
                    <div>
                      <div className="text-sm font-semibold text-slate-800">{n.title}</div>
                      <div className="mt-0.5 text-xs text-slate-500">{n.body}</div>
                      <div className="mt-1 text-[11px] text-slate-400">
                        {formatRelative(n.created_at)}
                      </div>
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
