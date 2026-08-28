import { useEffect, useState, type FormEvent } from 'react'
import { useAuth } from '../../lib/auth-context'
import {
  api,
  ApiError,
  type Department,
  type EmployeeLite,
  type LeaveBalance,
  type LeaveRequest,
  type LeaveType,
} from '../../lib/api'
import { Button, Card, ErrorBanner, PageHeader, StatusBadge, Table } from '../../components/ui'

export function MyLeave() {
  const { user } = useAuth()
  const currentYear = new Date().getFullYear()

  const [balances, setBalances] = useState<LeaveBalance[]>([])
  const [requests, setRequests] = useState<LeaveRequest[]>([])
  const [leaveTypes, setLeaveTypes] = useState<LeaveType[]>([])
  const [isResponsable, setIsResponsable] = useState(false)
  const [colleagues, setColleagues] = useState<EmployeeLite[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const [balanceData, requestData, typeData] = await Promise.all([
        api.get<LeaveBalance[]>(`/leave-balances?annee=${currentYear}`),
        api.get<LeaveRequest[]>('/leave-requests'),
        api.get<LeaveType[]>('/leave-types'),
      ])
      setBalances(balanceData)
      setRequests(requestData)
      setLeaveTypes(typeData)

      if (user?.department_id != null) {
        const departments = await api.get<Department[]>('/departments')
        const myDept = departments.find((d) => d.id === user.department_id)
        const responsable = myDept?.leave_responsable_employee_id === user.employee_id
        setIsResponsable(responsable)
        if (responsable) {
          const roster = await api.get<EmployeeLite[]>(
            `/employees?department_id=${user.department_id}`,
          )
          setColleagues(roster.filter((e) => e.id !== user.employee_id))
        }
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur de chargement.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // Re-runs once `user` resolves from AuthProvider's own /auth/me fetch —
    // don't assume it's already populated on first mount (it usually is in
    // the real app, since RequireRole gates rendering on `loading`, but this
    // component shouldn't silently depend on that).
    if (user) load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user])

  return (
    <div>
      <PageHeader title="Mon congé" subtitle="Solde, demandes et nouvelle demande de congé." />
      <ErrorBanner message={error} />

      {!loading && (
        <>
          <Card className="mb-6 p-4">
            <h2 className="mb-3 text-sm font-semibold text-slate-700">Solde {currentYear}</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {balances
                .filter((b) => leaveTypes.find((t) => t.id === b.leave_type_id)?.deduit_du_solde)
                .map((b) => (
                  <div key={b.leave_type_id} className="rounded-md bg-slate-50 p-3">
                    <div className="text-xs text-slate-500">{b.leave_type_libelle}</div>
                    <div className="text-lg font-semibold text-slate-900">{b.solde} j</div>
                    <div className="text-xs text-slate-400">
                      {b.jours_acquis} acquis · {b.jours_pris} pris
                    </div>
                  </div>
                ))}
            </div>
          </Card>

          <NewRequestForm
            leaveTypes={leaveTypes}
            isResponsable={isResponsable}
            colleagues={colleagues}
            selfId={user?.employee_id ?? null}
            onCreated={load}
          />

          <Card className="mt-6">
            <Table>
              <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
                <tr>
                  {isResponsable && <th className="px-4 py-2">Collaborateur</th>}
                  <th className="px-4 py-2">Type</th>
                  <th className="px-4 py-2">Période</th>
                  <th className="px-4 py-2">Jours</th>
                  <th className="px-4 py-2">Statut</th>
                  <th className="px-4 py-2" />
                </tr>
              </thead>
              <tbody>
                {requests.length === 0 && (
                  <tr>
                    <td className="px-4 py-6 text-center text-slate-400" colSpan={6}>
                      Aucune demande.
                    </td>
                  </tr>
                )}
                {requests.map((r) => (
                  <tr key={r.id} className="border-b border-slate-100 last:border-0">
                    {isResponsable && (
                      <td className="px-4 py-3 text-slate-600">{r.employee_nom}</td>
                    )}
                    <td className="px-4 py-3 text-slate-600">{r.leave_type_libelle}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {r.date_debut} → {r.date_fin}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{r.nb_jours}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={r.status} />
                      {r.status === 'rejected' && r.decision_comment && (
                        <div className="mt-1 text-xs text-slate-500">{r.decision_comment}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {r.status === 'approved' && (
                        <a
                          className="text-sm text-blue-700 hover:underline"
                          href={`/api/leave-requests/${r.id}/certificate`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Certificat
                        </a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </Card>
        </>
      )}
    </div>
  )
}

function NewRequestForm({
  leaveTypes,
  isResponsable,
  colleagues,
  selfId,
  onCreated,
}: {
  leaveTypes: LeaveType[]
  isResponsable: boolean
  colleagues: EmployeeLite[]
  selfId: number | null
  onCreated: () => void
}) {
  const [employeeId, setEmployeeId] = useState<number | null>(selfId)
  const [leaveTypeId, setLeaveTypeId] = useState<number | null>(null)
  const [dateDebut, setDateDebut] = useState('')
  const [dateFin, setDateFin] = useState('')
  const [commentaire, setCommentaire] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (leaveTypes.length && leaveTypeId === null) setLeaveTypeId(leaveTypes[0].id)
    if (selfId !== null && employeeId === null) setEmployeeId(selfId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leaveTypes, selfId])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!employeeId || !leaveTypeId || !dateDebut || !dateFin) return
    setSubmitting(true)
    setError(null)
    try {
      await api.post('/leave-requests', {
        employee_id: employeeId,
        leave_type_id: leaveTypeId,
        date_debut: dateDebut,
        date_fin: dateFin,
        commentaire: commentaire || null,
      })
      setDateDebut('')
      setDateFin('')
      setCommentaire('')
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card className="p-4">
      <h2 className="mb-3 text-sm font-semibold text-slate-700">Nouvelle demande</h2>
      <ErrorBanner message={error} />
      <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
        {isResponsable && (
          <div className="sm:col-span-2">
            <label className="mb-1 block text-sm font-medium text-slate-700">Pour qui ?</label>
            <select
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={employeeId ?? ''}
              onChange={(e) => setEmployeeId(Number(e.target.value))}
            >
              <option value={selfId ?? ''}>Moi-même</option>
              {colleagues.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.full_name}
                </option>
              ))}
            </select>
          </div>
        )}
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Type de congé</label>
          <select
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            value={leaveTypeId ?? ''}
            onChange={(e) => setLeaveTypeId(Number(e.target.value))}
          >
            {leaveTypes.map((t) => (
              <option key={t.id} value={t.id}>
                {t.libelle}
              </option>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Du</label>
            <input
              type="date"
              required
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={dateDebut}
              onChange={(e) => setDateDebut(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">Au</label>
            <input
              type="date"
              required
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              value={dateFin}
              onChange={(e) => setDateFin(e.target.value)}
            />
          </div>
        </div>
        <div className="sm:col-span-2">
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Commentaire (optionnel)
          </label>
          <input
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            value={commentaire}
            onChange={(e) => setCommentaire(e.target.value)}
          />
        </div>
        <div className="sm:col-span-2">
          <Button type="submit" disabled={submitting}>
            {submitting ? 'Envoi…' : 'Envoyer la demande'}
          </Button>
        </div>
      </form>
    </Card>
  )
}
