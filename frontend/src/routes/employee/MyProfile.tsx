import { useEffect, useState } from 'react'
import { api, ApiError, type Employee } from '../../lib/api'
import { Card, ErrorBanner, PageHeader } from '../../components/ui'

export function MyProfile() {
  const [employee, setEmployee] = useState<Employee | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<Employee>('/employees/me')
      .then(setEmployee)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur de chargement.'))
  }, [])

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <PageHeader
          title="Mon profil"
          subtitle="Récapitulatif de votre dossier. Pour toute correction, contactez le service RH directement."
        />
        {employee && (
          <a
            href="/api/employees/me/fiche"
            target="_blank"
            rel="noreferrer"
            className="rounded-lg bg-slate-100 px-3.5 py-2 text-sm font-semibold text-slate-800 hover:bg-slate-200"
          >
            Télécharger ma fiche
          </a>
        )}
      </div>
      <ErrorBanner message={error} />

      {employee && (
        <Card className="p-5">
          <h2 className="mb-4 text-base font-semibold text-slate-900">{employee.full_name}</h2>
          <dl className="grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2 lg:grid-cols-3">
            {(
              [
                ['Matricule', employee.matricule],
                ['Email', employee.email],
                ['Téléphone', employee.telephone],
                ['Ville', employee.ville],
                ['Adresse', employee.adresse],
                ['Fonction', employee.position_intitule],
                ['Département', employee.department_nom],
                ["Date d'embauche", employee.date_embauche],
                ['Date de naissance', employee.date_naissance],
                ['Responsable hiérarchique', employee.manager_nom],
              ] as [string, string | null][]
            ).map(([label, val]) => (
              <div key={label}>
                <dt className="text-xs uppercase text-slate-400">{label}</dt>
                <dd className="text-sm text-slate-800">{val ?? '—'}</dd>
              </div>
            ))}
          </dl>

          {employee.emergency_contacts.length > 0 && (
            <div className="mt-6">
              <h3 className="mb-2 text-xs uppercase text-slate-400">Contacts d'urgence</h3>
              <ul className="space-y-1 text-sm text-slate-700">
                {employee.emergency_contacts.map((c) => (
                  <li key={c.id}>
                    {c.nom} {c.lien ? `(${c.lien})` : ''} — {c.telephone}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
