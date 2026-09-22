import { useEffect, useState } from 'react'
import { api, ApiError, type Employee, type EmployeeLite } from '../../lib/api'
import { Card, ErrorBanner, Modal, PageHeader, Table } from '../../components/ui'

export function EmployeesOverview() {
  const [employees, setEmployees] = useState<EmployeeLite[]>([])
  const [selected, setSelected] = useState<Employee | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get<EmployeeLite[]>('/employees')
      .then(setEmployees)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur.'))
      .finally(() => setLoading(false))
  }, [])

  const openDetail = async (id: number) => {
    setError(null)
    try {
      const employee = await api.get<Employee>(`/employees/${id}`)
      setSelected(employee)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  return (
    <div>
      <PageHeader
        title="Collaborateurs — vue d'ensemble"
        subtitle="Lecture seule, données de toute l'entreprise."
      />
      <ErrorBanner message={error} />

      <Card>
        <Table>
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Nom</th>
              <th className="px-4 py-2" />
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
            {!loading && employees.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={2}>
                  Aucun collaborateur.
                </td>
              </tr>
            )}
            {employees.map((e) => (
              <tr
                key={e.id}
                className="cursor-pointer border-b border-slate-100 last:border-0 hover:bg-slate-50"
                onClick={() => openDetail(e.id)}
              >
                <td className="px-4 py-3 font-medium text-slate-800">{e.full_name}</td>
                <td className="px-4 py-3 text-right text-sm text-brand-700">Voir la fiche →</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      {selected && (
        <Modal
          title={selected.full_name}
          onClose={() => setSelected(null)}
          maxWidthClassName="max-w-2xl"
        >
          <a
            href={`/api/employees/${selected.id}/fiche`}
            target="_blank"
            rel="noreferrer"
            className="mb-4 inline-block rounded-lg bg-slate-100 px-3.5 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-200"
          >
            Télécharger la fiche
          </a>
          <dl className="grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
            {(
              [
                ['Matricule', selected.matricule],
                ['CIN', selected.cin],
                ['CNSS', selected.cnss],
                ['Email', selected.email],
                ['Téléphone', selected.telephone],
                ['Fonction', selected.position_intitule],
                ['Département', selected.department_nom],
                ["Date d'embauche", selected.date_embauche],
                ['Statut', selected.status_libelle],
                ['Salaire de base', selected.salaire_base],
                ['Salaire net', selected.salaire_net],
              ] as [string, string | null][]
            ).map(([label, val]) => (
              <div key={label}>
                <dt className="text-xs uppercase text-slate-400">{label}</dt>
                <dd className="text-sm text-slate-800">{val ?? '—'}</dd>
              </div>
            ))}
          </dl>

          <div className="mt-5 border-t border-slate-200 pt-4">
            <h3 className="mb-2 text-sm font-semibold text-slate-800">Documents</h3>
            {selected.documents.length === 0 ? (
              <p className="text-sm text-slate-400">Aucun document.</p>
            ) : (
              <ul className="space-y-1">
                {selected.documents.map((d) => (
                  <li key={d.id} className="flex items-center justify-between text-sm">
                    <a
                      href={`/api/employees/${selected.id}/documents/${d.id}/download`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-brand-700 hover:underline"
                    >
                      {d.type_document} — {d.nom_fichier}
                    </a>
                    {d.date_expiration && (
                      <span className="text-xs text-slate-400">Exp. {d.date_expiration}</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Modal>
      )}
    </div>
  )
}
