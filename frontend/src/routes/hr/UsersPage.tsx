import { useEffect, useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  api,
  ApiError,
  type AppUser,
  type BulkUserCreateResultItem,
  type EmployeeAccountCandidate,
  type EmployeeLite,
  type Role,
  type UserCreateInput,
  type UserUpdateInput,
} from '../../lib/api'
import {
  Button,
  Card,
  ErrorBanner,
  Field,
  Input,
  Modal,
  PageHeader,
  Select,
  Table,
} from '../../components/ui'

const ROLE_LABEL: Record<Role, string> = { hr: 'RH', dg: 'DG', employee: 'Employé' }

const EMPTY_CREATE: UserCreateInput = {
  email: '',
  password: '',
  role: 'employee',
  employee_id: null,
}

export function UsersPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [users, setUsers] = useState<AppUser[]>([])
  const [availableEmployees, setAvailableEmployees] = useState<EmployeeLite[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState<UserCreateInput>(EMPTY_CREATE)

  const [editingUser, setEditingUser] = useState<AppUser | null>(null)
  const [editForm, setEditForm] = useState<UserUpdateInput | null>(null)

  const [resettingUser, setResettingUser] = useState<AppUser | null>(null)
  const [newPassword, setNewPassword] = useState('')

  const [showBulk, setShowBulk] = useState(false)
  const [bulkCandidates, setBulkCandidates] = useState<EmployeeAccountCandidate[]>([])
  const [bulkSelected, setBulkSelected] = useState<Set<number>>(new Set())
  const [bulkBusy, setBulkBusy] = useState(false)
  const [bulkResults, setBulkResults] = useState<BulkUserCreateResultItem[] | null>(null)

  const load = async () => {
    const [userList, employeeList] = await Promise.all([
      api.get<AppUser[]>('/users'),
      api.get<EmployeeLite[]>('/users/employees-sans-compte'),
    ])
    setUsers(userList)
    setAvailableEmployees(employeeList)
  }

  useEffect(() => {
    setLoading(true)
    load()
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur de chargement.'))
      .finally(() => setLoading(false))
  }, [])

  const create = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await api.post('/users', createForm)
      setShowCreate(false)
      setCreateForm(EMPTY_CREATE)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const startEdit = (u: AppUser) => {
    setEditingUser(u)
    setEditForm({ role: u.role, employee_id: u.employee_id, is_active: u.is_active })
  }

  const saveEdit = async (e: FormEvent) => {
    e.preventDefault()
    if (!editingUser || !editForm) return
    setError(null)
    try {
      await api.put(`/users/${editingUser.id}`, editForm)
      setEditingUser(null)
      setEditForm(null)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const toggleActive = async (u: AppUser) => {
    if (u.is_active && !window.confirm(`Désactiver le compte ${u.email} ?`)) return
    setError(null)
    try {
      await api.put(`/users/${u.id}`, {
        role: u.role,
        employee_id: u.employee_id,
        is_active: !u.is_active,
      })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const resetPassword = async (e: FormEvent) => {
    e.preventDefault()
    if (!resettingUser || !newPassword) return
    setError(null)
    try {
      await api.post(`/users/${resettingUser.id}/reset-password`, { password: newPassword })
      setResettingUser(null)
      setNewPassword('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const needsAccount = (c: EmployeeAccountCandidate) =>
    !c.coverage_note || !c.coverage_note.includes('non indispensable')

  const openBulk = async () => {
    setError(null)
    setBulkResults(null)
    setShowBulk(true)
    try {
      const candidates = await api.get<EmployeeAccountCandidate[]>('/users/account-candidates')
      setBulkCandidates(candidates)
      // Pre-select only the collaborateurs who actually need their own
      // login; those covered by a responsable congé start unchecked so HR
      // isn't creating 60 accounts when a handful truly need one.
      setBulkSelected(new Set(candidates.filter(needsAccount).map((c) => c.id)))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur de chargement.')
    }
  }

  useEffect(() => {
    // Coming from "Créer leurs accès maintenant" after a bulk employee
    // import (EmployeesPage) — jump straight into the bulk account modal
    // instead of leaving HR to find it on their own.
    const state = location.state as { autoOpenBulk?: boolean } | null
    if (state?.autoOpenBulk) {
      openBulk()
      navigate(location.pathname, { replace: true })
    }
  }, [location.state])

  const closeBulk = () => {
    setShowBulk(false)
    setBulkCandidates([])
    setBulkSelected(new Set())
    setBulkResults(null)
  }

  const toggleBulkSelected = (id: number) => {
    setBulkSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const submitBulk = async () => {
    if (bulkSelected.size === 0) return
    setBulkBusy(true)
    setError(null)
    try {
      const result = await api.post<{ results: BulkUserCreateResultItem[] }>('/users/bulk', {
        items: Array.from(bulkSelected).map((employee_id) => ({ employee_id })),
      })
      setBulkResults(result.results)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    } finally {
      setBulkBusy(false)
    }
  }

  const downloadBulkResultsCsv = () => {
    if (!bulkResults) return
    const lines = [
      'Collaborateur;Email;Mot de passe;Erreur',
      ...bulkResults.map(
        (r) => `${r.employee_nom};${r.email ?? ''};${r.password ?? ''};${r.error ?? ''}`,
      ),
    ]
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'comptes-crees.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <PageHeader
          title="Comptes utilisateurs"
          subtitle="Créez un accès à l'application pour un collaborateur, changez un rôle, ou désactivez un compte."
        />
        <div className="flex gap-2">
          <Button variant="secondary" onClick={openBulk}>
            Créer des comptes en masse
          </Button>
          <Button onClick={() => setShowCreate(true)}>Nouveau compte</Button>
        </div>
      </div>
      <ErrorBanner message={error} />

      <Card>
        <Table>
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Email</th>
              <th className="px-4 py-2">Rôle</th>
              <th className="px-4 py-2">Collaborateur lié</th>
              <th className="px-4 py-2">Statut</th>
              <th className="px-4 py-2">Dernière connexion</th>
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
            {!loading && users.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={6}>
                  Aucun compte.
                </td>
              </tr>
            )}
            {users.map((u) => (
              <tr key={u.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-3 font-medium text-slate-800">{u.email}</td>
                <td className="px-4 py-3 text-slate-600">{ROLE_LABEL[u.role]}</td>
                <td className="px-4 py-3 text-slate-600">{u.employee_nom ?? '—'}</td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs ${
                      u.is_active
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-slate-200 text-slate-600'
                    }`}
                  >
                    {u.is_active ? 'Actif' : 'Désactivé'}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-600">
                  {u.last_login_at ? new Date(u.last_login_at).toLocaleString('fr-FR') : '—'}
                </td>
                <td className="px-4 py-3 text-right text-sm">
                  <button
                    className="mr-3 font-medium text-brand-700 hover:underline"
                    onClick={() => startEdit(u)}
                  >
                    Modifier
                  </button>
                  <button
                    className="mr-3 text-slate-600 hover:underline"
                    onClick={() => setResettingUser(u)}
                  >
                    Mot de passe
                  </button>
                  <button
                    className={
                      u.is_active
                        ? 'text-red-600 hover:underline'
                        : 'text-emerald-700 hover:underline'
                    }
                    onClick={() => toggleActive(u)}
                  >
                    {u.is_active ? 'Désactiver' : 'Réactiver'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      {showCreate && (
        <Modal
          title="Nouveau compte"
          onClose={() => {
            setShowCreate(false)
            setCreateForm(EMPTY_CREATE)
          }}
        >
          <form onSubmit={create} className="grid grid-cols-1 gap-3">
            <Field label="Email">
              <Input
                type="email"
                required
                value={createForm.email}
                onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
              />
            </Field>
            <Field label="Mot de passe initial">
              <Input
                type="text"
                required
                minLength={8}
                value={createForm.password}
                onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })}
              />
            </Field>
            <Field label="Rôle">
              <Select
                value={createForm.role}
                onChange={(e) =>
                  setCreateForm({
                    ...createForm,
                    role: e.target.value as Role,
                    employee_id: e.target.value === 'employee' ? createForm.employee_id : null,
                  })
                }
              >
                <option value="employee">Employé</option>
                <option value="hr">RH</option>
                <option value="dg">DG</option>
              </Select>
            </Field>
            {createForm.role === 'employee' && (
              <Field label="Collaborateur">
                <Select
                  required
                  value={createForm.employee_id ?? ''}
                  onChange={(e) =>
                    setCreateForm({
                      ...createForm,
                      employee_id: e.target.value ? Number(e.target.value) : null,
                    })
                  }
                >
                  <option value="">—</option>
                  {availableEmployees.map((emp) => (
                    <option key={emp.id} value={emp.id}>
                      {emp.full_name}
                    </option>
                  ))}
                </Select>
              </Field>
            )}
            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setShowCreate(false)}>
                Annuler
              </Button>
              <Button type="submit">Créer</Button>
            </div>
          </form>
        </Modal>
      )}

      {editingUser && editForm && (
        <Modal
          title={`Modifier — ${editingUser.email}`}
          onClose={() => {
            setEditingUser(null)
            setEditForm(null)
          }}
        >
          <form onSubmit={saveEdit} className="grid grid-cols-1 gap-3">
            <Field label="Rôle">
              <Select
                value={editForm.role}
                onChange={(e) => setEditForm({ ...editForm, role: e.target.value as Role })}
              >
                <option value="employee">Employé</option>
                <option value="hr">RH</option>
                <option value="dg">DG</option>
              </Select>
            </Field>
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setEditingUser(null)
                  setEditForm(null)
                }}
              >
                Annuler
              </Button>
              <Button type="submit">Enregistrer</Button>
            </div>
          </form>
        </Modal>
      )}

      {resettingUser && (
        <Modal
          title={`Réinitialiser le mot de passe — ${resettingUser.email}`}
          onClose={() => {
            setResettingUser(null)
            setNewPassword('')
          }}
        >
          <form onSubmit={resetPassword} className="grid grid-cols-1 gap-3">
            <Field label="Nouveau mot de passe">
              <Input
                type="text"
                required
                minLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </Field>
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setResettingUser(null)
                  setNewPassword('')
                }}
              >
                Annuler
              </Button>
              <Button type="submit">Réinitialiser</Button>
            </div>
          </form>
        </Modal>
      )}

      {showBulk && (
        <Modal title="Créer des comptes en masse" onClose={closeBulk} maxWidthClassName="max-w-3xl">
          {!bulkResults ? (
            <>
              <p className="mb-3 text-sm text-slate-600">
                Les collaborateurs déjà couverts par un responsable congé de leur département sont
                décochés par défaut — ils n&apos;ont pas besoin d&apos;un accès individuel. Décochez
                ou cochez librement avant de créer les comptes.
              </p>
              {bulkCandidates.length === 0 ? (
                <p className="text-sm text-slate-400">
                  Tous les collaborateurs ont déjà un compte.
                </p>
              ) : (
                <>
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <span className="text-slate-600">
                      {bulkSelected.size} sélectionné(s) sur {bulkCandidates.length}
                    </span>
                    <div className="flex gap-3">
                      <button
                        type="button"
                        className="font-medium text-brand-700 hover:underline"
                        onClick={() => setBulkSelected(new Set(bulkCandidates.map((c) => c.id)))}
                      >
                        Tout sélectionner
                      </button>
                      <button
                        type="button"
                        className="font-medium text-brand-700 hover:underline"
                        onClick={() => setBulkSelected(new Set())}
                      >
                        Tout désélectionner
                      </button>
                    </div>
                  </div>
                  <Table>
                    <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
                      <tr>
                        <th className="px-3 py-2" />
                        <th className="px-3 py-2">Collaborateur</th>
                        <th className="px-3 py-2">Email généré</th>
                        <th className="px-3 py-2">Accès</th>
                      </tr>
                    </thead>
                    <tbody>
                      {bulkCandidates.map((c) => (
                        <tr key={c.id} className="border-b border-slate-100 last:border-0">
                          <td className="px-3 py-2">
                            <input
                              type="checkbox"
                              checked={bulkSelected.has(c.id)}
                              onChange={() => toggleBulkSelected(c.id)}
                            />
                          </td>
                          <td className="px-3 py-2 text-slate-800">
                            {c.full_name}
                            <div className="text-xs text-slate-400">
                              {[c.department_nom, c.position_intitule].filter(Boolean).join(' · ')}
                            </div>
                          </td>
                          <td className="px-3 py-2 text-slate-600">{c.suggested_email}</td>
                          <td className="px-3 py-2">
                            {c.coverage_note && (
                              <span
                                className={`text-xs ${
                                  needsAccount(c) ? 'text-amber-700' : 'text-slate-400'
                                }`}
                              >
                                {c.coverage_note}
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                  <div className="mt-4 flex justify-end gap-2">
                    <Button type="button" variant="secondary" onClick={closeBulk}>
                      Annuler
                    </Button>
                    <Button
                      type="button"
                      disabled={bulkSelected.size === 0 || bulkBusy}
                      onClick={submitBulk}
                    >
                      {bulkBusy
                        ? 'Création…'
                        : `Créer ${bulkSelected.size} compte${bulkSelected.size > 1 ? 's' : ''}`}
                    </Button>
                  </div>
                </>
              )}
            </>
          ) : (
            <>
              <p className="mb-3 text-sm text-slate-700">
                {bulkResults.filter((r) => !r.error).length} compte(s) créé(s). Communiquez ces
                identifiants aux collaborateurs concernés — ils pourront demander une
                réinitialisation du mot de passe par la suite.
              </p>
              <Table>
                <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Collaborateur</th>
                    <th className="px-3 py-2">Email</th>
                    <th className="px-3 py-2">Mot de passe</th>
                  </tr>
                </thead>
                <tbody>
                  {bulkResults.map((r) => (
                    <tr key={r.employee_id} className="border-b border-slate-100 last:border-0">
                      <td className="px-3 py-2 text-slate-800">{r.employee_nom}</td>
                      {r.error ? (
                        <td className="px-3 py-2 text-red-700" colSpan={2}>
                          {r.error}
                        </td>
                      ) : (
                        <>
                          <td className="px-3 py-2 text-slate-600">{r.email}</td>
                          <td className="px-3 py-2 font-mono text-slate-600">{r.password}</td>
                        </>
                      )}
                    </tr>
                  ))}
                </tbody>
              </Table>
              <div className="mt-4 flex justify-end gap-2">
                <Button type="button" variant="secondary" onClick={downloadBulkResultsCsv}>
                  Télécharger la liste (.csv)
                </Button>
                <Button type="button" onClick={closeBulk}>
                  Fermer
                </Button>
              </div>
            </>
          )}
        </Modal>
      )}
    </div>
  )
}
