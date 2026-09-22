import { useEffect, useState, type DragEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  api,
  ApiError,
  type ApplicationComment,
  type ApplicationStage,
  type BulkCvImportResult,
  type Candidate,
  type Department,
  type Employee,
  type HirePreview,
  type HireRequest,
  type JobApplication,
  type JobOffer,
  type Position,
} from '../../lib/api'
import {
  Button,
  ErrorBanner,
  Field,
  Input,
  Modal,
  PageHeader,
  Select,
  Textarea,
} from '../../components/ui'
import { AccountCreationFields } from '../../components/AccountCreationFields'
import { employeeToFormInput, missingContractFieldLabels } from '../../lib/employee'

type ContractDraft = {
  cin: string
  date_naissance: string
  lieu_naissance: string
  adresse: string
  salaire_net: string
}

const EMPTY_CONTRACT_DRAFT: ContractDraft = {
  cin: '',
  date_naissance: '',
  lieu_naissance: '',
  adresse: '',
  salaire_net: '',
}

export function RecruitmentPipelinePage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [offers, setOffers] = useState<JobOffer[]>([])
  const [stages, setStages] = useState<ApplicationStage[]>([])
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [positions, setPositions] = useState<Position[]>([])
  const [offerId, setOfferId] = useState<number | null>(null)
  const [applications, setApplications] = useState<JobApplication[]>([])
  const [error, setError] = useState<string | null>(null)

  const [showAdd, setShowAdd] = useState(false)
  const [addCandidateId, setAddCandidateId] = useState('')
  const [addResponsable, setAddResponsable] = useState('')

  const [commentsApp, setCommentsApp] = useState<JobApplication | null>(null)
  const [comments, setComments] = useState<ApplicationComment[]>([])
  const [newComment, setNewComment] = useState('')

  const [hireApp, setHireApp] = useState<JobApplication | null>(null)
  const [hireForm, setHireForm] = useState<HireRequest | null>(null)
  const [createAccount, setCreateAccount] = useState(false)
  const [accountEmail, setAccountEmail] = useState('')
  const [accountPassword, setAccountPassword] = useState('')
  const [warning, setWarning] = useState<string | null>(null)
  const [hiredEmployee, setHiredEmployee] = useState<Employee | null>(null)
  const [contractDraft, setContractDraft] = useState<ContractDraft>(EMPTY_CONTRACT_DRAFT)
  const [savingContract, setSavingContract] = useState(false)

  const [showBulkImport, setShowBulkImport] = useState(false)
  const [bulkFiles, setBulkFiles] = useState<File[]>([])
  const [bulkImporting, setBulkImporting] = useState(false)
  const [bulkResult, setBulkResult] = useState<BulkCvImportResult | null>(null)

  useEffect(() => {
    Promise.all([
      api.get<JobOffer[]>('/recruitment/job-offers'),
      api.get<ApplicationStage[]>('/recruitment/application-stages'),
      api.get<Candidate[]>('/recruitment/candidates'),
      // Active-only: these feed the hire form, which always creates a
      // brand-new employee — a deactivated département/poste shouldn't be
      // assignable there.
      api.get<Department[]>('/departments'),
      api.get<Position[]>('/positions'),
    ])
      .then(([o, s, c, d, p]) => {
        setOffers(o)
        setStages(s)
        setCandidates(c)
        setDepartments(d)
        setPositions(p)
        const requestedOfferId = Number(searchParams.get('offre'))
        const requested = o.find((offer) => offer.id === requestedOfferId)
        if (requested) setOfferId(requested.id)
        else if (o.length > 0) setOfferId(o[0].id)
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur de chargement.'))
  }, [])

  const loadApplications = (id: number) =>
    api
      .get<JobApplication[]>(`/recruitment/applications?job_offer_id=${id}`)
      .then(setApplications)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur.'))

  useEffect(() => {
    if (offerId !== null) loadApplications(offerId)
  }, [offerId])

  const firstStageId = stages[0]?.id

  const addToPipeline = async () => {
    if (!offerId || !addCandidateId) return
    setError(null)
    try {
      await api.post<JobApplication>('/recruitment/applications', {
        candidate_id: Number(addCandidateId),
        job_offer_id: offerId,
        responsable: addResponsable || null,
        stage_id: firstStageId ?? null,
      })
      setShowAdd(false)
      setAddCandidateId('')
      setAddResponsable('')
      await loadApplications(offerId)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const openHireModal = async (application: JobApplication) => {
    try {
      const preview = await api.get<HirePreview>(
        `/recruitment/applications/${application.id}/hire-preview`,
      )
      setHireApp(application)
      setHireForm({
        prenom: preview.prenom_suggere,
        nom: preview.nom_suggere,
        telephone: preview.telephone,
        email: preview.email,
        ville: preview.ville,
        department_id: preview.department_id,
        position_id: null,
        categorie_professionnelle: null,
        date_embauche: null,
        date_fin_periode_essai: null,
      })
      setCreateAccount(false)
      setAccountEmail(preview.email ?? '')
      setAccountPassword('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const closeHireModal = () => {
    setHireApp(null)
    setHireForm(null)
    setCreateAccount(false)
    setAccountEmail('')
    setAccountPassword('')
  }

  const moveStage = async (application: JobApplication, stageId: number) => {
    setError(null)
    try {
      await api.put(`/recruitment/applications/${application.id}/stage`, { stage_id: stageId })
      if (offerId) await loadApplications(offerId)

      const targetStage = stages.find((s) => s.id === stageId)
      const alreadyHired = candidates.find((c) => c.id === application.candidate_id)?.employee_id
      if (targetStage?.is_hire_stage && !alreadyHired) {
        await openHireModal(application)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const withdrawApplication = async (application: JobApplication) => {
    if (!window.confirm(`Retirer ${application.candidate_nom} de ce pipeline ?`)) return
    setError(null)
    try {
      await api.delete(`/recruitment/applications/${application.id}`)
      if (offerId) await loadApplications(offerId)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const openComments = async (application: JobApplication) => {
    setCommentsApp(application)
    try {
      const list = await api.get<ApplicationComment[]>(
        `/recruitment/applications/${application.id}/comments`,
      )
      setComments(list)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const addComment = async () => {
    if (!commentsApp || !newComment.trim()) return
    try {
      await api.post(`/recruitment/applications/${commentsApp.id}/comments`, { texte: newComment })
      setNewComment('')
      const list = await api.get<ApplicationComment[]>(
        `/recruitment/applications/${commentsApp.id}/comments`,
      )
      setComments(list)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const confirmHire = async () => {
    if (!hireApp || !hireForm) return
    setError(null)
    setWarning(null)
    try {
      const employee = await api.post<Employee>(
        `/recruitment/applications/${hireApp.id}/hire`,
        hireForm,
      )
      if (createAccount) {
        try {
          await api.post('/users', {
            email: accountEmail,
            password: accountPassword,
            role: 'employee',
            employee_id: employee.id,
          })
        } catch (err) {
          setWarning(
            `${employee.full_name} a été embauché(e), mais le compte de connexion n'a pas pu être créé : ${
              err instanceof ApiError ? err.message : 'erreur inconnue'
            }`,
          )
        }
      }
      closeHireModal()
      setHiredEmployee(employee)
      setContractDraft(EMPTY_CONTRACT_DRAFT)
      if (offerId) await loadApplications(offerId)
      const refreshed = await api.get<Candidate[]>('/recruitment/candidates')
      setCandidates(refreshed)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const saveContractFieldsAndDownload = async () => {
    if (!hiredEmployee) return
    setError(null)
    setSavingContract(true)
    try {
      const updated = await api.put<Employee>(`/employees/${hiredEmployee.id}`, {
        ...employeeToFormInput(hiredEmployee),
        cin: contractDraft.cin || null,
        date_naissance: contractDraft.date_naissance || null,
        lieu_naissance: contractDraft.lieu_naissance || null,
        adresse: contractDraft.adresse || null,
        salaire_net: contractDraft.salaire_net || null,
      })
      setHiredEmployee(updated)
      window.open(`/api/employees/${updated.id}/contrat-cdi`, '_blank')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    } finally {
      setSavingContract(false)
    }
  }

  const closeBulkImport = () => {
    setShowBulkImport(false)
    setBulkFiles([])
    setBulkResult(null)
  }

  const runBulkImport = async () => {
    if (!offerId || bulkFiles.length === 0) return
    setError(null)
    setBulkImporting(true)
    try {
      const formData = new FormData()
      bulkFiles.forEach((file) => formData.append('files', file))
      const result = await api.upload<BulkCvImportResult>(
        `/recruitment/job-offers/${offerId}/bulk-import-cvs`,
        formData,
      )
      setBulkResult(result)
      setBulkFiles([])
      await loadApplications(offerId)
      const refreshed = await api.get<Candidate[]>('/recruitment/candidates')
      setCandidates(refreshed)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    } finally {
      setBulkImporting(false)
    }
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <PageHeader
          title="Pipeline de recrutement"
          subtitle="Un tableau par offre. Glissez une candidature vers une autre étape, ou utilisez le menu de la carte."
        />
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setShowBulkImport(true)} disabled={!offerId}>
            Importer des CV
          </Button>
          <Button onClick={() => setShowAdd(true)} disabled={!offerId}>
            Ajouter une candidature
          </Button>
        </div>
      </div>
      <ErrorBanner message={error} />
      {warning && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {warning}
        </div>
      )}

      <div className="mb-4 max-w-xs">
        <Field label="Offre">
          <Select
            value={offerId ?? ''}
            onChange={(e) => setOfferId(e.target.value ? Number(e.target.value) : null)}
          >
            {offers.map((o) => (
              <option key={o.id} value={o.id}>
                {o.titre} ({o.candidatures_count})
              </option>
            ))}
          </Select>
        </Field>
      </div>

      <div className="flex gap-4 overflow-x-auto pb-2">
        {stages.map((stage) => (
          <div
            key={stage.id}
            className="w-64 flex-none rounded-xl border border-slate-200 bg-slate-50 p-3"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              const appId = Number(e.dataTransfer.getData('text/plain'))
              const application = applications.find((a) => a.id === appId)
              if (application) moveStage(application, stage.id)
            }}
          >
            <div
              className="mb-2 flex items-center justify-between gap-2 text-xs font-semibold uppercase text-slate-500"
              style={{ color: stage.couleur }}
            >
              <span>{stage.libelle}</span>
              <span>{applications.filter((a) => a.stage_id === stage.id).length}</span>
            </div>
            <div className="space-y-2">
              {applications
                .filter((a) => a.stage_id === stage.id)
                .map((a) => {
                  const employeeId = candidates.find((c) => c.id === a.candidate_id)?.employee_id
                  return (
                    <div
                      key={a.id}
                      className="cursor-move rounded-xl border border-slate-200 bg-white p-3 shadow-sm"
                      draggable
                      onDragStart={(e: DragEvent) =>
                        e.dataTransfer.setData('text/plain', String(a.id))
                      }
                    >
                      <div className="mb-1 flex items-start justify-between gap-2">
                        <button
                          className="text-left text-sm font-semibold text-slate-800 hover:underline"
                          onClick={() => openComments(a)}
                        >
                          {a.candidate_nom}
                        </button>
                        <button
                          className="text-xs text-slate-400 hover:text-red-600 hover:underline"
                          onClick={() => withdrawApplication(a)}
                          title="Retirer du pipeline"
                        >
                          Retirer
                        </button>
                      </div>
                      <div className="text-xs text-slate-500">{a.candidate_ville ?? '—'}</div>
                      {a.responsable && (
                        <div className="mt-1 text-xs text-slate-400">{a.responsable}</div>
                      )}
                      {employeeId != null && (
                        <button
                          className="mt-1 inline-block rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800 hover:bg-emerald-200"
                          onClick={() => navigate(`/hr/collaborateurs/${employeeId}`)}
                        >
                          Déjà embauché — voir la fiche →
                        </button>
                      )}
                      <Select
                        className="mt-2 py-1 text-xs"
                        value={stage.id}
                        onChange={(e) => moveStage(a, Number(e.target.value))}
                      >
                        {stages.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.libelle}
                          </option>
                        ))}
                      </Select>
                      {stage.is_hire_stage && employeeId == null && (
                        <button
                          className="mt-2 block w-full rounded-lg bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
                          onClick={() => openHireModal(a)}
                        >
                          Proposer l'embauche
                        </button>
                      )}
                    </div>
                  )
                })}
            </div>
          </div>
        ))}
      </div>

      {showAdd && (
        <Modal title="Ajouter une candidature" onClose={() => setShowAdd(false)}>
          <Field label="Candidat" className="mb-3">
            <Select value={addCandidateId} onChange={(e) => setAddCandidateId(e.target.value)}>
              <option value="">—</option>
              {candidates.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nom_complet}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Responsable" className="mb-4">
            <Input value={addResponsable} onChange={(e) => setAddResponsable(e.target.value)} />
          </Field>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setShowAdd(false)}>
              Annuler
            </Button>
            <Button onClick={addToPipeline} disabled={!addCandidateId}>
              Ajouter
            </Button>
          </div>
        </Modal>
      )}

      {commentsApp && (
        <Modal
          title={`Commentaires — ${commentsApp.candidate_nom}`}
          onClose={() => setCommentsApp(null)}
        >
          <div className="mb-4 max-h-64 space-y-2 overflow-y-auto">
            {comments.length === 0 && <p className="text-sm text-slate-400">Aucun commentaire.</p>}
            {comments.map((c) => (
              <div key={c.id} className="rounded-lg bg-slate-50 p-2 text-sm">
                <div className="text-slate-700">{c.texte}</div>
                <div className="mt-1 text-xs text-slate-400">
                  {c.auteur_email} · {new Date(c.created_at).toLocaleString('fr-FR')}
                </div>
              </div>
            ))}
          </div>
          <Textarea
            rows={2}
            placeholder="Ajouter un commentaire…"
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
          />
          <div className="mt-2 flex justify-end">
            <Button onClick={addComment} disabled={!newComment.trim()}>
              Envoyer
            </Button>
          </div>
        </Modal>
      )}

      {hireApp && hireForm && (
        <Modal title={`Proposer l'embauche — ${hireApp.candidate_nom}`} onClose={closeHireModal}>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Prénom">
              <Input
                value={hireForm.prenom}
                onChange={(e) => setHireForm({ ...hireForm, prenom: e.target.value })}
              />
            </Field>
            <Field label="Nom">
              <Input
                value={hireForm.nom}
                onChange={(e) => setHireForm({ ...hireForm, nom: e.target.value })}
              />
            </Field>
            <Field label="Département">
              <Select
                value={hireForm.department_id ?? ''}
                onChange={(e) =>
                  setHireForm({
                    ...hireForm,
                    department_id: e.target.value ? Number(e.target.value) : null,
                  })
                }
              >
                <option value="">—</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.nom}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Poste">
              <Select
                value={hireForm.position_id ?? ''}
                onChange={(e) =>
                  setHireForm({
                    ...hireForm,
                    position_id: e.target.value ? Number(e.target.value) : null,
                  })
                }
              >
                <option value="">—</option>
                {positions.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.intitule}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Catégorie">
              <Select
                value={hireForm.categorie_professionnelle ?? ''}
                onChange={(e) =>
                  setHireForm({ ...hireForm, categorie_professionnelle: e.target.value || null })
                }
              >
                <option value="">—</option>
                <option value="cadre">Cadre</option>
                <option value="salarie">Salarié</option>
              </Select>
            </Field>
            <Field label="Date d'embauche">
              <Input
                type="date"
                value={hireForm.date_embauche ?? ''}
                onChange={(e) =>
                  setHireForm({ ...hireForm, date_embauche: e.target.value || null })
                }
              />
            </Field>
            <Field label="Fin de période d'essai">
              <Input
                type="date"
                value={hireForm.date_fin_periode_essai ?? ''}
                onChange={(e) =>
                  setHireForm({ ...hireForm, date_fin_periode_essai: e.target.value || null })
                }
              />
            </Field>
          </div>
          <div className="mt-4">
            <AccountCreationFields
              enabled={createAccount}
              onToggle={setCreateAccount}
              email={accountEmail}
              onEmailChange={setAccountEmail}
              password={accountPassword}
              onPasswordChange={setAccountPassword}
            />
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="secondary" onClick={closeHireModal}>
              Plus tard
            </Button>
            <Button onClick={confirmHire}>Confirmer l'embauche</Button>
          </div>
        </Modal>
      )}

      {hiredEmployee && (
        <Modal title="Embauche confirmée" onClose={() => setHiredEmployee(null)}>
          {missingContractFieldLabels(hiredEmployee).length > 0 ? (
            <>
              <p className="mb-3 text-sm text-slate-600">
                {hiredEmployee.full_name} a été embauché(e). Avant de télécharger le contrat CDI,
                complétez les champs qu'il lui manque encore :
              </p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Field label="CIN">
                  <Input
                    value={contractDraft.cin}
                    onChange={(e) => setContractDraft({ ...contractDraft, cin: e.target.value })}
                  />
                </Field>
                <Field label="Date de naissance">
                  <Input
                    type="date"
                    value={contractDraft.date_naissance}
                    onChange={(e) =>
                      setContractDraft({ ...contractDraft, date_naissance: e.target.value })
                    }
                  />
                </Field>
                <Field label="Lieu de naissance">
                  <Input
                    value={contractDraft.lieu_naissance}
                    onChange={(e) =>
                      setContractDraft({ ...contractDraft, lieu_naissance: e.target.value })
                    }
                  />
                </Field>
                <Field label="Adresse">
                  <Input
                    value={contractDraft.adresse}
                    onChange={(e) =>
                      setContractDraft({ ...contractDraft, adresse: e.target.value })
                    }
                  />
                </Field>
                <Field label="Salaire net">
                  <Input
                    type="number"
                    step="0.01"
                    value={contractDraft.salaire_net}
                    onChange={(e) =>
                      setContractDraft({ ...contractDraft, salaire_net: e.target.value })
                    }
                  />
                </Field>
              </div>
              <div className="mt-4 flex justify-end gap-2">
                <Button variant="secondary" onClick={() => setHiredEmployee(null)}>
                  Fermer
                </Button>
                <Button
                  onClick={saveContractFieldsAndDownload}
                  disabled={
                    savingContract ||
                    !contractDraft.cin ||
                    !contractDraft.date_naissance ||
                    !contractDraft.lieu_naissance ||
                    !contractDraft.adresse ||
                    !contractDraft.salaire_net
                  }
                >
                  {savingContract ? 'Enregistrement…' : 'Enregistrer et télécharger le contrat'}
                </Button>
              </div>
            </>
          ) : (
            <>
              <p className="mb-4 text-sm text-slate-600">
                {hiredEmployee.full_name} a été embauché(e). Le contrat CDI peut être généré dès
                maintenant à partir du modèle de l'entreprise.
              </p>
              <div className="flex justify-end gap-2">
                <Button variant="secondary" onClick={() => setHiredEmployee(null)}>
                  Fermer
                </Button>
                <a
                  href={`/api/employees/${hiredEmployee.id}/contrat-cdi`}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-lg bg-accent-600 px-3.5 py-2 text-sm font-semibold text-white shadow-sm shadow-accent-600/20 hover:bg-accent-700"
                >
                  Télécharger le contrat CDI
                </a>
              </div>
            </>
          )}
        </Modal>
      )}

      {showBulkImport && (
        <Modal
          title={`Importer des CV — ${offers.find((o) => o.id === offerId)?.titre ?? ''}`}
          onClose={closeBulkImport}
          maxWidthClassName="max-w-2xl"
        >
          <p className="mb-3 text-sm text-slate-600">
            Chaque CV est analysé, ajouté à la banque de CV (ou rattaché au candidat existant s'il y
            figure déjà) et placé directement dans le pipeline de cette offre.
          </p>
          <input
            type="file"
            multiple
            accept=".pdf,.docx,.txt"
            onChange={(e) => setBulkFiles(Array.from(e.target.files ?? []))}
            className="block text-sm text-slate-700"
          />
          {bulkFiles.length > 0 && (
            <p className="mt-2 text-xs text-slate-500">
              {bulkFiles.length} fichier{bulkFiles.length > 1 ? 's' : ''} sélectionné
              {bulkFiles.length > 1 ? 's' : ''}.
            </p>
          )}

          {bulkResult && (
            <div className="mt-4 max-h-72 space-y-1.5 overflow-y-auto border-t border-slate-100 pt-3">
              {bulkResult.items.map((item, i) => (
                <div
                  key={i}
                  className={`rounded-lg border px-3 py-2 text-sm ${
                    item.status === 'error'
                      ? 'border-red-200 bg-red-50 text-red-800'
                      : item.status === 'already_applied'
                        ? 'border-slate-200 bg-slate-50 text-slate-600'
                        : 'border-emerald-200 bg-emerald-50 text-emerald-800'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">
                      {item.candidate?.nom_complet ?? item.filename}
                    </span>
                    <span className="text-xs">
                      {item.status === 'created' && 'Ajouté au pipeline'}
                      {item.status === 'linked_existing' &&
                        'Candidat existant — ajouté au pipeline'}
                      {item.status === 'already_applied' && 'Déjà dans ce pipeline'}
                      {item.status === 'error' && 'Échec'}
                    </span>
                  </div>
                  {item.message && <p className="mt-0.5 text-xs opacity-80">{item.message}</p>}
                </div>
              ))}
            </div>
          )}

          <div className="mt-5 flex justify-end gap-2">
            <Button variant="secondary" onClick={closeBulkImport}>
              Fermer
            </Button>
            <Button onClick={runBulkImport} disabled={bulkFiles.length === 0 || bulkImporting}>
              {bulkImporting ? 'Importation…' : 'Importer'}
            </Button>
          </div>
        </Modal>
      )}
    </div>
  )
}
