import { useEffect, useState, type FormEvent } from 'react'
import {
  api,
  ApiError,
  type Department,
  type EmployeeLite,
  type Holiday,
  type LeaveType,
} from '../../lib/api'
import { Button, Card, ErrorBanner, PageHeader, Table } from '../../components/ui'

export function Parametres() {
  const [departments, setDepartments] = useState<Department[]>([])
  const [rosterByDept, setRosterByDept] = useState<Record<number, EmployeeLite[]>>({})
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const depts = await api.get<Department[]>('/departments')
      setDepartments(depts)
      const rosters = await Promise.all(
        depts.map((d) => api.get<EmployeeLite[]>(`/employees?department_id=${d.id}`)),
      )
      const map: Record<number, EmployeeLite[]> = {}
      depts.forEach((d, i) => (map[d.id] = rosters[i]))
      setRosterByDept(map)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur de chargement.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const setResponsable = async (departmentId: number, employeeId: string) => {
    setError(null)
    try {
      await api.patch(`/departments/${departmentId}/leave-responsable`, {
        employee_id: employeeId ? Number(employeeId) : null,
      })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  return (
    <div>
      <PageHeader
        title="Paramètres — Responsables congés"
        subtitle="Par département : qui peut soumettre une demande de congé au nom de ses collègues (HR-40). Toute demande reste soumise à l'approbation RH."
      />
      <ErrorBanner message={error} />

      <Card>
        <Table>
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Département</th>
              <th className="px-4 py-2">Responsable congés</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={2}>
                  Chargement…
                </td>
              </tr>
            )}
            {!loading &&
              departments.map((d) => (
                <tr key={d.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-3 font-medium text-slate-800">{d.nom}</td>
                  <td className="px-4 py-3">
                    <select
                      className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
                      value={d.leave_responsable_employee_id ?? ''}
                      onChange={(e) => setResponsable(d.id, e.target.value)}
                    >
                      <option value="">Aucun — chacun soumet sa propre demande</option>
                      {(rosterByDept[d.id] ?? []).map((emp) => (
                        <option key={emp.id} value={emp.id}>
                          {emp.full_name}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
          </tbody>
        </Table>
      </Card>

      <div className="mt-8">
        <LeaveTypesPanel />
      </div>

      <div className="mt-8">
        <HolidaysPanel />
      </div>
    </div>
  )
}

function LeaveTypesPanel() {
  const [types, setTypes] = useState<LeaveType[]>([])
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState<LeaveTypeForm | null>(null)
  const [newForm, setNewForm] = useState<LeaveTypeForm>({
    libelle: '',
    couleur: '#0288D1',
    deduit_du_solde: true,
    accrual_legal: false,
  })

  const load = async () => {
    try {
      const all = await api.get<LeaveType[]>('/leave-types?include_inactive=true')
      setTypes(all)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur de chargement.')
    }
  }

  useEffect(() => {
    load()
  }, [])

  const create = async (e: FormEvent) => {
    e.preventDefault()
    if (!newForm.libelle.trim()) return
    setError(null)
    try {
      await api.post('/leave-types', newForm)
      setNewForm({ libelle: '', couleur: '#0288D1', deduit_du_solde: true, accrual_legal: false })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const startEdit = (t: LeaveType) => {
    setEditingId(t.id)
    setEditForm({
      libelle: t.libelle,
      couleur: t.couleur,
      deduit_du_solde: t.deduit_du_solde,
      accrual_legal: t.accrual_legal,
      is_active: t.is_active,
    })
  }

  const saveEdit = async (id: number) => {
    if (!editForm) return
    setError(null)
    try {
      await api.put(`/leave-types/${id}`, editForm)
      setEditingId(null)
      setEditForm(null)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const toggleActive = async (t: LeaveType) => {
    setError(null)
    try {
      await api.put(`/leave-types/${t.id}`, { ...t, is_active: !t.is_active })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  return (
    <div>
      <PageHeader
        title="Types de congé"
        subtitle="Créez ou modifiez les types de congé disponibles. Désactiver un type le retire des nouvelles demandes sans toucher à l'historique existant."
      />
      <ErrorBanner message={error} />

      <Card className="mb-4 p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Ajouter un type de congé</h3>
        <form onSubmit={create} className="flex flex-wrap items-end gap-3">
          <div className="flex-1">
            <label className="mb-1 block text-xs text-slate-500">Libellé</label>
            <input
              required
              className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
              value={newForm.libelle}
              onChange={(e) => setNewForm({ ...newForm, libelle: e.target.value })}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-slate-500">Couleur</label>
            <input
              type="color"
              className="h-9 w-14 rounded-md border border-slate-300"
              value={newForm.couleur}
              onChange={(e) => setNewForm({ ...newForm, couleur: e.target.value })}
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={newForm.deduit_du_solde}
              onChange={(e) => setNewForm({ ...newForm, deduit_du_solde: e.target.checked })}
            />
            Déduit du solde
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={newForm.accrual_legal}
              onChange={(e) => setNewForm({ ...newForm, accrual_legal: e.target.checked })}
            />
            Accrual automatique (ancienneté)
          </label>
          <Button type="submit">Ajouter</Button>
        </form>
      </Card>

      <Card>
        <Table>
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Libellé</th>
              <th className="px-4 py-2">Couleur</th>
              <th className="px-4 py-2">Déduit du solde</th>
              <th className="px-4 py-2">Accrual auto</th>
              <th className="px-4 py-2">Statut</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {types.map((t) =>
              editingId === t.id && editForm ? (
                <tr key={t.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-3">
                    <input
                      className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
                      value={editForm.libelle}
                      onChange={(e) => setEditForm({ ...editForm, libelle: e.target.value })}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="color"
                      className="h-8 w-12 rounded-md border border-slate-300"
                      value={editForm.couleur}
                      onChange={(e) => setEditForm({ ...editForm, couleur: e.target.value })}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={editForm.deduit_du_solde}
                      onChange={(e) =>
                        setEditForm({ ...editForm, deduit_du_solde: e.target.checked })
                      }
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={editForm.accrual_legal}
                      onChange={(e) =>
                        setEditForm({ ...editForm, accrual_legal: e.target.checked })
                      }
                    />
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {editForm.is_active ? 'Actif' : 'Inactif'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      className="mr-3 text-sm text-blue-700 hover:underline"
                      onClick={() => saveEdit(t.id)}
                    >
                      Enregistrer
                    </button>
                    <button
                      className="text-sm text-slate-500 hover:underline"
                      onClick={() => {
                        setEditingId(null)
                        setEditForm(null)
                      }}
                    >
                      Annuler
                    </button>
                  </td>
                </tr>
              ) : (
                <tr key={t.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-3 font-medium text-slate-800">{t.libelle}</td>
                  <td className="px-4 py-3">
                    <span
                      className="inline-block h-4 w-4 rounded-full border border-slate-300"
                      style={{ backgroundColor: t.couleur }}
                    />
                  </td>
                  <td className="px-4 py-3 text-slate-600">{t.deduit_du_solde ? 'Oui' : 'Non'}</td>
                  <td className="px-4 py-3 text-slate-600">{t.accrual_legal ? 'Oui' : 'Non'}</td>
                  <td className="px-4 py-3">
                    <span
                      className={
                        t.is_active
                          ? 'rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700'
                          : 'rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500'
                      }
                    >
                      {t.is_active ? 'Actif' : 'Inactif'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      className="mr-3 text-sm text-blue-700 hover:underline"
                      onClick={() => startEdit(t)}
                    >
                      Modifier
                    </button>
                    <button
                      className="text-sm text-red-600 hover:underline"
                      onClick={() => toggleActive(t)}
                    >
                      {t.is_active ? 'Désactiver' : 'Réactiver'}
                    </button>
                  </td>
                </tr>
              ),
            )}
          </tbody>
        </Table>
      </Card>
    </div>
  )
}

interface LeaveTypeForm {
  libelle: string
  couleur: string
  deduit_du_solde: boolean
  accrual_legal: boolean
  is_active?: boolean
}

function HolidaysPanel() {
  const [holidays, setHolidays] = useState<Holiday[]>([])
  const [year, setYear] = useState(new Date().getFullYear())
  const [newDate, setNewDate] = useState('')
  const [newLibelle, setNewLibelle] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = async () => {
    try {
      const all = await api.get<Holiday[]>('/holidays')
      setHolidays(all)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur de chargement.')
    }
  }

  useEffect(() => {
    load()
  }, [])

  const generateFixed = async () => {
    setBusy(true)
    setError(null)
    try {
      await api.post(`/holidays/generate-fixed?annee=${year}`)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    } finally {
      setBusy(false)
    }
  }

  const addManual = async (e: FormEvent) => {
    e.preventDefault()
    if (!newDate || !newLibelle) return
    setError(null)
    try {
      await api.post('/holidays', { date: newDate, libelle: newLibelle })
      setNewDate('')
      setNewLibelle('')
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const remove = async (id: number) => {
    setError(null)
    try {
      await api.delete(`/holidays/${id}`)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const holidaysForYear = holidays.filter((h) => new Date(h.date).getFullYear() === year)

  return (
    <div>
      <PageHeader
        title="Jours fériés"
        subtitle="Les jours fériés civils à date fixe peuvent être générés automatiquement. Les fêtes religieuses mobiles (Aïd al-Fitr, Aïd al-Adha, ...) changent de date chaque année selon le calendrier lunaire et doivent être ajoutées manuellement une fois confirmées."
      />
      <ErrorBanner message={error} />

      <Card className="mb-4 flex flex-wrap items-center gap-3 p-4">
        <label className="text-sm font-medium text-slate-700">Année</label>
        <input
          type="number"
          className="w-24 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
        />
        <Button variant="secondary" onClick={generateFixed} disabled={busy}>
          {busy ? 'Génération…' : 'Générer les jours fériés fixes'}
        </Button>
      </Card>

      <Card className="mb-4 p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">
          Ajouter une fête mobile (ou tout autre jour férié)
        </h3>
        <form onSubmit={addManual} className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-xs text-slate-500">Date</label>
            <input
              type="date"
              required
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
              value={newDate}
              onChange={(e) => setNewDate(e.target.value)}
            />
          </div>
          <div className="flex-1">
            <label className="mb-1 block text-xs text-slate-500">Libellé</label>
            <input
              required
              placeholder="ex. Aïd al-Fitr"
              className="w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
              value={newLibelle}
              onChange={(e) => setNewLibelle(e.target.value)}
            />
          </div>
          <Button type="submit">Ajouter</Button>
        </form>
      </Card>

      <Card>
        <Table>
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Date</th>
              <th className="px-4 py-2">Libellé</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {holidaysForYear.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={3}>
                  Aucun jour férié pour {year}.
                </td>
              </tr>
            )}
            {holidaysForYear.map((h) => (
              <tr key={h.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-3 text-slate-600">{h.date}</td>
                <td className="px-4 py-3 text-slate-600">{h.libelle}</td>
                <td className="px-4 py-3 text-right">
                  <button
                    className="text-sm text-red-600 hover:underline"
                    onClick={() => remove(h.id)}
                  >
                    Supprimer
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </div>
  )
}
