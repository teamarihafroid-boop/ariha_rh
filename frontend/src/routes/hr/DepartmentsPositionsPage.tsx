import { useEffect, useState, type FormEvent } from 'react'
import { api, ApiError, type Department, type Position } from '../../lib/api'
import {
  Button,
  Card,
  ErrorBanner,
  Field,
  Input,
  PageHeader,
  Select,
  Table,
} from '../../components/ui'

interface DepartmentForm {
  nom: string
  description: string
  is_active?: boolean
}

interface PositionForm {
  intitule: string
  department_id: number | null
  is_active?: boolean
}

const EMPTY_DEPARTMENT_FORM: DepartmentForm = { nom: '', description: '' }
const EMPTY_POSITION_FORM: PositionForm = { intitule: '', department_id: null }

export function DepartmentsPositionsPage() {
  const [departments, setDepartments] = useState<Department[]>([])
  const [positions, setPositions] = useState<Position[]>([])
  const [error, setError] = useState<string | null>(null)

  const [newDept, setNewDept] = useState<DepartmentForm>(EMPTY_DEPARTMENT_FORM)
  const [editingDeptId, setEditingDeptId] = useState<number | null>(null)
  const [editDeptForm, setEditDeptForm] = useState<DepartmentForm | null>(null)

  const [newPosition, setNewPosition] = useState<PositionForm>(EMPTY_POSITION_FORM)
  const [editingPositionId, setEditingPositionId] = useState<number | null>(null)
  const [editPositionForm, setEditPositionForm] = useState<PositionForm | null>(null)

  const load = async () => {
    try {
      const [d, p] = await Promise.all([
        api.get<Department[]>('/departments?include_inactive=true'),
        api.get<Position[]>('/positions?include_inactive=true'),
      ])
      setDepartments(d)
      setPositions(p)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur de chargement.')
    }
  }

  useEffect(() => {
    load()
  }, [])

  // --- Départements ---

  const createDepartment = async (e: FormEvent) => {
    e.preventDefault()
    if (!newDept.nom.trim()) return
    setError(null)
    try {
      await api.post('/departments', { nom: newDept.nom, description: newDept.description || null })
      setNewDept(EMPTY_DEPARTMENT_FORM)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const startEditDept = (d: Department) => {
    setEditingDeptId(d.id)
    setEditDeptForm({ nom: d.nom, description: d.description ?? '', is_active: d.is_active })
  }

  const saveEditDept = async (id: number) => {
    if (!editDeptForm) return
    setError(null)
    try {
      await api.put(`/departments/${id}`, {
        nom: editDeptForm.nom,
        description: editDeptForm.description || null,
        is_active: editDeptForm.is_active ?? true,
      })
      setEditingDeptId(null)
      setEditDeptForm(null)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const toggleDeptActive = async (d: Department) => {
    setError(null)
    try {
      await api.put(`/departments/${d.id}`, {
        nom: d.nom,
        description: d.description,
        is_active: !d.is_active,
      })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  // --- Postes ---

  const createPosition = async (e: FormEvent) => {
    e.preventDefault()
    if (!newPosition.intitule.trim()) return
    setError(null)
    try {
      await api.post('/positions', {
        intitule: newPosition.intitule,
        department_id: newPosition.department_id,
      })
      setNewPosition(EMPTY_POSITION_FORM)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const startEditPosition = (p: Position) => {
    setEditingPositionId(p.id)
    setEditPositionForm({
      intitule: p.intitule,
      department_id: p.department_id,
      is_active: p.is_active,
    })
  }

  const saveEditPosition = async (id: number) => {
    if (!editPositionForm) return
    setError(null)
    try {
      await api.put(`/positions/${id}`, {
        intitule: editPositionForm.intitule,
        department_id: editPositionForm.department_id,
        is_active: editPositionForm.is_active ?? true,
      })
      setEditingPositionId(null)
      setEditPositionForm(null)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const togglePositionActive = async (p: Position) => {
    setError(null)
    try {
      await api.put(`/positions/${p.id}`, {
        intitule: p.intitule,
        department_id: p.department_id,
        is_active: !p.is_active,
      })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const departmentName = (id: number | null) =>
    id ? (departments.find((d) => d.id === id)?.nom ?? '—') : '—'

  return (
    <div>
      <PageHeader
        title="Départements & Postes"
        subtitle="Gérez la structure organisationnelle : départements et postes disponibles pour les fiches employés et les offres d'emploi. Désactiver retire l'élément des nouveaux choix sans toucher à l'historique existant."
      />
      <ErrorBanner message={error} />

      <h2 className="mb-3 text-sm font-semibold text-slate-700">Départements</h2>
      <Card className="mb-4 p-4">
        <form onSubmit={createDepartment} className="flex flex-wrap items-end gap-3">
          <Field label="Nom" className="min-w-[10rem] flex-1">
            <Input
              required
              value={newDept.nom}
              onChange={(e) => setNewDept({ ...newDept, nom: e.target.value })}
            />
          </Field>
          <Field label="Description" className="min-w-[14rem] flex-[2]">
            <Input
              value={newDept.description}
              onChange={(e) => setNewDept({ ...newDept, description: e.target.value })}
            />
          </Field>
          <Button type="submit">Ajouter</Button>
        </form>
      </Card>

      <Card className="mb-8">
        <Table>
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Nom</th>
              <th className="px-4 py-2">Description</th>
              <th className="px-4 py-2">Statut</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {departments.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={4}>
                  Aucun département.
                </td>
              </tr>
            )}
            {departments.map((d) =>
              editingDeptId === d.id && editDeptForm ? (
                <tr key={d.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-3">
                    <Input
                      className="py-1"
                      value={editDeptForm.nom}
                      onChange={(e) => setEditDeptForm({ ...editDeptForm, nom: e.target.value })}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <Input
                      className="py-1"
                      value={editDeptForm.description}
                      onChange={(e) =>
                        setEditDeptForm({ ...editDeptForm, description: e.target.value })
                      }
                    />
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {editDeptForm.is_active ? 'Actif' : 'Inactif'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      className="mr-3 text-sm font-medium text-brand-700 hover:underline"
                      onClick={() => saveEditDept(d.id)}
                    >
                      Enregistrer
                    </button>
                    <button
                      className="text-sm text-slate-500 hover:underline"
                      onClick={() => {
                        setEditingDeptId(null)
                        setEditDeptForm(null)
                      }}
                    >
                      Annuler
                    </button>
                  </td>
                </tr>
              ) : (
                <tr key={d.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-3 font-medium text-slate-800">{d.nom}</td>
                  <td className="px-4 py-3 text-slate-600">{d.description ?? '—'}</td>
                  <td className="px-4 py-3">
                    <span
                      className={
                        d.is_active
                          ? 'rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700'
                          : 'rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500'
                      }
                    >
                      {d.is_active ? 'Actif' : 'Inactif'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      className="mr-3 text-sm font-medium text-brand-700 hover:underline"
                      onClick={() => startEditDept(d)}
                    >
                      Modifier
                    </button>
                    <button
                      className="text-sm text-red-600 hover:underline"
                      onClick={() => toggleDeptActive(d)}
                    >
                      {d.is_active ? 'Désactiver' : 'Réactiver'}
                    </button>
                  </td>
                </tr>
              ),
            )}
          </tbody>
        </Table>
      </Card>

      <h2 className="mb-3 text-sm font-semibold text-slate-700">Postes</h2>
      <Card className="mb-4 p-4">
        <form onSubmit={createPosition} className="flex flex-wrap items-end gap-3">
          <Field label="Intitulé" className="min-w-[10rem] flex-1">
            <Input
              required
              value={newPosition.intitule}
              onChange={(e) => setNewPosition({ ...newPosition, intitule: e.target.value })}
            />
          </Field>
          <Field label="Département">
            <Select
              value={newPosition.department_id ?? ''}
              onChange={(e) =>
                setNewPosition({
                  ...newPosition,
                  department_id: e.target.value ? Number(e.target.value) : null,
                })
              }
            >
              <option value="">— (partagé entre départements)</option>
              {departments
                .filter((d) => d.is_active)
                .map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.nom}
                  </option>
                ))}
            </Select>
          </Field>
          <Button type="submit">Ajouter</Button>
        </form>
      </Card>

      <Card>
        <Table>
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Intitulé</th>
              <th className="px-4 py-2">Département</th>
              <th className="px-4 py-2">Statut</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={4}>
                  Aucun poste.
                </td>
              </tr>
            )}
            {positions.map((p) =>
              editingPositionId === p.id && editPositionForm ? (
                <tr key={p.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-3">
                    <Input
                      className="py-1"
                      value={editPositionForm.intitule}
                      onChange={(e) =>
                        setEditPositionForm({ ...editPositionForm, intitule: e.target.value })
                      }
                    />
                  </td>
                  <td className="px-4 py-3">
                    <Select
                      className="py-1"
                      value={editPositionForm.department_id ?? ''}
                      onChange={(e) =>
                        setEditPositionForm({
                          ...editPositionForm,
                          department_id: e.target.value ? Number(e.target.value) : null,
                        })
                      }
                    >
                      <option value="">— (partagé)</option>
                      {departments
                        .filter((d) => d.is_active)
                        .map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.nom}
                          </option>
                        ))}
                    </Select>
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {editPositionForm.is_active ? 'Actif' : 'Inactif'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      className="mr-3 text-sm font-medium text-brand-700 hover:underline"
                      onClick={() => saveEditPosition(p.id)}
                    >
                      Enregistrer
                    </button>
                    <button
                      className="text-sm text-slate-500 hover:underline"
                      onClick={() => {
                        setEditingPositionId(null)
                        setEditPositionForm(null)
                      }}
                    >
                      Annuler
                    </button>
                  </td>
                </tr>
              ) : (
                <tr key={p.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-3 font-medium text-slate-800">{p.intitule}</td>
                  <td className="px-4 py-3 text-slate-600">{departmentName(p.department_id)}</td>
                  <td className="px-4 py-3">
                    <span
                      className={
                        p.is_active
                          ? 'rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700'
                          : 'rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500'
                      }
                    >
                      {p.is_active ? 'Actif' : 'Inactif'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      className="mr-3 text-sm font-medium text-brand-700 hover:underline"
                      onClick={() => startEditPosition(p)}
                    >
                      Modifier
                    </button>
                    <button
                      className="text-sm text-red-600 hover:underline"
                      onClick={() => togglePositionActive(p)}
                    >
                      {p.is_active ? 'Désactiver' : 'Réactiver'}
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
