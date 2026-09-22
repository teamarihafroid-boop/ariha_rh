import { useEffect, useState } from 'react'
import {
  api,
  ApiError,
  type ApplicationStage,
  type Candidate,
  type JobApplication,
  type JobOffer,
} from '../../lib/api'
import { Card, ErrorBanner, PageHeader, Select, Table } from '../../components/ui'

export function RecruitmentOverview() {
  const [offers, setOffers] = useState<JobOffer[]>([])
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [stages, setStages] = useState<ApplicationStage[]>([])
  const [offerId, setOfferId] = useState<number | null>(null)
  const [applications, setApplications] = useState<JobApplication[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      api.get<JobOffer[]>('/recruitment/job-offers'),
      api.get<Candidate[]>('/recruitment/candidates'),
      api.get<ApplicationStage[]>('/recruitment/application-stages'),
    ])
      .then(([o, c, s]) => {
        setOffers(o)
        setCandidates(c)
        setStages(s)
        if (o.length > 0) setOfferId(o[0].id)
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur.'))
  }, [])

  useEffect(() => {
    if (offerId === null) return
    api
      .get<JobApplication[]>(`/recruitment/applications?job_offer_id=${offerId}`)
      .then(setApplications)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur.'))
  }, [offerId])

  return (
    <div>
      <PageHeader
        title="Recrutement — vue d'ensemble"
        subtitle="Lecture seule, données de toute l'entreprise."
      />
      <ErrorBanner message={error} />

      <Card className="mb-6">
        <Table>
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Offre</th>
              <th className="px-4 py-2">Ville</th>
              <th className="px-4 py-2">Statut</th>
            </tr>
          </thead>
          <tbody>
            {offers.map((o) => (
              <tr key={o.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-3 font-medium text-slate-800">{o.titre}</td>
                <td className="px-4 py-3 text-slate-600">{o.ville ?? '—'}</td>
                <td className="px-4 py-3 text-slate-600">{o.status_libelle}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <div className="mb-4 max-w-xs">
        <Select
          value={offerId ?? ''}
          onChange={(e) => setOfferId(e.target.value ? Number(e.target.value) : null)}
        >
          {offers.map((o) => (
            <option key={o.id} value={o.id}>
              {o.titre}
            </option>
          ))}
        </Select>
      </div>

      <div className="mb-8 flex gap-4 overflow-x-auto pb-2">
        {stages.map((stage) => (
          <div
            key={stage.id}
            className="w-56 flex-none rounded-xl border border-slate-200 bg-slate-50 p-3"
          >
            <div className="mb-2 text-xs font-semibold uppercase" style={{ color: stage.couleur }}>
              {stage.libelle}
            </div>
            <div className="space-y-2">
              {applications
                .filter((a) => a.stage_id === stage.id)
                .map((a) => (
                  <Card key={a.id} className="p-2 text-sm">
                    <div className="font-medium text-slate-800">{a.candidate_nom}</div>
                    <div className="text-xs text-slate-500">{a.candidate_ville ?? '—'}</div>
                  </Card>
                ))}
            </div>
          </div>
        ))}
      </div>

      <Card>
        <Table>
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Candidat</th>
              <th className="px-4 py-2">Ville</th>
              <th className="px-4 py-2">Contact</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((c) => (
              <tr key={c.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-3 font-medium text-slate-800">{c.nom_complet}</td>
                <td className="px-4 py-3 text-slate-600">{c.ville ?? '—'}</td>
                <td className="px-4 py-3 text-slate-600">
                  {[c.telephone, c.email].filter(Boolean).join(' · ') || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </div>
  )
}
