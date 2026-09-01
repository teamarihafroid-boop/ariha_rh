import { useEffect, useState } from 'react'
import { api, ApiError, type LeaveRequest, type LeaveStatus } from '../../lib/api'
import {
  Button,
  Card,
  ErrorBanner,
  Field,
  Modal,
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
  const [filter, setFilter] = useState<Filter>('pending')
  const [requests, setRequests] = useState<LeaveRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [decisionTarget, setDecisionTarget] = useState<{
    request: LeaveRequest
    kind: 'approve' | 'reject'
  } | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const qs = filter === 'all' ? '' : `?status=${filter}`
      const data = await api.get<LeaveRequest[]>(`/leave-requests${qs}`)
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
  }, [filter])

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-2">
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
                <td className="px-4 py-3 font-medium text-slate-800">{r.employee_nom}</td>
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
                  ) : r.status === 'approved' ? (
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
