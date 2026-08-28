import { useEffect, useState } from 'react'
import { api, ApiError, type LeaveRequest } from '../../lib/api'
import { Card, ErrorBanner, PageHeader, StatusBadge, Table } from '../../components/ui'
import { LeaveCalendarView } from '../../components/LeaveCalendarView'

export function LeaveOverview() {
  const [requests, setRequests] = useState<LeaveRequest[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get<LeaveRequest[]>('/leave-requests')
      .then(setRequests)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur.'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <PageHeader
        title="Congés — vue d'ensemble"
        subtitle="Lecture seule, données de toute l'entreprise."
      />

      <div className="mb-8">
        <LeaveCalendarView />
      </div>

      <ErrorBanner message={error} />

      <Card>
        <Table>
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Collaborateur</th>
              <th className="px-4 py-2">Type</th>
              <th className="px-4 py-2">Période</th>
              <th className="px-4 py-2">Jours</th>
              <th className="px-4 py-2">Statut</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={5}>
                  Chargement…
                </td>
              </tr>
            )}
            {!loading && requests.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={5}>
                  Aucune demande.
                </td>
              </tr>
            )}
            {requests.map((r) => (
              <tr key={r.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-3 font-medium text-slate-800">{r.employee_nom}</td>
                <td className="px-4 py-3 text-slate-600">{r.leave_type_libelle}</td>
                <td className="px-4 py-3 text-slate-600">
                  {r.date_debut} → {r.date_fin}
                </td>
                <td className="px-4 py-3 text-slate-600">{r.nb_jours}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={r.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </div>
  )
}
