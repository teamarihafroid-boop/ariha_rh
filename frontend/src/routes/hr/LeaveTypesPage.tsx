import { useEffect, useState, type FormEvent } from 'react'
import { api, ApiError, type LeaveType } from '../../lib/api'
import { Button, Card, ErrorBanner, Field, Input, PageHeader, Table } from '../../components/ui'

interface LeaveTypeForm {
  libelle: string
  couleur: string
  deduit_du_solde: boolean
  accrual_legal: boolean
  is_active?: boolean
}

export function LeaveTypesPage() {
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
          <Field label="Libellé" className="min-w-[10rem] flex-1">
            <Input
              required
              className="py-1.5"
              value={newForm.libelle}
              onChange={(e) => setNewForm({ ...newForm, libelle: e.target.value })}
            />
          </Field>
          <Field label="Couleur">
            <input
              type="color"
              className="h-9 w-14 rounded-lg border border-slate-300"
              value={newForm.couleur}
              onChange={(e) => setNewForm({ ...newForm, couleur: e.target.value })}
            />
          </Field>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              className="accent-brand-700"
              checked={newForm.deduit_du_solde}
              onChange={(e) => setNewForm({ ...newForm, deduit_du_solde: e.target.checked })}
            />
            Déduit du solde
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              className="accent-brand-700"
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
                    <Input
                      className="py-1"
                      value={editForm.libelle}
                      onChange={(e) => setEditForm({ ...editForm, libelle: e.target.value })}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="color"
                      className="h-8 w-12 rounded-lg border border-slate-300"
                      value={editForm.couleur}
                      onChange={(e) => setEditForm({ ...editForm, couleur: e.target.value })}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      className="accent-brand-700"
                      checked={editForm.deduit_du_solde}
                      onChange={(e) =>
                        setEditForm({ ...editForm, deduit_du_solde: e.target.checked })
                      }
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      className="accent-brand-700"
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
                      className="mr-3 text-sm font-medium text-brand-700 hover:underline"
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
                      className="mr-3 text-sm font-medium text-brand-700 hover:underline"
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
