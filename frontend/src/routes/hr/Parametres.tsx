import { useEffect, useState } from 'react'
import { api, ApiError, type Department, type EmployeeLite } from '../../lib/api'
import { Card, ErrorBanner, PageHeader, Table } from '../../components/ui'

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
    </div>
  )
}
