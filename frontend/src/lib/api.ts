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

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}

export type LeaveStatus = 'pending' | 'approved' | 'rejected' | 'cancelled'

export interface LeaveType {
  id: number
  libelle: string
  couleur: string
  deduit_du_solde: boolean
  accrual_legal: boolean
  is_active: boolean
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

export interface Department {
  id: number
  nom: string
  description: string | null
  leave_responsable_employee_id: number | null
}

export interface EmployeeLite {
  id: number
  full_name: string
  department_id: number | null
}

export interface NotificationItem {
  id: number
  type: 'leave_approved' | 'leave_rejected'
  title: string
  body: string
  related_entity_type: string
  related_entity_id: number
  is_read: boolean
  created_at: string
}
