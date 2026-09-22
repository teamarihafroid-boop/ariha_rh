export type Role = 'hr' | 'dg' | 'employee'

export interface Me {
  id: number
  email: string
  role: Role
  employee_id: number | null
  department_id: number | null
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  const { method = 'GET', body } = options
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (method !== 'GET' && method !== 'HEAD') {
    const csrf = getCookie('csrf_token')
    if (csrf) headers['X-CSRF-Token'] = csrf
  }

  const resp = await fetch(`/api${path}`, {
    method,
    headers,
    credentials: 'include',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (!resp.ok) {
    let detail = resp.statusText
    try {
      const data = await resp.json()
      detail = data.detail ?? detail
    } catch {
      // response had no JSON body
    }
    throw new ApiError(resp.status, detail)
  }

  if (resp.status === 204) return undefined as T
  const contentType = resp.headers.get('content-type') ?? ''
  if (contentType.includes('application/json')) return resp.json() as Promise<T>
  return undefined as T
}

async function upload<T>(path: string, formData: FormData): Promise<T> {
  const headers: Record<string, string> = {}
  const csrf = getCookie('csrf_token')
  if (csrf) headers['X-CSRF-Token'] = csrf

  const resp = await fetch(`/api${path}`, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: formData,
  })

  if (!resp.ok) {
    let detail = resp.statusText
    try {
      const data = await resp.json()
      detail = data.detail ?? detail
    } catch {
      // response had no JSON body
    }
    throw new ApiError(resp.status, detail)
  }
  return resp.json() as Promise<T>
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  upload,
}

export type LeaveStatus = 'pending' | 'approved' | 'rejected' | 'cancelled'

export interface LeaveType {
  id: number
  libelle: string
  couleur: string
  deduit_du_solde: boolean
  accrual_legal: boolean
  is_active: boolean
  code_court: string | null
  employee_requestable: boolean
  certificate_kind: string | null
}

export interface Holiday {
  id: number
  date: string
  libelle: string
}

export interface LeaveRequest {
  id: number
  employee_id: number
  employee_nom: string
  leave_type_id: number
  leave_type_libelle: string
  has_certificate: boolean
  date_debut: string
  date_fin: string
  nb_jours: string
  commentaire: string | null
  status: LeaveStatus
  submitted_by_user_id: number
  decided_by_user_id: number | null
  decision_comment: string | null
  decided_at: string | null
  created_at: string
}

export interface LeaveBalance {
  employee_id: number
  leave_type_id: number
  leave_type_libelle: string
  annee: number
  jours_acquis: string
  jours_pris: string
  solde: string
}

export interface MonthlySummary {
  employee_id: number
  mois: number
  annee: number
  jours_ouvres_mois: string
  jours_travailles: string
  conge_paye: string
  recuperation: string
  conge_exceptionnel: string
  absence_maladie: string
  conge_sans_solde: string
  absence: string
  mission: number
  jours_non_travailles: string
}

export interface Department {
  id: number
  nom: string
  description: string | null
  leave_responsable_employee_id: number | null
  is_active: boolean
}

export interface EmployeeLite {
  id: number
  full_name: string
  matricule: string | null
  department_id: number | null
  department_nom: string | null
  position_intitule: string | null
  status_libelle: string | null
  status_couleur: string | null
}

export interface Position {
  id: number
  intitule: string
  department_id: number | null
  is_active: boolean
}

export interface EmployeeStatus {
  id: number
  libelle: string
  couleur: string
  is_active_status: boolean
}

export interface NotificationItem {
  id: number
  type: 'leave_approved' | 'leave_rejected' | 'leave_pending'
  title: string
  body: string
  related_entity_type: string
  related_entity_id: number
  is_read: boolean
  created_at: string
}

export interface StalledApplication {
  application_id: number
  candidate_nom: string
  job_offer_titre: string
  stage_libelle: string | null
  date_dernier_mouvement: string
  jours_stagnation: number
}

export interface AttendanceCode {
  id: number
  libelle: string
  code_court: string
  couleur: string
  compte_absence: boolean
  is_active: boolean
}

export interface UploadPreview {
  token: string
  columns: string[]
  sample_rows: Record<string, string>[]
  guessed_identifier_column: string | null
  guessed_day_columns: string[]
  nb_rows: number
  unmapped_values: string[]
}

export interface ImportResult {
  id: number
  nom_fichier: string
  mois: number
  annee: number
  nb_lignes_importees: number
  nb_lignes_non_reconnues: number
  noms_non_reconnus: string[]
}

export interface EmergencyContact {
  id: number
  nom: string
  lien: string | null
  telephone: string
}

export interface EmergencyContactCreate {
  nom: string
  lien: string | null
  telephone: string
}

export interface ProbationEvaluation {
  id: number
  date_evaluation: string
  avis_rh: string | null
  evaluateur_rh: string | null
  avis_dg: string | null
  evaluateur_dg: string | null
  decision: string | null
  nouvelle_date_fin: string | null
}

export interface ProbationEvaluationCreate {
  date_evaluation: string
  avis_rh: string | null
  evaluateur_rh: string | null
  avis_dg: string | null
  evaluateur_dg: string | null
  decision: string | null
  nouvelle_date_fin: string | null
}

export interface ProbationAlert {
  employee_id: number
  employee_nom: string
  date_fin_periode_essai: string
  urgence: 'retard' | 'urgent' | 'semaine'
  a_evaluation_complete: boolean
}

export interface EmployeeDocument {
  id: number
  type_document: string
  nom_fichier: string
  content_type: string
  taille_octets: number
  date_expiration: string | null
  uploaded_by_email: string
  created_at: string
}

export interface DocumentAlert {
  employee_id: number
  employee_nom: string
  document_id: number
  type_document: string
  date_expiration: string
  urgence: 'retard' | 'urgent' | 'semaine'
}

export interface EmployeeEquipment {
  id: number
  libelle: string
}

export interface Employee {
  id: number
  matricule: string | null
  nom: string
  prenom: string
  full_name: string
  nom_arabe: string | null
  prenom_arabe: string | null
  date_naissance: string | null
  lieu_naissance: string | null
  date_embauche: string | null
  date_sortie: string | null
  motif_sortie: string | null
  date_fin_periode_essai: string | null
  email: string | null
  telephone: string | null
  ville: string | null
  adresse: string | null
  cin: string | null
  cnss: string | null
  type_contrat: string | null
  categorie_professionnelle: string | null
  salaire_base: string | null
  salaire_net: string | null
  notes: string | null
  equipe: string | null
  department_id: number | null
  department_nom: string | null
  position_id: number | null
  position_intitule: string | null
  status_id: number | null
  status_libelle: string | null
  manager_id: number | null
  manager_nom: string | null
  emergency_contacts: EmergencyContact[]
  probation_evaluations: ProbationEvaluation[]
  documents: EmployeeDocument[]
  equipements: EmployeeEquipment[]
}

export type EmployeeFormInput = Omit<
  Employee,
  | 'id'
  | 'full_name'
  | 'department_nom'
  | 'position_intitule'
  | 'status_libelle'
  | 'manager_nom'
  | 'emergency_contacts'
  | 'probation_evaluations'
  | 'documents'
  | 'equipements'
>

export type OrgChartNiveau = 'direction' | 'equipe' | 'responsable' | 'employe'

export interface OrgChartNode {
  id: number
  full_name: string
  department_id: number | null
  department_nom: string | null
  position_intitule: string | null
  niveau: OrgChartNiveau
  rapporte_a: { id: number; nom_complet: string; department_nom: string | null } | null
  enfants: OrgChartNode[]
}

export interface OrgChartVacant {
  id: number
  titre: string
  ville: string | null
}

export interface OrgChartDepartment {
  department_id: number
  department_nom: string
  collaborateurs: OrgChartNode[]
  postes_ouverts: OrgChartVacant[]
}

export interface OrgChart {
  direction: OrgChartNode[]
  departements: OrgChartDepartment[]
}

export interface JobOfferStatus {
  id: number
  libelle: string
  couleur: string
}

export interface ApplicationStage {
  id: number
  libelle: string
  ordre: number
  couleur: string
  is_hire_stage: boolean
}

export interface JobOffer {
  id: number
  titre: string
  ville: string | null
  department_id: number | null
  department_nom: string | null
  position_id: number | null
  position_intitule: string | null
  status_id: number
  status_libelle: string
  status_couleur: string
  description: string | null
  responsable: string | null
  date_creation: string
  date_cloture: string | null
  candidatures_count: number
}

export interface JobOfferInput {
  titre: string
  ville: string | null
  department_id: number | null
  position_id: number | null
  status_id: number
  description: string | null
  responsable: string | null
  date_cloture: string | null
}

export interface CandidateAttachment {
  id: number
  type_document: string
  nom_fichier: string
  content_type: string
  taille_octets: number
  uploaded_by_email: string
  created_at: string
}

export interface CandidateApplication {
  id: number
  job_offer_id: number
  job_offer_titre: string
  stage_libelle: string | null
}

export interface Candidate {
  id: number
  nom_complet: string
  telephone: string | null
  email: string | null
  ville: string | null
  annees_experience: string | null
  experience_resume: string | null
  competences: string | null
  diplomes: string | null
  langues: string | null
  favori: boolean
  notes: string | null
  employee_id: number | null
  date_ajout: string
  attachments: CandidateAttachment[]
  applications: CandidateApplication[]
}

export interface CandidateInput {
  nom_complet: string
  telephone: string | null
  email: string | null
  ville: string | null
  annees_experience: string | null
  experience_resume: string | null
  competences: string | null
  diplomes: string | null
  langues: string | null
  favori: boolean
  notes: string | null
}

export interface CandidateCreateResult {
  candidate: Candidate
  duplicates: Candidate[]
}

export interface CvFields {
  nom_complet: string | null
  telephone: string | null
  email: string | null
  ville: string | null
  experience_resume: string | null
  competences: string | null
  diplomes: string | null
  langues: string | null
}

export interface JobApplication {
  id: number
  candidate_id: number
  candidate_nom: string
  candidate_ville: string | null
  job_offer_id: number
  job_offer_titre: string
  stage_id: number | null
  stage_libelle: string | null
  responsable: string | null
  date_creation: string
  date_dernier_mouvement: string
}

export interface BulkCvImportItem {
  filename: string
  status: 'created' | 'linked_existing' | 'already_applied' | 'error'
  message: string | null
  candidate: Candidate | null
  application: JobApplication | null
}

export interface BulkCvImportResult {
  items: BulkCvImportItem[]
}

export interface ApplicationComment {
  id: number
  application_id: number
  texte: string
  auteur_email: string
  created_at: string
}

export interface HirePreview {
  prenom_suggere: string
  nom_suggere: string
  telephone: string | null
  email: string | null
  ville: string | null
  department_id: number | null
  department_nom: string | null
  cv_disponible: boolean
}

export interface HireRequest {
  prenom: string
  nom: string
  telephone: string | null
  email: string | null
  ville: string | null
  department_id: number | null
  position_id: number | null
  categorie_professionnelle: string | null
  date_embauche: string | null
  date_fin_periode_essai: string | null
}

export interface AppUser {
  id: number
  email: string
  role: Role
  employee_id: number | null
  employee_nom: string | null
  is_active: boolean
  last_login_at: string | null
  created_at: string
}

export interface UserCreateInput {
  email: string
  password: string
  role: Role
  employee_id: number | null
}

export interface UserUpdateInput {
  role: Role
  employee_id: number | null
  is_active: boolean
}
