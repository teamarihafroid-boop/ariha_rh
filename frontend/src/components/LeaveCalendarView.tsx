import { useEffect, useMemo, useState } from 'react'
import { api, ApiError } from '../lib/api'
import { Button, Card, ErrorBanner } from './ui'

interface CalendarEntry {
  id: number
  employee_id: number
  employee_nom: string
  leave_type_libelle: string
  couleur: string
  date_debut: string
  date_fin: string
  nb_jours: string
  status: string
}

interface CalendarResponse {
  conges: CalendarEntry[]
  jours_feries: { id: number; date: string; libelle: string }[]
}

const MONTH_NAMES = [
  'Janvier',
  'Février',
  'Mars',
  'Avril',
  'Mai',
  'Juin',
  'Juillet',
  'Août',
  'Septembre',
  'Octobre',
  'Novembre',
  'Décembre',
]

function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate()
}

function firstWeekdayOffset(year: number, month: number): number {
  // JS getDay(): 0=Sunday..6=Saturday. We render Mon-first grids, so shift.
  const jsDay = new Date(year, month - 1, 1).getDay()
  return (jsDay + 6) % 7
}

export function LeaveCalendarView() {
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth() + 1)
  const [data, setData] = useState<CalendarResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setError(null)
    api
      .get<CalendarResponse>(`/leave-calendar?mois=${month}&annee=${year}`)
      .then((d) => !cancelled && setData(d))
      .catch((err) => !cancelled && setError(err instanceof ApiError ? err.message : 'Erreur.'))
    return () => {
      cancelled = true
    }
  }, [year, month])

  const entriesByDay = useMemo(() => {
    const map = new Map<number, CalendarEntry[]>()
    if (!data) return map
    const nbDays = daysInMonth(year, month)
    for (let d = 1; d <= nbDays; d++) {
      const current = new Date(year, month - 1, d)
      const list = data.conges.filter((c) => {
        const debut = new Date(c.date_debut)
        const fin = new Date(c.date_fin)
        return current >= new Date(debut.toDateString()) && current <= new Date(fin.toDateString())
      })
      if (list.length) map.set(d, list)
    }
    return map
  }, [data, year, month])

  const holidaySet = useMemo(() => {
    const set = new Map<number, string>()
    data?.jours_feries.forEach((h) => set.set(new Date(h.date).getDate(), h.libelle))
    return set
  }, [data])

  const goPrev = () => {
    if (month === 1) {
      setMonth(12)
      setYear((y) => y - 1)
    } else {
      setMonth((m) => m - 1)
    }
  }
  const goNext = () => {
    if (month === 12) {
      setMonth(1)
      setYear((y) => y + 1)
    } else {
      setMonth((m) => m + 1)
    }
  }

  const nbDays = daysInMonth(year, month)
  const offset = firstWeekdayOffset(year, month)
  const cells: (number | null)[] = [
    ...Array(offset).fill(null),
    ...Array.from({ length: nbDays }, (_, i) => i + 1),
  ]

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <Button variant="secondary" onClick={goPrev}>
          ← Précédent
        </Button>
        <h2 className="text-base font-semibold text-slate-900">
          {MONTH_NAMES[month - 1]} {year}
        </h2>
        <Button variant="secondary" onClick={goNext}>
          Suivant →
        </Button>
      </div>

      <ErrorBanner message={error} />

      <Card className="p-3">
        <div className="overflow-x-auto">
          <div className="min-w-[560px]">
            <div className="grid grid-cols-7 gap-1 text-center text-xs font-medium text-slate-500">
              {['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'].map((d) => (
                <div key={d} className="py-1">
                  {d}
                </div>
              ))}
            </div>
            <div className="grid grid-cols-7 gap-1">
              {cells.map((day, idx) => (
                <div
                  key={idx}
                  className={`min-h-20 rounded-lg border p-1 text-xs ${
                    day === null ? 'border-transparent' : 'border-slate-100'
                  } ${day !== null && holidaySet.has(day) ? 'bg-amber-50' : ''}`}
                >
                  {day !== null && (
                    <>
                      <div className="mb-1 font-medium text-slate-600">{day}</div>
                      {holidaySet.has(day) && (
                        <div className="mb-1 truncate text-[10px] text-amber-700">
                          {holidaySet.get(day)}
                        </div>
                      )}
                      {(entriesByDay.get(day) ?? []).map((e) => (
                        <div
                          key={e.id}
                          title={`${e.employee_nom} — ${e.leave_type_libelle} (${e.status})`}
                          className="mb-0.5 truncate rounded px-1 text-[10px] text-white"
                          style={{
                            backgroundColor: e.couleur,
                            opacity: e.status === 'pending' ? 0.55 : 1,
                          }}
                        >
                          {e.employee_nom}
                        </div>
                      ))}
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </Card>
      <p className="mt-2 text-xs text-slate-400">
        Couleur pâle = demande en attente d'approbation. Couleur pleine = congé approuvé.
      </p>
    </div>
  )
}
