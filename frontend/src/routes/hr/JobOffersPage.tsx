import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  api,
  ApiError,
  type Department,
  type JobOffer,
  type JobOfferInput,
  type JobOfferStatus,
  type Position,
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
  Textarea,
} from '../../components/ui'

function defaultStatusId(statuses: JobOfferStatus[]): number {
  return (statuses.find((s) => s.libelle === 'Ouverte') ?? statuses[0])?.id ?? 0
}

const emptyForm = (statusId: number): JobOfferInput => ({
  titre: '',
  ville: null,
  department_id: null,
  position_id: null,
  status_id: statusId,
  description: null,
  responsable: null,
  date_cloture: null,
})

function offerToForm(o: JobOffer): JobOfferInput {
  return {
    titre: o.titre,
    ville: o.ville,
    department_id: o.department_id,
    position_id: o.position_id,
    status_id: o.status_id,
    description: o.description,
    responsable: o.responsable,
    date_cloture: o.date_cloture,
  }
}

export function JobOffersPage() {
  const navigate = useNavigate()
  const [offers, setOffers] = useState<JobOffer[]>([])
  const [statuses, setStatuses] = useState<JobOfferStatus[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [positions, setPositions] = useState<Position[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [q, setQ] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<JobOfferInput>(emptyForm(0))

  const [editingOffer, setEditingOffer] = useState<JobOffer | null>(null)
  const [editForm, setEditForm] = useState<JobOfferInput | null>(null)

  const filteredOffers = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return offers.filter((o) => {
      if (statusFilter && String(o.status_id) !== statusFilter) return false
      if (!needle) return true
      return [o.titre, o.ville, o.department_nom, o.position_intitule]
        .filter(Boolean)
        .some((v) => v!.toLowerCase().includes(needle))
    })
  }, [offers, q, statusFilter])

  useEffect(() => {
    Promise.all([
      api.get<JobOffer[]>('/recruitment/job-offers'),
      api.get<JobOfferStatus[]>('/recruitment/job-offer-statuses'),
      api.get<Department[]>('/departments?include_inactive=true'),
      api.get<Position[]>('/positions?include_inactive=true'),
    ])
      .then(([o, s, d, p]) => {
        setOffers(o)
        setStatuses(s)
        setDepartments(d)
        setPositions(p)
        if (s.length > 0) setForm(emptyForm(defaultStatusId(s)))
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur de chargement.'))
      .finally(() => setLoading(false))
  }, [])

  const reload = () => api.get<JobOffer[]>('/recruitment/job-offers').then(setOffers)

  const create = async (e: FormEvent) => {
    e.preventDefault()
    if (!form.titre.trim()) return
    setError(null)
    try {
      await api.post('/recruitment/job-offers', form)
      setShowCreate(false)
      setForm(emptyForm(defaultStatusId(statuses)))
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const startEdit = (o: JobOffer) => {
    setEditingOffer(o)
    setEditForm(offerToForm(o))
  }

  const saveEdit = async (e: FormEvent) => {
    e.preventDefault()
    if (!editingOffer || !editForm) return
    setError(null)
    try {
      await api.put(`/recruitment/job-offers/${editingOffer.id}`, editForm)
      setEditingOffer(null)
      setEditForm(null)
      await reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  // Options are filtered to active ones, plus the currently selected id if
  // it's since been deactivated — so a new offer can't be assigned to a
  // deactivated département/poste, while editing an existing offer still
  // shows its current (possibly deactivated) assignment.
  const renderFields = (value: JobOfferInput, onChange: (next: JobOfferInput) => void) => (
    <>
      <Field label="Titre">
        <Input
          required
          value={value.titre}
          onChange={(e) => onChange({ ...value, titre: e.target.value })}
        />
      </Field>
      <Field label="Ville">
        <Input
          value={value.ville ?? ''}
          onChange={(e) => onChange({ ...value, ville: e.target.value || null })}
        />
      </Field>
      <Field label="Responsable">
        <Input
          value={value.responsable ?? ''}
          onChange={(e) => onChange({ ...value, responsable: e.target.value || null })}
        />
      </Field>
      <Field label="Département">
        <Select
          value={value.department_id ?? ''}
          onChange={(e) =>
            onChange({
              ...value,
              department_id: e.target.value ? Number(e.target.value) : null,
            })
          }
        >
          <option value="">—</option>
          {departments
            .filter((d) => d.is_active || d.id === value.department_id)
            .map((d) => (
              <option key={d.id} value={d.id}>
                {d.nom}
                {!d.is_active ? ' (inactif)' : ''}
              </option>
            ))}
        </Select>
      </Field>
      <Field label="Poste">
        <Select
          value={value.position_id ?? ''}
          onChange={(e) =>
            onChange({ ...value, position_id: e.target.value ? Number(e.target.value) : null })
          }
        >
          <option value="">—</option>
          {positions
            .filter((p) => p.is_active || p.id === value.position_id)
            .map((p) => (
              <option key={p.id} value={p.id}>
                {p.intitule}
                {!p.is_active ? ' (inactif)' : ''}
              </option>
            ))}
        </Select>
      </Field>
      <Field label="Statut">
        <Select
          value={value.status_id}
          onChange={(e) => onChange({ ...value, status_id: Number(e.target.value) })}
        >
          {statuses.map((s) => (
            <option key={s.id} value={s.id}>
              {s.libelle}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="Date de clôture">
        <Input
          type="date"
          value={value.date_cloture ?? ''}
          onChange={(e) => onChange({ ...value, date_cloture: e.target.value || null })}
        />
      </Field>
      <Field label="Description" className="sm:col-span-2 lg:col-span-3">
        <Textarea
          rows={3}
          value={value.description ?? ''}
          onChange={(e) => onChange({ ...value, description: e.target.value || null })}
        />
      </Field>
    </>
  )

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <PageHeader
          title="Offres d'emploi"
          subtitle="Créez et gérez les offres ouvertes au recrutement."
        />
        <Button onClick={() => setShowCreate((s) => !s)}>
          {showCreate ? 'Fermer' : 'Nouvelle offre'}
        </Button>
      </div>
      <ErrorBanner message={error} />

      {showCreate && (
        <Card className="mb-4 p-4">
          <form onSubmit={create} className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {renderFields(form, setForm)}
            <div className="sm:col-span-2 lg:col-span-3">
              <Button type="submit">Créer l'offre</Button>
            </div>
          </form>
        </Card>
      )}

      <Card className="mb-4 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Recherche" className="min-w-[12rem] flex-1">
            <Input
              placeholder="Titre, ville, département, poste…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </Field>
          <Field label="Statut">
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">Tous</option>
              {statuses.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.libelle}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      </Card>

      <Card>
        <Table>
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Titre</th>
              <th className="px-4 py-2">Poste</th>
              <th className="px-4 py-2">Ville</th>
              <th className="px-4 py-2">Département</th>
              <th className="px-4 py-2">Statut</th>
              <th className="px-4 py-2">Candidatures</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={7}>
                  Chargement…
                </td>
              </tr>
            )}
            {!loading && filteredOffers.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={7}>
                  Aucune offre ne correspond à cette recherche.
                </td>
              </tr>
            )}
            {filteredOffers.map((o) => (
              <tr key={o.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-3 font-medium text-slate-800">{o.titre}</td>
                <td className="px-4 py-3 text-slate-600">{o.position_intitule ?? '—'}</td>
                <td className="px-4 py-3 text-slate-600">{o.ville ?? '—'}</td>
                <td className="px-4 py-3 text-slate-600">{o.department_nom ?? '—'}</td>
                <td className="px-4 py-3">
                  <ColorBadge label={o.status_libelle} color={o.status_couleur} />
                </td>
                <td className="px-4 py-3">
                  <button
                    className="text-sm text-brand-700 hover:underline disabled:cursor-default disabled:text-slate-400 disabled:no-underline"
                    disabled={o.candidatures_count === 0}
                    onClick={() => navigate(`/hr/recrutement/pipeline?offre=${o.id}`)}
                  >
                    {o.candidatures_count} candidature{o.candidatures_count > 1 ? 's' : ''}
                  </button>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    className="text-sm font-medium text-brand-700 hover:underline"
                    onClick={() => startEdit(o)}
                  >
                    Modifier
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      {editingOffer && editForm && (
        <Modal
          title={`Modifier — ${editingOffer.titre}`}
          onClose={() => {
            setEditingOffer(null)
            setEditForm(null)
          }}
          maxWidthClassName="max-w-2xl"
        >
          <form onSubmit={saveEdit} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {renderFields(editForm, setEditForm)}
            <div className="sm:col-span-2 flex justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setEditingOffer(null)
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
    </div>
  )
}
