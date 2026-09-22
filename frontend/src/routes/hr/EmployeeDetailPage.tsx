import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  api,
  ApiError,
  type Department,
  type Employee,
  type EmployeeFormInput,
  type EmployeeLite,
  type EmployeeStatus,
  type LeaveBalance,
  type LeaveRequest,
  type MonthlySummary,
  type Position,
  type ProbationEvaluationCreate,
} from '../../lib/api'
import { EMPLOYEE_DOCUMENT_TYPES, EMPLOYEE_EQUIPMENT_TYPES } from '../../lib/documentTypes'
import { employeeToFormInput as toFormInput, missingContractFieldLabels } from '../../lib/employee'
import {
  Button,
  Card,
  ErrorBanner,
  Field,
  FormSection,
  Input,
  Modal,
  PageHeader,
  Select,
  StatusBadge,
  Table,
  Textarea,
} from '../../components/ui'
import { EmployeeForm } from '../../components/EmployeeForm'

type TabKey =
  'infos' | 'contacts' | 'periode-essai' | 'documents' | 'equipement' | 'conges' | 'presence'

const currentYear = new Date().getFullYear()
const currentMonth = new Date().getMonth() + 1

function InfoItem({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs uppercase text-slate-400">{label}</dt>
      <dd className="text-sm text-slate-800">{value ?? '—'}</dd>
    </div>
  )
}

const EMPTY_CONTACT = { nom: '', lien: '', telephone: '' }
const EMPTY_EVALUATION: ProbationEvaluationCreate = {
  date_evaluation: new Date().toISOString().slice(0, 10),
  avis_rh: '',
  evaluateur_rh: '',
  avis_dg: '',
  evaluateur_dg: '',
  decision: '',
  nouvelle_date_fin: '',
}

export function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const employeeId = Number(id)

  const [employee, setEmployee] = useState<Employee | null>(null)
  const [departments, setDepartments] = useState<Department[]>([])
  const [positions, setPositions] = useState<Position[]>([])
  const [statuses, setStatuses] = useState<EmployeeStatus[]>([])
  const [managers, setManagers] = useState<EmployeeLite[]>([])
  const [leaveBalances, setLeaveBalances] = useState<LeaveBalance[]>([])
  const [leaveRequests, setLeaveRequests] = useState<LeaveRequest[]>([])
  const [monthlySummary, setMonthlySummary] = useState<MonthlySummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<TabKey>('infos')

  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState<EmployeeFormInput | null>(null)
  const [contactForm, setContactForm] = useState(EMPTY_CONTACT)
  const [evalForm, setEvalForm] = useState<ProbationEvaluationCreate>(EMPTY_EVALUATION)
  const [showDeactivate, setShowDeactivate] = useState(false)
  const [docType, setDocType] = useState(EMPLOYEE_DOCUMENT_TYPES[0])
  const [docExpiration, setDocExpiration] = useState('')
  const [docFile, setDocFile] = useState<File | null>(null)
  const [docUploading, setDocUploading] = useState(false)
  const [customEquipment, setCustomEquipment] = useState('')
  const [contractWarning, setContractWarning] = useState<string | null>(null)
  const [pendingContractDownload, setPendingContractDownload] = useState(false)

  const load = async () => {
    const emp = await api.get<Employee>(`/employees/${employeeId}`)
    setEmployee(emp)
  }

  useEffect(() => {
    Promise.all([
      load(),
      // include_inactive: an employee's current département/poste must still
      // render as selected even if it's since been deactivated — otherwise
      // the dropdown looks blank and editing/saving would silently reassign
      // them.
      api.get<Department[]>('/departments?include_inactive=true').then(setDepartments),
      api.get<Position[]>('/positions?include_inactive=true').then(setPositions),
      api.get<EmployeeStatus[]>('/employee-statuses').then(setStatuses),
      api.get<EmployeeLite[]>('/employees').then(setManagers),
      api
        .get<LeaveBalance[]>(`/leave-balances?annee=${currentYear}&employee_id=${employeeId}`)
        .then(setLeaveBalances),
      api.get<LeaveRequest[]>(`/leave-requests?employee_id=${employeeId}`).then(setLeaveRequests),
      api
        .get<MonthlySummary>(
          `/attendance/etat/resume?employee_id=${employeeId}&mois=${currentMonth}&annee=${currentYear}`,
        )
        .then(setMonthlySummary),
    ]).catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur de chargement.'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [employeeId])

  const startEdit = () => {
    if (!employee) return
    setForm(toFormInput(employee))
    setEditing(true)
  }

  const saveEdit = async (e: FormEvent) => {
    e.preventDefault()
    if (!form) return
    setError(null)
    try {
      await api.put(`/employees/${employeeId}`, form)
      setEditing(false)
      await load()
      if (pendingContractDownload) {
        setPendingContractDownload(false)
        setContractWarning(null)
        window.open(`/api/employees/${employeeId}/contrat-cdi`, '_blank')
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const downloadContract = () => {
    if (!employee) return
    const missing = missingContractFieldLabels(employee)
    if (missing.length > 0) {
      setContractWarning(
        `Complétez ces champs avant de télécharger le contrat CDI : ${missing.join(', ')}.`,
      )
      setTab('infos')
      startEdit()
      setPendingContractDownload(true)
      return
    }
    window.open(`/api/employees/${employeeId}/contrat-cdi`, '_blank')
  }

  const addContact = async (e: FormEvent) => {
    e.preventDefault()
    if (!contactForm.nom.trim() || !contactForm.telephone.trim()) return
    setError(null)
    try {
      await api.post(`/employees/${employeeId}/contacts-urgence`, {
        nom: contactForm.nom,
        lien: contactForm.lien || null,
        telephone: contactForm.telephone,
      })
      setContactForm(EMPTY_CONTACT)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const removeContact = async (contactId: number) => {
    setError(null)
    try {
      await api.delete(`/employees/${employeeId}/contacts-urgence/${contactId}`)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const addEvaluation = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      await api.post(`/employees/${employeeId}/periode-essai/evaluations`, {
        ...evalForm,
        avis_rh: evalForm.avis_rh || null,
        evaluateur_rh: evalForm.evaluateur_rh || null,
        avis_dg: evalForm.avis_dg || null,
        evaluateur_dg: evalForm.evaluateur_dg || null,
        decision: evalForm.decision || null,
        nouvelle_date_fin: evalForm.nouvelle_date_fin || null,
      })
      setEvalForm(EMPTY_EVALUATION)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const uploadDocument = async (e: FormEvent) => {
    e.preventDefault()
    if (!docFile) return
    setError(null)
    setDocUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', docFile)
      const params = new URLSearchParams({ type_document: docType })
      if (docExpiration) params.set('date_expiration', docExpiration)
      await api.upload(`/employees/${employeeId}/documents?${params.toString()}`, formData)
      setDocFile(null)
      setDocExpiration('')
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    } finally {
      setDocUploading(false)
    }
  }

  const removeDocument = async (documentId: number) => {
    setError(null)
    try {
      await api.delete(`/employees/${employeeId}/documents/${documentId}`)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const addEquipment = async (libelle: string) => {
    if (!libelle.trim()) return
    setError(null)
    try {
      await api.post(`/employees/${employeeId}/equipement`, { libelle })
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const removeEquipment = async (itemId: number) => {
    setError(null)
    try {
      await api.delete(`/employees/${employeeId}/equipement/${itemId}`)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const deactivate = async () => {
    setError(null)
    try {
      await api.delete(`/employees/${employeeId}`)
      setShowDeactivate(false)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  if (!employee) {
    return (
      <div>
        <ErrorBanner message={error} />
        {!error && <p className="text-sm text-slate-400">Chargement…</p>}
      </div>
    )
  }

  return (
    <div>
      <button
        className="mb-3 text-sm text-slate-500 hover:underline"
        onClick={() => navigate('/hr/collaborateurs')}
      >
        ← Retour à la liste
      </button>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <PageHeader
          title={employee.full_name}
          subtitle={[employee.position_intitule, employee.department_nom]
            .filter(Boolean)
            .join(' — ')}
        />
        <div className="flex gap-2">
          <a
            href={`/api/employees/${employeeId}/fiche`}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg bg-slate-100 px-3.5 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-200"
          >
            Télécharger la fiche
          </a>
          <Button variant="secondary" onClick={downloadContract}>
            Télécharger le contrat CDI
          </Button>
          <Button variant="danger" onClick={() => setShowDeactivate(true)}>
            Désactiver
          </Button>
        </div>
      </div>
      <ErrorBanner message={error} />
      {contractWarning && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          {contractWarning}
        </div>
      )}

      <div className="mb-4 flex gap-1 border-b border-slate-200">
        {(
          [
            ['infos', 'Infos'],
            ['contacts', "Contacts d'urgence"],
            ['periode-essai', "Période d'essai"],
            ['documents', 'Documents'],
            ['equipement', 'Équipement'],
            ['conges', 'Congés'],
            ['presence', 'Présence'],
          ] as [TabKey, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`border-b-2 px-3 py-2 text-sm font-medium ${
              tab === key
                ? 'border-brand-700 text-brand-700'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'infos' && (
        <Card className="p-5">
          {!editing ? (
            <div className="space-y-5">
              <FormSection title="Identité">
                <InfoItem label="Matricule" value={employee.matricule} />
                <InfoItem label="CIN" value={employee.cin} />
                <InfoItem label="Date de naissance" value={employee.date_naissance} />
                <InfoItem label="Lieu de naissance" value={employee.lieu_naissance} />
              </FormSection>

              <FormSection title="Contact">
                <InfoItem label="Email" value={employee.email} />
                <InfoItem label="Téléphone" value={employee.telephone} />
                <InfoItem label="Ville" value={employee.ville} />
                <InfoItem label="Adresse" value={employee.adresse} />
              </FormSection>

              <FormSection title="Poste & organisation">
                <InfoItem label="Département" value={employee.department_nom} />
                <InfoItem label="Poste" value={employee.position_intitule} />
                <InfoItem label="Statut" value={employee.status_libelle} />
                <InfoItem label="Responsable hiérarchique" value={employee.manager_nom} />
                <InfoItem label="Équipe" value={employee.equipe} />
              </FormSection>

              <FormSection title="Contrat & rémunération">
                <InfoItem label="Type de contrat" value={employee.type_contrat} />
                <InfoItem label="Catégorie" value={employee.categorie_professionnelle} />
                <InfoItem label="CNSS" value={employee.cnss} />
                <InfoItem label="Salaire de base" value={employee.salaire_base} />
                <InfoItem label="Salaire net" value={employee.salaire_net} />
                <InfoItem label="Date d'embauche" value={employee.date_embauche} />
                <InfoItem label="Fin de période d'essai" value={employee.date_fin_periode_essai} />
              </FormSection>

              {(employee.date_sortie || employee.motif_sortie) && (
                <FormSection title="Fin de contrat">
                  <InfoItem label="Date de sortie" value={employee.date_sortie} />
                  <InfoItem label="Motif de sortie" value={employee.motif_sortie} />
                </FormSection>
              )}

              {employee.notes && (
                <FormSection title="Notes">
                  <dd className="whitespace-pre-wrap text-sm text-slate-800 sm:col-span-2 lg:col-span-3">
                    {employee.notes}
                  </dd>
                </FormSection>
              )}

              <div>
                <Button onClick={startEdit}>Modifier</Button>
              </div>
            </div>
          ) : (
            form && (
              <form onSubmit={saveEdit}>
                <EmployeeForm
                  value={form}
                  onChange={setForm}
                  departments={departments}
                  positions={positions}
                  statuses={statuses}
                  managers={managers.filter((m) => m.id !== employee.id)}
                />
                <div className="mt-5 flex justify-end gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      setEditing(false)
                      setPendingContractDownload(false)
                      setContractWarning(null)
                    }}
                  >
                    Annuler
                  </Button>
                  <Button type="submit">Enregistrer</Button>
                </div>
              </form>
            )
          )}
        </Card>
      )}

      {tab === 'contacts' && (
        <Card className="p-5">
          <Table>
            <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Nom</th>
                <th className="px-3 py-2">Lien</th>
                <th className="px-3 py-2">Téléphone</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {employee.emergency_contacts.length === 0 && (
                <tr>
                  <td className="px-3 py-4 text-center text-slate-400" colSpan={4}>
                    Aucun contact enregistré.
                  </td>
                </tr>
              )}
              {employee.emergency_contacts.map((c) => (
                <tr key={c.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-3 py-2">{c.nom}</td>
                  <td className="px-3 py-2 text-slate-600">{c.lien ?? '—'}</td>
                  <td className="px-3 py-2 text-slate-600">{c.telephone}</td>
                  <td className="px-3 py-2 text-right">
                    <button
                      className="text-sm text-red-600 hover:underline"
                      onClick={() => removeContact(c.id)}
                    >
                      Supprimer
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>

          <form onSubmit={addContact} className="mt-4 flex flex-wrap items-end gap-3">
            <Field label="Nom">
              <Input
                value={contactForm.nom}
                onChange={(e) => setContactForm({ ...contactForm, nom: e.target.value })}
              />
            </Field>
            <Field label="Lien">
              <Input
                placeholder="Conjoint, parent, ..."
                value={contactForm.lien}
                onChange={(e) => setContactForm({ ...contactForm, lien: e.target.value })}
              />
            </Field>
            <Field label="Téléphone">
              <Input
                value={contactForm.telephone}
                onChange={(e) => setContactForm({ ...contactForm, telephone: e.target.value })}
              />
            </Field>
            <Button type="submit" variant="secondary">
              Ajouter
            </Button>
          </form>
        </Card>
      )}

      {tab === 'periode-essai' && (
        <Card className="p-5">
          <p className="mb-4 text-sm text-slate-600">
            Fin de période d'essai actuelle :{' '}
            <strong>{employee.date_fin_periode_essai ?? '—'}</strong>
          </p>

          <Table>
            <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Date</th>
                <th className="px-3 py-2">Avis RH</th>
                <th className="px-3 py-2">Avis DG</th>
                <th className="px-3 py-2">Décision</th>
              </tr>
            </thead>
            <tbody>
              {employee.probation_evaluations.length === 0 && (
                <tr>
                  <td className="px-3 py-4 text-center text-slate-400" colSpan={4}>
                    Aucune évaluation enregistrée.
                  </td>
                </tr>
              )}
              {employee.probation_evaluations.map((ev) => (
                <tr key={ev.id} className="border-b border-slate-100 last:border-0 align-top">
                  <td className="px-3 py-2 text-slate-600">{ev.date_evaluation}</td>
                  <td className="px-3 py-2 text-slate-600">
                    {ev.avis_rh ?? '—'}
                    {ev.evaluateur_rh && (
                      <div className="text-xs text-slate-400">{ev.evaluateur_rh}</div>
                    )}
                  </td>
                  <td className="px-3 py-2 text-slate-600">
                    {ev.avis_dg ?? '—'}
                    {ev.evaluateur_dg && (
                      <div className="text-xs text-slate-400">{ev.evaluateur_dg}</div>
                    )}
                  </td>
                  <td className="px-3 py-2 font-medium text-slate-800">{ev.decision ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </Table>

          <form onSubmit={addEvaluation} className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Date de l'évaluation">
              <Input
                type="date"
                required
                value={evalForm.date_evaluation}
                onChange={(e) => setEvalForm({ ...evalForm, date_evaluation: e.target.value })}
              />
            </Field>
            <Field label="Décision">
              <Select
                value={evalForm.decision ?? ''}
                onChange={(e) => setEvalForm({ ...evalForm, decision: e.target.value })}
              >
                <option value="">—</option>
                <option value="Confirmé">Confirmé</option>
                <option value="Prolongé">Prolongé</option>
                <option value="Rompu">Rompu</option>
              </Select>
            </Field>
            <Field label="Avis RH">
              <Textarea
                rows={2}
                value={evalForm.avis_rh ?? ''}
                onChange={(e) => setEvalForm({ ...evalForm, avis_rh: e.target.value })}
              />
            </Field>
            <Field label="Évaluateur RH">
              <Input
                value={evalForm.evaluateur_rh ?? ''}
                onChange={(e) => setEvalForm({ ...evalForm, evaluateur_rh: e.target.value })}
              />
            </Field>
            <Field label="Avis DG (rapporté)">
              <Textarea
                rows={2}
                value={evalForm.avis_dg ?? ''}
                onChange={(e) => setEvalForm({ ...evalForm, avis_dg: e.target.value })}
              />
            </Field>
            <Field label="Évaluateur DG">
              <Input
                value={evalForm.evaluateur_dg ?? ''}
                onChange={(e) => setEvalForm({ ...evalForm, evaluateur_dg: e.target.value })}
              />
            </Field>
            {evalForm.decision === 'Prolongé' && (
              <Field label="Nouvelle date de fin">
                <Input
                  type="date"
                  value={evalForm.nouvelle_date_fin ?? ''}
                  onChange={(e) => setEvalForm({ ...evalForm, nouvelle_date_fin: e.target.value })}
                />
              </Field>
            )}
            <div className="sm:col-span-2">
              <Button type="submit">Enregistrer l'évaluation</Button>
            </div>
          </form>
        </Card>
      )}

      {tab === 'documents' && (
        <Card className="p-5">
          <Table>
            <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Fichier</th>
                <th className="px-3 py-2">Expiration</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {employee.documents.length === 0 && (
                <tr>
                  <td className="px-3 py-4 text-center text-slate-400" colSpan={4}>
                    Aucun document.
                  </td>
                </tr>
              )}
              {employee.documents.map((d) => (
                <tr key={d.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-3 py-2">{d.type_document}</td>
                  <td className="px-3 py-2">
                    <a
                      href={`/api/employees/${employeeId}/documents/${d.id}/download`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-brand-700 hover:underline"
                    >
                      {d.nom_fichier}
                    </a>
                  </td>
                  <td className="px-3 py-2 text-slate-600">{d.date_expiration ?? '—'}</td>
                  <td className="px-3 py-2 text-right">
                    <button
                      className="text-sm text-red-600 hover:underline"
                      onClick={() => removeDocument(d.id)}
                    >
                      Supprimer
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>

          <form onSubmit={uploadDocument} className="mt-4 flex flex-wrap items-end gap-3">
            <Field label="Type">
              <Select value={docType} onChange={(e) => setDocType(e.target.value)}>
                {EMPLOYEE_DOCUMENT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Date d'expiration (optionnelle)">
              <Input
                type="date"
                value={docExpiration}
                onChange={(e) => setDocExpiration(e.target.value)}
              />
            </Field>
            <Field label="Fichier">
              <input
                type="file"
                onChange={(e) => setDocFile(e.target.files?.[0] ?? null)}
                className="block text-sm text-slate-700"
              />
            </Field>
            <Button type="submit" variant="secondary" disabled={!docFile || docUploading}>
              {docUploading ? 'Envoi…' : 'Téléverser'}
            </Button>
          </form>
        </Card>
      )}

      {tab === 'equipement' && (
        <Card className="p-5">
          <p className="mb-4 text-sm text-slate-600">
            Ce que le collaborateur a actuellement en sa possession. Cocher ajoute l'élément,
            décocher le retire — utile pour vérifier ce qui doit être restitué en fin de contrat.
          </p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {EMPLOYEE_EQUIPMENT_TYPES.map((type) => {
              const existing = employee.equipements.find((e) => e.libelle === type)
              return (
                <label key={type} className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={Boolean(existing)}
                    onChange={() => (existing ? removeEquipment(existing.id) : addEquipment(type))}
                  />
                  {type}
                </label>
              )
            })}
          </div>

          {employee.equipements.filter((e) => !EMPLOYEE_EQUIPMENT_TYPES.includes(e.libelle))
            .length > 0 && (
            <div className="mt-5">
              <div className="mb-2 text-xs uppercase text-slate-400">Autres éléments</div>
              <div className="flex flex-wrap gap-2">
                {employee.equipements
                  .filter((e) => !EMPLOYEE_EQUIPMENT_TYPES.includes(e.libelle))
                  .map((item) => (
                    <span
                      key={item.id}
                      className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700"
                    >
                      {item.libelle}
                      <button
                        className="text-slate-400 hover:text-red-600"
                        onClick={() => removeEquipment(item.id)}
                        aria-label={`Retirer ${item.libelle}`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
              </div>
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault()
              addEquipment(customEquipment)
              setCustomEquipment('')
            }}
            className="mt-5 flex flex-wrap items-end gap-3"
          >
            <Field label="Ajouter un élément hors liste">
              <Input
                placeholder="Ex. Ordinateur de bureau"
                value={customEquipment}
                onChange={(e) => setCustomEquipment(e.target.value)}
              />
            </Field>
            <Button type="submit" variant="secondary" disabled={!customEquipment.trim()}>
              Ajouter
            </Button>
          </form>
        </Card>
      )}

      {tab === 'conges' && (
        <Card className="p-5">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-slate-700">Solde {currentYear}</h3>
            <button
              className="text-sm font-medium text-brand-700 hover:underline"
              onClick={() => navigate(`/hr/demandes?employee_id=${employeeId}`)}
            >
              Voir dans Demandes de congé →
            </button>
          </div>
          <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {leaveBalances.length === 0 && (
              <p className="text-sm text-slate-400">Aucun solde suivi pour ce collaborateur.</p>
            )}
            {leaveBalances.map((b) => (
              <div
                key={b.leave_type_id}
                className="rounded-lg border border-slate-100 bg-brand-50 p-3"
              >
                <div className="text-xs text-slate-500">{b.leave_type_libelle}</div>
                <div className="text-lg font-bold text-slate-900">{b.solde} j</div>
                <div className="text-xs text-slate-400">
                  {b.jours_acquis} acquis · {b.jours_pris} pris
                </div>
              </div>
            ))}
          </div>

          <h3 className="mb-3 text-sm font-semibold text-slate-700">Historique des demandes</h3>
          <Table>
            <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
              <tr>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Période</th>
                <th className="px-3 py-2">Jours</th>
                <th className="px-3 py-2">Statut</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {leaveRequests.length === 0 && (
                <tr>
                  <td className="px-3 py-4 text-center text-slate-400" colSpan={5}>
                    Aucune demande de congé.
                  </td>
                </tr>
              )}
              {leaveRequests.map((r) => (
                <tr key={r.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-3 py-2">{r.leave_type_libelle}</td>
                  <td className="px-3 py-2 text-slate-600">
                    {r.date_debut} → {r.date_fin}
                  </td>
                  <td className="px-3 py-2 text-slate-600">{r.nb_jours}</td>
                  <td className="px-3 py-2">
                    <StatusBadge status={r.status} />
                  </td>
                  <td className="px-3 py-2 text-right">
                    {r.status === 'approved' && r.has_certificate && (
                      <a
                        className="text-sm font-medium text-brand-700 hover:underline"
                        href={`/api/leave-requests/${r.id}/certificate`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Certificat
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      )}

      {tab === 'presence' && (
        <Card className="p-5">
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-slate-700">
              Ce mois-ci ({String(currentMonth).padStart(2, '0')}/{currentYear})
            </h3>
            <button
              className="text-sm font-medium text-brand-700 hover:underline"
              onClick={() => navigate('/hr/presence')}
            >
              Voir le module Présence →
            </button>
          </div>
          {!monthlySummary ? (
            <p className="text-sm text-slate-400">Aucune donnée de présence pour ce mois.</p>
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-lg border border-slate-100 bg-brand-50 p-3">
                <div className="text-xs text-slate-500">Jours travaillés</div>
                <div className="text-lg font-bold text-slate-900">
                  {monthlySummary.jours_travailles} j
                </div>
                <div className="text-xs text-slate-400">
                  sur {monthlySummary.jours_ouvres_mois} j ouvrés
                </div>
              </div>
              <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <div className="text-xs text-slate-500">Congé payé</div>
                <div className="text-lg font-bold text-slate-900">
                  {monthlySummary.conge_paye} j
                </div>
              </div>
              <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <div className="text-xs text-slate-500">Récupération</div>
                <div className="text-lg font-bold text-slate-900">
                  {monthlySummary.recuperation} j
                </div>
              </div>
              <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <div className="text-xs text-slate-500">Mission</div>
                <div className="text-lg font-bold text-slate-900">{monthlySummary.mission} j</div>
              </div>
              <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <div className="text-xs text-slate-500">Congé exceptionnel</div>
                <div className="text-lg font-bold text-slate-900">
                  {monthlySummary.conge_exceptionnel} j
                </div>
              </div>
              <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <div className="text-xs text-slate-500">Absence maladie</div>
                <div className="text-lg font-bold text-slate-900">
                  {monthlySummary.absence_maladie} j
                </div>
              </div>
              <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <div className="text-xs text-slate-500">Congé sans solde</div>
                <div className="text-lg font-bold text-slate-900">
                  {monthlySummary.conge_sans_solde} j
                </div>
              </div>
              <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <div className="text-xs text-slate-500">Absence non justifiée</div>
                <div className="text-lg font-bold text-slate-900">{monthlySummary.absence} j</div>
              </div>
            </div>
          )}
        </Card>
      )}

      {showDeactivate && (
        <Modal title="Désactiver ce collaborateur ?" onClose={() => setShowDeactivate(false)}>
          <p className="mb-4 text-sm text-slate-600">
            Le dossier n'est pas supprimé : la date de sortie est enregistrée et le statut passe à
            inactif. L'historique (congés, présence, etc.) reste intact.
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setShowDeactivate(false)}>
              Annuler
            </Button>
            <Button variant="danger" onClick={deactivate}>
              Confirmer
            </Button>
          </div>
        </Modal>
      )}
    </div>
  )
}
