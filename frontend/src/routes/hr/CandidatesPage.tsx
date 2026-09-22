import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  api,
  ApiError,
  type Candidate,
  type CandidateCreateResult,
  type CandidateInput,
  type CvFields,
  type JobOffer,
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
  Textarea,
} from '../../components/ui'
import { CANDIDATE_ATTACHMENT_TYPES, formatFileSize } from '../../lib/documentTypes'

const EMPTY_FORM: CandidateInput = {
  nom_complet: '',
  telephone: null,
  email: null,
  ville: null,
  annees_experience: null,
  experience_resume: null,
  competences: null,
  diplomes: null,
  langues: null,
  favori: false,
  notes: null,
}

function candidateToForm(c: Candidate): CandidateInput {
  return {
    nom_complet: c.nom_complet,
    telephone: c.telephone,
    email: c.email,
    ville: c.ville,
    annees_experience: c.annees_experience,
    experience_resume: c.experience_resume,
    competences: c.competences,
    diplomes: c.diplomes,
    langues: c.langues,
    favori: c.favori,
    notes: c.notes,
  }
}

export function CandidatesPage() {
  const navigate = useNavigate()
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [offers, setOffers] = useState<JobOffer[]>([])
  const [error, setError] = useState<string | null>(null)
  const [warning, setWarning] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [q, setQ] = useState('')
  const [ville, setVille] = useState('')
  const [favoriOnly, setFavoriOnly] = useState(false)
  const skipNextAutoSearch = useRef(true)

  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState<CandidateInput>(EMPTY_FORM)
  const [createOfferId, setCreateOfferId] = useState('')
  const [extractFile, setExtractFile] = useState<File | null>(null)
  const [extracting, setExtracting] = useState(false)
  const [extractError, setExtractError] = useState<string | null>(null)

  const [editingCandidate, setEditingCandidate] = useState<Candidate | null>(null)
  const [editForm, setEditForm] = useState<CandidateInput | null>(null)

  const [attachType, setAttachType] = useState(CANDIDATE_ATTACHMENT_TYPES[0])
  const [attachFile, setAttachFile] = useState<File | null>(null)
  const [attachUploading, setAttachUploading] = useState(false)

  const load = async () => {
    const params = new URLSearchParams()
    if (q) params.set('q', q)
    if (ville) params.set('ville', ville)
    if (favoriOnly) params.set('favori', 'true')
    const list = await api.get<Candidate[]>(`/recruitment/candidates?${params.toString()}`)
    setCandidates(list)
    return list
  }

  useEffect(() => {
    setLoading(true)
    load()
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur de chargement.'))
      .finally(() => setLoading(false))
    // The offer picker is a nice-to-have on top of the candidate list — a
    // failure here shouldn't block or error the whole page, just leave the
    // dropdown with only its "no offer" option.
    api
      .get<JobOffer[]>('/recruitment/job-offers')
      .then(setOffers)
      .catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (skipNextAutoSearch.current) {
      skipNextAutoSearch.current = false
      return
    }
    const timer = setTimeout(() => {
      load().catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur.'))
    }, 300)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, ville, favoriOnly])

  const resetFilters = () => {
    setQ('')
    setVille('')
    setFavoriOnly(false)
  }

  const extractCv = async () => {
    if (!extractFile) return
    setExtractError(null)
    setExtracting(true)
    try {
      const formData = new FormData()
      formData.append('file', extractFile)
      const fields = await api.upload<CvFields>('/recruitment/candidates/extract-cv', formData)
      setForm((prev) => ({
        ...prev,
        nom_complet: prev.nom_complet || fields.nom_complet || '',
        telephone: prev.telephone || fields.telephone,
        email: prev.email || fields.email,
        ville: prev.ville || fields.ville,
        experience_resume: prev.experience_resume || fields.experience_resume,
        competences: prev.competences || fields.competences,
        diplomes: prev.diplomes || fields.diplomes,
        langues: prev.langues || fields.langues,
      }))
    } catch (err) {
      setExtractError(err instanceof ApiError ? err.message : 'Erreur.')
    } finally {
      setExtracting(false)
    }
  }

  const create = async (e: FormEvent) => {
    e.preventDefault()
    if (!form.nom_complet.trim()) return
    setError(null)
    setWarning(null)
    try {
      const result = await api.post<CandidateCreateResult>('/recruitment/candidates', form)
      const warnings: string[] = []
      if (result.duplicates.length > 0) {
        warnings.push(
          `Doublon possible : ${result.duplicates.map((d) => d.nom_complet).join(', ')} partage(nt) le même email ou téléphone.`,
        )
      }
      if (extractFile) {
        try {
          const attachFormData = new FormData()
          attachFormData.append('file', extractFile)
          await api.upload(
            `/recruitment/candidates/${result.candidate.id}/attachments?type_document=CV`,
            attachFormData,
          )
        } catch {
          warnings.push(
            "Le candidat a été créé, mais le CV n'a pas pu être enregistré en pièce jointe.",
          )
        }
      }
      if (createOfferId) {
        try {
          await api.post('/recruitment/applications', {
            candidate_id: result.candidate.id,
            job_offer_id: Number(createOfferId),
            responsable: null,
          })
        } catch (err) {
          warnings.push(
            `Le candidat a été créé, mais n'a pas pu être ajouté au pipeline de l'offre : ${
              err instanceof ApiError ? err.message : 'erreur inconnue'
            }`,
          )
        }
      }
      if (warnings.length > 0) setWarning(warnings.join(' '))
      setShowCreate(false)
      setForm(EMPTY_FORM)
      setCreateOfferId('')
      setExtractFile(null)
      setExtractError(null)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const toggleFavori = async (c: Candidate) => {
    setError(null)
    try {
      await api.put(`/recruitment/candidates/${c.id}`, { ...candidateToForm(c), favori: !c.favori })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const startEdit = (c: Candidate) => {
    setEditingCandidate(c)
    setEditForm(candidateToForm(c))
  }

  const saveEdit = async (e: FormEvent) => {
    e.preventDefault()
    if (!editingCandidate || !editForm) return
    setError(null)
    try {
      await api.put(`/recruitment/candidates/${editingCandidate.id}`, editForm)
      setEditingCandidate(null)
      setEditForm(null)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const refreshEditingCandidate = async (candidateId: number) => {
    const list = await load()
    const refreshed = list.find((c) => c.id === candidateId)
    if (refreshed) setEditingCandidate(refreshed)
  }

  const uploadAttachment = async (e: FormEvent) => {
    e.preventDefault()
    if (!editingCandidate || !attachFile) return
    setError(null)
    setAttachUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', attachFile)
      const params = new URLSearchParams({ type_document: attachType })
      await api.upload(
        `/recruitment/candidates/${editingCandidate.id}/attachments?${params.toString()}`,
        formData,
      )
      setAttachFile(null)
      await refreshEditingCandidate(editingCandidate.id)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    } finally {
      setAttachUploading(false)
    }
  }

  const removeAttachment = async (attachmentId: number) => {
    if (!editingCandidate) return
    setError(null)
    try {
      await api.delete(`/recruitment/candidates/${editingCandidate.id}/attachments/${attachmentId}`)
      await refreshEditingCandidate(editingCandidate.id)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const renderFields = (value: CandidateInput, onChange: (next: CandidateInput) => void) => (
    <>
      <Field label="Nom complet" className="sm:col-span-2">
        <Input
          required
          value={value.nom_complet}
          onChange={(e) => onChange({ ...value, nom_complet: e.target.value })}
        />
      </Field>
      <Field label="Téléphone">
        <Input
          value={value.telephone ?? ''}
          onChange={(e) => onChange({ ...value, telephone: e.target.value || null })}
        />
      </Field>
      <Field label="Email">
        <Input
          type="email"
          value={value.email ?? ''}
          onChange={(e) => onChange({ ...value, email: e.target.value || null })}
        />
      </Field>
      <Field label="Ville">
        <Input
          value={value.ville ?? ''}
          onChange={(e) => onChange({ ...value, ville: e.target.value || null })}
        />
      </Field>
      <Field label="Années d'expérience">
        <Input
          type="number"
          step="0.5"
          value={value.annees_experience ?? ''}
          onChange={(e) => onChange({ ...value, annees_experience: e.target.value || null })}
        />
      </Field>
      <Field label="Résumé d'expérience" className="sm:col-span-2">
        <Textarea
          rows={2}
          value={value.experience_resume ?? ''}
          onChange={(e) => onChange({ ...value, experience_resume: e.target.value || null })}
        />
      </Field>
      <Field label="Compétences" className="sm:col-span-2">
        <Textarea
          rows={2}
          value={value.competences ?? ''}
          onChange={(e) => onChange({ ...value, competences: e.target.value || null })}
        />
      </Field>
      <Field label="Diplômes" className="sm:col-span-2">
        <Textarea
          rows={2}
          value={value.diplomes ?? ''}
          onChange={(e) => onChange({ ...value, diplomes: e.target.value || null })}
        />
      </Field>
      <Field label="Langues" className="sm:col-span-2">
        <Input
          value={value.langues ?? ''}
          onChange={(e) => onChange({ ...value, langues: e.target.value || null })}
        />
      </Field>
      <Field label="Notes" className="sm:col-span-2">
        <Textarea
          rows={2}
          value={value.notes ?? ''}
          onChange={(e) => onChange({ ...value, notes: e.target.value || null })}
        />
      </Field>
    </>
  )

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <PageHeader
          title="Banque de CV"
          subtitle="Saisie manuelle ou import d'un CV pour pré-remplir la fiche."
        />
        <Button onClick={() => setShowCreate(true)}>Nouveau candidat</Button>
      </div>
      <ErrorBanner message={error} />
      {warning && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {warning}
        </div>
      )}

      <Card className="mb-4 p-4">
        <form onSubmit={(e) => e.preventDefault()} className="flex flex-wrap items-end gap-3">
          <Field label="Recherche" className="min-w-[12rem] flex-1">
            <Input
              placeholder="Nom, email, téléphone…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </Field>
          <Field label="Ville">
            <Input value={ville} onChange={(e) => setVille(e.target.value)} />
          </Field>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              className="accent-brand-700"
              checked={favoriOnly}
              onChange={(e) => setFavoriOnly(e.target.checked)}
            />
            Favoris uniquement
          </label>
          {(q || ville || favoriOnly) && (
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
              <th className="px-4 py-2">Ville</th>
              <th className="px-4 py-2">Contact</th>
              <th className="px-4 py-2">Candidatures</th>
              <th className="px-4 py-2">Favori</th>
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
            {!loading && candidates.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={6}>
                  Aucun candidat ne correspond à cette recherche.
                </td>
              </tr>
            )}
            {candidates.map((c) => (
              <tr key={c.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-3 font-medium text-slate-800">{c.nom_complet}</td>
                <td className="px-4 py-3 text-slate-600">{c.ville ?? '—'}</td>
                <td className="px-4 py-3 text-slate-600">
                  {[c.telephone, c.email].filter(Boolean).join(' · ') || '—'}
                </td>
                <td className="px-4 py-3">
                  {c.employee_id != null ? (
                    <button
                      className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800 hover:bg-emerald-200"
                      onClick={() => navigate(`/hr/collaborateurs/${c.employee_id}`)}
                    >
                      Embauché — voir la fiche →
                    </button>
                  ) : c.applications.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {c.applications.map((a) => (
                        <button
                          key={a.id}
                          className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700 hover:bg-slate-200"
                          onClick={() =>
                            navigate(`/hr/recrutement/pipeline?offre=${a.job_offer_id}`)
                          }
                          title={a.stage_libelle ?? undefined}
                        >
                          {a.job_offer_titre}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <span className="text-xs text-slate-400">Aucune</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <button
                    className={`text-sm ${c.favori ? 'text-amber-600' : 'text-slate-400'} hover:underline`}
                    onClick={() => toggleFavori(c)}
                  >
                    {c.favori ? '★ Favori' : '☆ Marquer'}
                  </button>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    className="text-sm font-medium text-brand-700 hover:underline"
                    onClick={() => startEdit(c)}
                  >
                    Modifier
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      {showCreate && (
        <Modal
          title="Nouveau candidat"
          onClose={() => {
            setShowCreate(false)
            setCreateOfferId('')
            setExtractFile(null)
            setExtractError(null)
          }}
          maxWidthClassName="max-w-2xl"
        >
          <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="mb-2 text-sm font-semibold text-slate-800">
              Importer un CV (optionnel)
            </div>
            {extractError && <div className="mb-2 text-sm text-red-700">{extractError}</div>}
            <div className="flex flex-wrap items-end gap-3">
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={(e) => setExtractFile(e.target.files?.[0] ?? null)}
                className="block text-sm text-slate-700"
              />
              <Button
                type="button"
                variant="secondary"
                disabled={!extractFile || extracting}
                onClick={extractCv}
              >
                {extracting ? 'Extraction…' : 'Extraire les infos'}
              </Button>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Vérifiez les champs avant de créer — l'extraction automatique peut se tromper. Le
              fichier sera enregistré comme pièce jointe du candidat à la création.
            </p>
          </div>

          <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
            <Field label="Offre (optionnel)">
              <Select value={createOfferId} onChange={(e) => setCreateOfferId(e.target.value)}>
                <option value="">Aucune — ajouter seulement à la banque de CV</option>
                {offers.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.titre}
                    {o.department_nom ? ` — ${o.department_nom}` : ''}
                  </option>
                ))}
              </Select>
            </Field>
            <p className="mt-2 text-xs text-slate-500">
              Si une offre est choisie, le candidat est ajouté directement à son pipeline de
              recrutement.
            </p>
          </div>

          <form onSubmit={create} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {renderFields(form, setForm)}
            <div className="sm:col-span-2 flex justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setShowCreate(false)
                  setCreateOfferId('')
                  setExtractFile(null)
                  setExtractError(null)
                }}
              >
                Annuler
              </Button>
              <Button type="submit">Créer</Button>
            </div>
          </form>
        </Modal>
      )}

      {editingCandidate && editForm && (
        <Modal
          title={`Modifier — ${editingCandidate.nom_complet}`}
          onClose={() => {
            setEditingCandidate(null)
            setEditForm(null)
            setAttachFile(null)
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
                  setEditingCandidate(null)
                  setEditForm(null)
                  setAttachFile(null)
                }}
              >
                Annuler
              </Button>
              <Button type="submit">Enregistrer</Button>
            </div>
          </form>

          <div className="mt-6 border-t border-slate-200 pt-4">
            <h3 className="mb-2 text-sm font-semibold text-slate-800">Pièces jointes</h3>
            <ul className="mb-3 space-y-1">
              {editingCandidate.attachments.length === 0 && (
                <li className="text-sm text-slate-400">Aucune pièce jointe.</li>
              )}
              {editingCandidate.attachments.map((a) => (
                <li key={a.id} className="flex items-center justify-between gap-2 text-sm">
                  <a
                    href={`/api/recruitment/candidates/${editingCandidate.id}/attachments/${a.id}/download`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-brand-700 hover:underline"
                  >
                    {a.type_document} — {a.nom_fichier}
                  </a>
                  <span className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">
                      {formatFileSize(a.taille_octets)}
                    </span>
                    <button
                      className="text-red-600 hover:underline"
                      onClick={() => removeAttachment(a.id)}
                    >
                      Supprimer
                    </button>
                  </span>
                </li>
              ))}
            </ul>
            <form onSubmit={uploadAttachment} className="flex flex-wrap items-end gap-3">
              <Field label="Type">
                <select
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
                  value={attachType}
                  onChange={(e) => setAttachType(e.target.value)}
                >
                  {CANDIDATE_ATTACHMENT_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Fichier">
                <input
                  type="file"
                  onChange={(e) => setAttachFile(e.target.files?.[0] ?? null)}
                  className="block text-sm text-slate-700"
                />
              </Field>
              <Button type="submit" variant="secondary" disabled={!attachFile || attachUploading}>
                {attachUploading ? 'Envoi…' : 'Téléverser'}
              </Button>
            </form>
          </div>
        </Modal>
      )}
    </div>
  )
}
