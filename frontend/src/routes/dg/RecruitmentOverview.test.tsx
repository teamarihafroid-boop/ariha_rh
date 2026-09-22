import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { mockFetch } from '../../test/mockFetch'
import { RecruitmentOverview } from './RecruitmentOverview'

describe('RecruitmentOverview (DG)', () => {
  it('renders offers and candidates read-only', async () => {
    mockFetch({
      '/api/recruitment/job-offers': {
        body: [
          {
            id: 1,
            titre: 'Technicien froid',
            ville: null,
            department_id: null,
            department_nom: null,
            position_id: null,
            position_intitule: null,
            status_id: 1,
            status_libelle: 'Ouverte',
            description: null,
            responsable: null,
            date_creation: '2026-09-01T00:00:00Z',
            date_cloture: null,
          },
        ],
      },
      '/api/recruitment/candidates': {
        body: [
          {
            id: 1,
            nom_complet: 'Karim Idrissi',
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
            employee_id: null,
            date_ajout: '2026-09-01T00:00:00Z',
          },
        ],
      },
      '/api/recruitment/application-stages': { body: [] },
      '/api/recruitment/applications': { body: [] },
    })

    render(<RecruitmentOverview />)

    expect((await screen.findAllByText('Technicien froid')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Karim Idrissi')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
