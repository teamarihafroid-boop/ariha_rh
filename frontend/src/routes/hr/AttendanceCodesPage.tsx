import { useEffect, useState, type FormEvent } from 'react'
import { api, ApiError, type AttendanceCode } from '../../lib/api'
import { Button, Card, ErrorBanner, Field, Input, PageHeader, Table } from '../../components/ui'

interface CodeForm {
  libelle: string
  code_court: string
  couleur: string
  compte_absence: boolean
  is_active?: boolean
}

const EMPTY_FORM: CodeForm = {
  libelle: '',
  code_court: '',
  couleur: '#607D8B',
  compte_absence: false,
}

export function AttendanceCodesPage() {
  const [codes, setCodes] = useState<AttendanceCode[]>([])
  const [error, setError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState<CodeForm | null>(null)
  const [newForm, setNewForm] = useState<CodeForm>(EMPTY_FORM)

  const load = async () => {
    try {
      const all = await api.get<AttendanceCode[]>('/attendance/codes?include_inactive=true')
      setCodes(all)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur de chargement.')
    }
  }

  useEffect(() => {
    load()
  }, [])

  const create = async (e: FormEvent) => {
    e.preventDefault()
    if (!newForm.libelle.trim() || !newForm.code_court.trim()) return
    setError(null)
    try {
      await api.post('/attendance/codes', newForm)
      setNewForm(EMPTY_FORM)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const startEdit = (c: AttendanceCode) => {
    setEditingId(c.id)
    setEditForm({
      libelle: c.libelle,
      code_court: c.code_court,
      couleur: c.couleur,
      compte_absence: c.compte_absence,
      is_active: c.is_active,
    })
  }

  const saveEdit = async (id: number) => {
    if (!editForm) return
    setError(null)
    try {
      await api.put(`/attendance/codes/${id}`, editForm)
      setEditingId(null)
      setEditForm(null)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const toggleActive = async (c: AttendanceCode) => {
    setError(null)
    try {
      await api.put(`/attendance/codes/${c.id}`, { ...c, is_active: !c.is_active })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  return (
    <div>
      <PageHeader
        title="Codes de présence"
        subtitle="Les codes utilisés pour interpréter les cellules d'un pointage importé (ex. P = présent, A = absence) et affichés sur l'export Excel mensuel."
      />
      <ErrorBanner message={error} />

      <Card className="mb-4 p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">Ajouter un code</h3>
        <form onSubmit={create} className="flex flex-wrap items-end gap-3">
          <Field label="Libellé" className="min-w-[10rem] flex-1">
            <Input
              required
              className="py-1.5"
              value={newForm.libelle}
              onChange={(e) => setNewForm({ ...newForm, libelle: e.target.value })}
            />
          </Field>
          <Field label="Code court">
            <Input
              required
              className="w-20 py-1.5"
              placeholder="ex. P"
              maxLength={8}
              value={newForm.code_court}
              onChange={(e) => setNewForm({ ...newForm, code_court: e.target.value.toUpperCase() })}
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
              checked={newForm.compte_absence}
              onChange={(e) => setNewForm({ ...newForm, compte_absence: e.target.checked })}
            />
            Compte comme absence
          </label>
          <Button type="submit">Ajouter</Button>
        </form>
      </Card>

      <Card>
        <Table>
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Libellé</th>
              <th className="px-4 py-2">Code</th>
              <th className="px-4 py-2">Couleur</th>
              <th className="px-4 py-2">Absence</th>
              <th className="px-4 py-2">Statut</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {codes.map((c) =>
              editingId === c.id && editForm ? (
                <tr key={c.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-3">
                    <Input
                      className="py-1"
                      value={editForm.libelle}
                      onChange={(e) => setEditForm({ ...editForm, libelle: e.target.value })}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <Input
                      className="w-20 py-1"
                      maxLength={8}
                      value={editForm.code_court}
                      onChange={(e) =>
                        setEditForm({ ...editForm, code_court: e.target.value.toUpperCase() })
                      }
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
                      checked={editForm.compte_absence}
                      onChange={(e) =>
                        setEditForm({ ...editForm, compte_absence: e.target.checked })
                      }
                    />
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {editForm.is_active ? 'Actif' : 'Inactif'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      className="mr-3 text-sm font-medium text-brand-700 hover:underline"
                      onClick={() => saveEdit(c.id)}
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
                <tr key={c.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-4 py-3 font-medium text-slate-800">{c.libelle}</td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-600">{c.code_court}</td>
                  <td className="px-4 py-3">
                    <span
                      className="inline-block h-4 w-4 rounded-full border border-slate-300"
                      style={{ backgroundColor: c.couleur }}
                    />
                  </td>
                  <td className="px-4 py-3 text-slate-600">{c.compte_absence ? 'Oui' : 'Non'}</td>
                  <td className="px-4 py-3">
                    <span
                      className={
                        c.is_active
                          ? 'rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700'
                          : 'rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500'
                      }
                    >
                      {c.is_active ? 'Actif' : 'Inactif'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      className="mr-3 text-sm font-medium text-brand-700 hover:underline"
                      onClick={() => startEdit(c)}
                    >
                      Modifier
                    </button>
                    <button
                      className="text-sm text-red-600 hover:underline"
                      onClick={() => toggleActive(c)}
                    >
                      {c.is_active ? 'Désactiver' : 'Réactiver'}
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
