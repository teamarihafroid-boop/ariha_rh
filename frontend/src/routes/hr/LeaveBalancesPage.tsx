import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError, type EmployeeLite, type LeaveBalance, type LeaveType } from '../../lib/api'
import { Card, ErrorBanner, Field, Input, PageHeader, Select, Table } from '../../components/ui'

const currentYear = new Date().getFullYear()
const YEAR_OPTIONS = [currentYear - 1, currentYear, currentYear + 1]

export function LeaveBalancesPage() {
  const navigate = useNavigate()
  const [employees, setEmployees] = useState<EmployeeLite[]>([])
  const [leaveTypes, setLeaveTypes] = useState<LeaveType[]>([])
  const [balances, setBalances] = useState<LeaveBalance[]>([])
  const [annee, setAnnee] = useState(currentYear)
  const [q, setQ] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    setError(null)
    Promise.all([
      api.get<EmployeeLite[]>('/employees'),
      api.get<LeaveType[]>('/leave-types'),
      api.get<LeaveBalance[]>(`/leave-balances?annee=${annee}`),
    ])
      .then(([emps, types, bals]) => {
        setEmployees(emps)
        setLeaveTypes(types.filter((t) => t.deduit_du_solde))
        setBalances(bals)
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur de chargement.'))
      .finally(() => setLoading(false))
  }, [annee])

  const filteredEmployees = useMemo(() => {
    const needle = q.trim().toLowerCase()
    if (!needle) return employees
    return employees.filter((e) =>
      [e.full_name, e.matricule, e.department_nom]
        .filter(Boolean)
        .some((v) => v!.toLowerCase().includes(needle)),
    )
  }, [employees, q])

  const balanceFor = (employeeId: number, leaveTypeId: number) =>
    balances.find((b) => b.employee_id === employeeId && b.leave_type_id === leaveTypeId)

  return (
    <div>
      <PageHeader
        title="Soldes de congés"
        subtitle="Vue d'ensemble : solde de congé payé et de récupération de chaque collaborateur."
      />
      <ErrorBanner message={error} />

      <Card className="mb-4 p-4">
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Recherche" className="min-w-[12rem] flex-1">
            <Input
              placeholder="Nom, matricule, département…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </Field>
          <Field label="Année">
            <Select value={annee} onChange={(e) => setAnnee(Number(e.target.value))}>
              {YEAR_OPTIONS.map((y) => (
                <option key={y} value={y}>
                  {y}
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
              <th className="px-4 py-2">Collaborateur</th>
              <th className="px-4 py-2">Département</th>
              {leaveTypes.map((t) => (
                <th key={t.id} className="px-4 py-2 text-right">
                  {t.libelle}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td
                  className="px-4 py-6 text-center text-slate-400"
                  colSpan={2 + leaveTypes.length}
                >
                  Chargement…
                </td>
              </tr>
            )}
            {!loading && filteredEmployees.length === 0 && (
              <tr>
                <td
                  className="px-4 py-6 text-center text-slate-400"
                  colSpan={2 + leaveTypes.length}
                >
                  Aucun collaborateur ne correspond à cette recherche.
                </td>
              </tr>
            )}
            {filteredEmployees.map((e) => (
              <tr key={e.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-3 font-medium text-slate-800">
                  <button
                    className="hover:underline"
                    onClick={() => navigate(`/hr/collaborateurs/${e.id}`)}
                  >
                    {e.full_name}
                  </button>
                </td>
                <td className="px-4 py-3 text-slate-600">{e.department_nom ?? '—'}</td>
                {leaveTypes.map((t) => {
                  const b = balanceFor(e.id, t.id)
                  return (
                    <td key={t.id} className="px-4 py-3 text-right">
                      {b ? (
                        <>
                          <div className="font-semibold text-slate-900">{b.solde} j</div>
                          <div className="text-xs text-slate-400">
                            {b.jours_acquis} acquis · {b.jours_pris} pris
                          </div>
                        </>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </div>
  )
}
