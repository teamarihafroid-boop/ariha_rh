import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  api,
  ApiError,
  type EmployeeLite,
  type LeaveRequest,
  type LeaveStatus,
  type LeaveType,
} from '../../lib/api'
import {
  Button,
  Card,
  ErrorBanner,
  Field,
  Input,
  Modal,
  Select,
  StatusBadge,
  Table,
  Textarea,
} from '../../components/ui'

type Filter = LeaveStatus | 'all'

const FILTERS: { value: Filter; label: string }[] = [
  { value: 'pending', label: 'En attente' },
  { value: 'all', label: 'Historique complet' },
]

export function LeaveQueue() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const employeeFilterId = searchParams.get('employee_id')
  // A link from a collaborateur's fiche wants their full history, not just
  // what's pending — default to "Historique complet" when arriving filtered.
  const [filter, setFilter] = useState<Filter>(employeeFilterId ? 'all' : 'pending')
  const [requests, setRequests] = useState<LeaveRequest[]>([])
  const [employees, setEmployees] = useState<EmployeeLite[]>([])
  const [leaveTypes, setLeaveTypes] = useState<LeaveType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [decisionTarget, setDecisionTarget] = useState<{
    request: LeaveRequest
    kind: 'approve' | 'reject'
  } | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (filter !== 'all') params.set('status', filter)
      if (employeeFilterId) params.set('employee_id', employeeFilterId)
      const qs = params.toString()
      const data = await api.get<LeaveRequest[]>(`/leave-requests${qs ? `?${qs}` : ''}`)
      setRequests(data)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur de chargement.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, employeeFilterId])

  useEffect(() => {
    Promise.all([
      api.get<EmployeeLite[]>('/employees'),
      // HR isn't restricted to employee_requestable types (see NewRequestCard).
      api.get<LeaveType[]>('/leave-types'),
    ])
      .then(([emps, types]) => {
        setEmployees(emps)
        setLeaveTypes(types)
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur de chargement.'))
  }, [])

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={`rounded-full px-3 py-1 text-sm font-medium transition-colors ${
                filter === f.value ? 'bg-brand-700 text-white' : 'bg-slate-100 text-slate-700'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <Button variant="secondary" onClick={() => setShowCreate((s) => !s)}>
          {showCreate ? 'Fermer' : 'Nouvelle demande'}
        </Button>
      </div>

      {employeeFilterId && (
        <div className="mb-4 flex items-center gap-2 rounded-lg bg-brand-50 px-3 py-2 text-sm text-brand-800">
          Filtré pour {requests[0]?.employee_nom ?? `collaborateur #${employeeFilterId}`}
          <button
            className="font-semibold text-brand-700 hover:underline"
            onClick={() => navigate('/hr/demandes')}
          >
            × Retirer le filtre
          </button>
        </div>
      )}

      <ErrorBanner message={error} />

      {showCreate && (
        <NewRequestCard
          employees={employees}
          leaveTypes={leaveTypes}
          onCreated={() => {
            setShowCreate(false)
            load()
          }}
        />
      )}

      <Card>
        <Table>
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Collaborateur</th>
              <th className="px-4 py-2">Type</th>
              <th className="px-4 py-2">Période</th>
              <th className="px-4 py-2">Jours</th>
              <th className="px-4 py-2">Statut</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={6}>
                  Chargement…
                </td>
              </tr>
            )}
            {!loading && requests.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={6}>
                  Aucune demande.
                </td>
              </tr>
            )}
            {requests.map((r) => (
              <tr key={r.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-3 font-medium text-slate-800">
                  <button
                    className="hover:underline"
                    onClick={() => navigate(`/hr/collaborateurs/${r.employee_id}`)}
                  >
                    {r.employee_nom}
                  </button>
                </td>
                <td className="px-4 py-3 text-slate-600">{r.leave_type_libelle}</td>
                <td className="px-4 py-3 text-slate-600">
                  {r.date_debut} → {r.date_fin}
                </td>
                <td className="px-4 py-3 text-slate-600">{r.nb_jours}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={r.status} />
                </td>
                <td className="px-4 py-3 text-right">
                  {r.status === 'pending' ? (
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="primary"
                        onClick={() => setDecisionTarget({ request: r, kind: 'approve' })}
                      >
                        Approuver
                      </Button>
                      <Button
                        variant="danger"
                        onClick={() => setDecisionTarget({ request: r, kind: 'reject' })}
                      >
                        Refuser
                      </Button>
                    </div>
                  ) : r.status === 'approved' && r.has_certificate ? (
                    <a
                      className="text-sm font-medium text-brand-700 hover:underline"
                      href={`/api/leave-requests/${r.id}/certificate`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Certificat
                    </a>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      {decisionTarget && (
        <DecisionModal
          request={decisionTarget.request}
          kind={decisionTarget.kind}
          onClose={() => setDecisionTarget(null)}
          onDone={() => {
            setDecisionTarget(null)
            load()
          }}
        />
      )}
    </div>
  )
}

function NewRequestCard({
  employees,
  leaveTypes,
  onCreated,
}: {
  employees: EmployeeLite[]
  leaveTypes: LeaveType[]
  onCreated: () => void
}) {
  const [employeeId, setEmployeeId] = useState<number | null>(null)
  const [leaveTypeId, setLeaveTypeId] = useState<number | null>(null)
  const [dateDebut, setDateDebut] = useState('')
  const [dateFin, setDateFin] = useState('')
  const [commentaire, setCommentaire] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (leaveTypes.length && leaveTypeId === null) setLeaveTypeId(leaveTypes[0].id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leaveTypes])

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
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card className="mb-4 p-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">
        Nouvelle demande pour un collaborateur
      </h3>
      <ErrorBanner message={error} />
      <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
        <Field label="Collaborateur">
          <Select
            required
            value={employeeId ?? ''}
            onChange={(e) => setEmployeeId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">—</option>
            {employees.map((e) => (
              <option key={e.id} value={e.id}>
                {e.full_name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Type de congé">
          <Select
            value={leaveTypeId ?? ''}
            onChange={(e) => setLeaveTypeId(Number(e.target.value))}
          >
            {leaveTypes.map((t) => (
              <option key={t.id} value={t.id}>
                {t.libelle}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Du">
          <Input
            type="date"
            required
            value={dateDebut}
            onChange={(e) => setDateDebut(e.target.value)}
          />
        </Field>
        <Field label="Au">
          <Input
            type="date"
            required
            value={dateFin}
            onChange={(e) => setDateFin(e.target.value)}
          />
        </Field>
        <Field label="Commentaire (optionnel)" className="sm:col-span-2">
          <Input value={commentaire} onChange={(e) => setCommentaire(e.target.value)} />
        </Field>
        <div className="sm:col-span-2">
          <Button type="submit" disabled={submitting}>
            {submitting ? 'Envoi…' : 'Créer la demande'}
          </Button>
        </div>
      </form>
    </Card>
  )
}

function DecisionModal({
  request,
  kind,
  onClose,
  onDone,
}: {
  request: LeaveRequest
  kind: 'approve' | 'reject'
  onClose: () => void
  onDone: () => void
}) {
  const [comment, setComment] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const isApprove = kind === 'approve'

  const submit = async () => {
    if (!isApprove && !comment.trim()) {
      setError('Un motif est obligatoire pour refuser une demande.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await api.post(`/leave-requests/${request.id}/${kind}`, { comment: comment || null })
      onDone()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      title={`${isApprove ? 'Approuver' : 'Refuser'} la demande de ${request.employee_nom}`}
      onClose={onClose}
    >
      <p className="mb-3 text-sm text-slate-600">
        {request.leave_type_libelle} · {request.date_debut} → {request.date_fin} ({request.nb_jours}{' '}
        j)
      </p>
      <ErrorBanner message={error} />
      <Field
        label={isApprove ? 'Commentaire (optionnel)' : 'Motif du refus'}
        htmlFor="comment"
        className="mb-4"
      >
        <Textarea
          id="comment"
          rows={3}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
        />
      </Field>
      <div className="flex flex-wrap justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          Annuler
        </Button>
        <Button variant={isApprove ? 'primary' : 'danger'} disabled={submitting} onClick={submit}>
          {submitting ? 'Envoi…' : isApprove ? 'Approuver' : 'Refuser'}
        </Button>
      </div>
    </Modal>
  )
}
