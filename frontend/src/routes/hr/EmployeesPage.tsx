import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  api,
  ApiError,
  type Department,
  type DocumentAlert,
  type Employee,
  type EmployeeFormInput,
  type EmployeeLite,
  type EmployeeStatus,
  type Position,
  type ProbationAlert,
} from '../../lib/api'
import {
  Button,
  Card,
  ColorBadge,
  ErrorBanner,
  Field,
  Input,
  Modal,
  PageHeader,
  Select,
  Table,
} from '../../components/ui'
import { EMPTY_EMPLOYEE_FORM, EmployeeForm } from '../../components/EmployeeForm'
import { AccountCreationFields } from '../../components/AccountCreationFields'

export function EmployeesPage() {
  const navigate = useNavigate()
  const [employees, setEmployees] = useState<EmployeeLite[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [positions, setPositions] = useState<Position[]>([])
  const [statuses, setStatuses] = useState<EmployeeStatus[]>([])
  const [probationAlerts, setProbationAlerts] = useState<ProbationAlert[]>([])
  const [documentAlerts, setDocumentAlerts] = useState<DocumentAlert[]>([])
  const [error, setError] = useState<string | null>(null)
  const [warning, setWarning] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [q, setQ] = useState('')
  const [departmentId, setDepartmentId] = useState('')
  const [statusId, setStatusId] = useState('')
  const skipNextAutoSearch = useRef(true)

  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<EmployeeFormInput>(EMPTY_EMPLOYEE_FORM)
  const [createAccount, setCreateAccount] = useState(false)
  const [accountEmail, setAccountEmail] = useState('')
  const [accountPassword, setAccountPassword] = useState('')

  const loadReference = async () => {
    const [depts, poss, stats] = await Promise.all([
      // Active-only: this list feeds both the département filter and the
      // "Nouveau collaborateur" form — a brand-new hire should never be
      // assignable to a deactivated département/poste.
      api.get<Department[]>('/departments'),
      api.get<Position[]>('/positions'),
      api.get<EmployeeStatus[]>('/employee-statuses'),
    ])
    setDepartments(depts)
    setPositions(poss)
    setStatuses(stats)
  }

  const loadEmployees = async () => {
    const params = new URLSearchParams()
    if (q) params.set('q', q)
    if (departmentId) params.set('department_id', departmentId)
    if (statusId) params.set('status_id', statusId)
    const list = await api.get<EmployeeLite[]>(`/employees?${params.toString()}`)
    setEmployees(list)
  }

  useEffect(() => {
    setLoading(true)
    Promise.all([
      loadReference(),
      loadEmployees(),
      api.get<ProbationAlert[]>('/employees/periode-essai/alertes').then(setProbationAlerts),
      api.get<DocumentAlert[]>('/employees/documents/alertes').then(setDocumentAlerts),
    ])
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur de chargement.'))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Search-as-you-type: the free-text field is debounced so each keystroke
  // doesn't fire a request, but department/statut apply immediately since
  // they're discrete choices, not typing.
  useEffect(() => {
    if (skipNextAutoSearch.current) {
      skipNextAutoSearch.current = false
      return
    }
    const timer = setTimeout(() => {
      loadEmployees().catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur.'))
    }, 300)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, departmentId, statusId])

  const URGENCE_ORDER: Record<ProbationAlert['urgence'], number> = {
    retard: 0,
    urgent: 1,
    semaine: 2,
  }
  const URGENCE_STYLE: Record<ProbationAlert['urgence'], string> = {
    retard: 'border-red-200 bg-red-50 text-red-800',
    urgent: 'border-amber-200 bg-amber-50 text-amber-800',
    semaine: 'border-slate-200 bg-slate-50 text-slate-700',
  }
  const URGENCE_LABEL: Record<ProbationAlert['urgence'], string> = {
    retard: 'Délai dépassé',
    urgent: '≤ 3 jours',
    semaine: '≤ 10 jours',
  }
  const sortedAlerts = [...probationAlerts].sort(
    (a, b) => URGENCE_ORDER[a.urgence] - URGENCE_ORDER[b.urgence],
  )

  const DOC_URGENCE_LABEL: Record<DocumentAlert['urgence'], string> = {
    retard: 'Expiré',
    urgent: '≤ 7 jours',
    semaine: '≤ 30 jours',
  }
  const sortedDocumentAlerts = [...documentAlerts].sort(
    (a, b) => URGENCE_ORDER[a.urgence] - URGENCE_ORDER[b.urgence],
  )

  const resetFilters = () => {
    setQ('')
    setDepartmentId('')
    setStatusId('')
  }

  const resetCreateForm = () => {
    setShowCreate(false)
    setForm(EMPTY_EMPLOYEE_FORM)
    setCreateAccount(false)
    setAccountEmail('')
    setAccountPassword('')
  }

  const create = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setWarning(null)
    try {
      const created = await api.post<Employee>('/employees', form)
      if (createAccount) {
        try {
          await api.post('/users', {
            email: accountEmail,
            password: accountPassword,
            role: 'employee',
            employee_id: created.id,
          })
        } catch (err) {
          setWarning(
            `Le collaborateur a été créé, mais le compte de connexion n'a pas pu être créé : ${
              err instanceof ApiError ? err.message : 'erreur inconnue'
            }`,
          )
        }
      }
      resetCreateForm()
      await loadEmployees()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <PageHeader title="Collaborateurs" subtitle="Fiches employés, recherche et création." />
        <Button onClick={() => setShowCreate(true)}>Nouveau collaborateur</Button>
      </div>
      <ErrorBanner message={error} />
      {warning && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {warning}
        </div>
      )}

      {sortedAlerts.length > 0 && (
        <Card className="mb-4 p-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-800">
            Périodes d'essai à statuer — {sortedAlerts.length}
          </h2>
          <ul className="space-y-2">
            {sortedAlerts.map((a) => (
              <li key={a.employee_id}>
                <button
                  className={`flex w-full items-center justify-between gap-3 rounded-lg border px-3 py-2 text-left text-sm hover:opacity-80 ${URGENCE_STYLE[a.urgence]}`}
                  onClick={() => navigate(`/hr/collaborateurs/${a.employee_id}`)}
                >
                  <span className="font-medium">{a.employee_nom}</span>
                  <span className="flex items-center gap-3 text-xs">
                    <span>Fin d'essai : {a.date_fin_periode_essai}</span>
                    <span className="rounded-full bg-white/60 px-2 py-0.5 font-semibold">
                      {URGENCE_LABEL[a.urgence]}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {sortedDocumentAlerts.length > 0 && (
        <Card className="mb-4 p-4">
          <h2 className="mb-3 text-sm font-semibold text-slate-800">
            Documents à renouveler — {sortedDocumentAlerts.length}
          </h2>
          <ul className="space-y-2">
            {sortedDocumentAlerts.map((a) => (
              <li key={a.document_id}>
                <button
                  className={`flex w-full items-center justify-between gap-3 rounded-lg border px-3 py-2 text-left text-sm hover:opacity-80 ${URGENCE_STYLE[a.urgence]}`}
                  onClick={() => navigate(`/hr/collaborateurs/${a.employee_id}`)}
                >
                  <span className="font-medium">
                    {a.employee_nom} — {a.type_document}
                  </span>
                  <span className="flex items-center gap-3 text-xs">
                    <span>Expiration : {a.date_expiration}</span>
                    <span className="rounded-full bg-white/60 px-2 py-0.5 font-semibold">
                      {DOC_URGENCE_LABEL[a.urgence]}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card className="mb-4 p-4">
        <form onSubmit={(e) => e.preventDefault()} className="flex flex-wrap items-end gap-3">
          <Field label="Recherche" className="min-w-[12rem] flex-1">
            <Input
              placeholder="Nom, email, téléphone, matricule…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </Field>
          <Field label="Département">
            <Select value={departmentId} onChange={(e) => setDepartmentId(e.target.value)}>
              <option value="">Tous</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.nom}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Statut">
            <Select value={statusId} onChange={(e) => setStatusId(e.target.value)}>
              <option value="">Tous</option>
              {statuses.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.libelle}
                </option>
              ))}
            </Select>
          </Field>
          {(q || departmentId || statusId) && (
            <Button type="button" variant="secondary" onClick={resetFilters}>
              Réinitialiser
            </Button>
          )}
        </form>
      </Card>

      <Card>
        <Table>
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Nom</th>
              <th className="px-4 py-2">Matricule</th>
              <th className="px-4 py-2">Poste</th>
              <th className="px-4 py-2">Département</th>
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
            {!loading && employees.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={6}>
                  Aucun collaborateur ne correspond à cette recherche.
                </td>
              </tr>
            )}
            {employees.map((e) => (
              <tr
                key={e.id}
                className="cursor-pointer border-b border-slate-100 last:border-0 hover:bg-slate-50"
                onClick={() => navigate(`/hr/collaborateurs/${e.id}`)}
              >
                <td className="px-4 py-3 font-medium text-slate-800">{e.full_name}</td>
                <td className="px-4 py-3 text-slate-500">{e.matricule ?? '—'}</td>
                <td className="px-4 py-3 text-slate-600">{e.position_intitule ?? '—'}</td>
                <td className="px-4 py-3 text-slate-600">{e.department_nom ?? '—'}</td>
                <td className="px-4 py-3">
                  {e.status_libelle && (
                    <ColorBadge label={e.status_libelle} color={e.status_couleur} />
                  )}
                </td>
                <td className="px-4 py-3 text-right text-sm text-brand-700">Voir la fiche →</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
      {!loading && (
        <p className="mt-2 text-xs text-slate-400">
          {employees.length} collaborateur{employees.length > 1 ? 's' : ''}
        </p>
      )}

      {showCreate && (
        <Modal
          title="Nouveau collaborateur"
          onClose={resetCreateForm}
          maxWidthClassName="max-w-4xl"
        >
          <form onSubmit={create}>
            <EmployeeForm
              value={form}
              onChange={setForm}
              departments={departments}
              positions={positions}
              statuses={statuses}
              managers={employees}
            />
            <div className="mt-4">
              <AccountCreationFields
                enabled={createAccount}
                onToggle={(value) => {
                  setCreateAccount(value)
                  if (value && !accountEmail && form.email) setAccountEmail(form.email)
                }}
                email={accountEmail}
                onEmailChange={setAccountEmail}
                password={accountPassword}
                onPasswordChange={setAccountPassword}
              />
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={resetCreateForm}>
                Annuler
              </Button>
              <Button type="submit">Créer</Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
