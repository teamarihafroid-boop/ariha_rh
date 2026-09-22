import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { mockFetch } from '../../test/mockFetch'
import { JobOffersPage } from './JobOffersPage'

const OFFER = {
  id: 1,
  titre: 'Technicien froid',
  ville: 'Casablanca',
  department_id: 1,
  department_nom: 'Direction',
  position_id: null,
  position_intitule: 'Technicien',
  status_id: 1,
  status_libelle: 'Ouverte',
  status_couleur: '#43A047',
  description: null,
  responsable: null,
  date_creation: '2026-09-01T00:00:00Z',
  date_cloture: null,
  candidatures_count: 3,
}

describe('JobOffersPage', () => {
  it('lists job offers with their poste and candidature count', async () => {
    mockFetch({
      '/api/recruitment/job-offers': { body: [OFFER] },
      '/api/recruitment/job-offer-statuses': {
        body: [{ id: 1, libelle: 'Ouverte', couleur: '#43A047' }],
      },
      '/api/departments': { body: [] },
      '/api/positions': { body: [] },
    })

    render(
      <MemoryRouter>
        <JobOffersPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Technicien froid')).toBeInTheDocument()
    expect(screen.getAllByText('Technicien').length).toBeGreaterThan(0)
    expect(screen.getByText('3 candidatures')).toBeInTheDocument()
  })

  it('filters offers by the search box without a server round-trip', async () => {
    mockFetch({
      '/api/recruitment/job-offers': {
        body: [OFFER, { ...OFFER, id: 2, titre: 'Comptable', position_intitule: 'Comptable' }],
      },
      '/api/recruitment/job-offer-statuses': {
        body: [{ id: 1, libelle: 'Ouverte', couleur: '#43A047' }],
      },
      '/api/departments': { body: [] },
      '/api/positions': { body: [] },
    })

    render(
      <MemoryRouter>
        <JobOffersPage />
      </MemoryRouter>,
    )

    await screen.findByText('Technicien froid')
    expect(screen.getAllByText('Comptable').length).toBeGreaterThan(0)

    await userEvent.type(screen.getByPlaceholderText('Titre, ville, département, poste…'), 'froid')

    expect(screen.queryByText('Comptable')).not.toBeInTheDocument()
    expect(screen.getByText('Technicien froid')).toBeInTheDocument()
  })

  it('hides deactivated départements/postes from the new-offer form but shows them when editing an offer that already uses one', async () => {
    mockFetch({
      '/api/recruitment/job-offers': { body: [OFFER] },
      '/api/recruitment/job-offer-statuses': {
        body: [{ id: 1, libelle: 'Ouverte', couleur: '#43A047' }],
      },
      '/api/departments': {
        body: [
          {
            id: 1,
            nom: 'Direction',
            description: null,
            leave_responsable_employee_id: null,
            is_active: true,
          },
          {
            id: 2,
            nom: 'Ancien département',
            description: null,
            leave_responsable_employee_id: null,
            is_active: false,
          },
        ],
      },
      '/api/positions': {
        body: [
          { id: 10, intitule: 'Technicien', department_id: 1, is_active: true },
          { id: 11, intitule: 'Ancien poste', department_id: 2, is_active: false },
        ],
      },
    })

    render(
      <MemoryRouter>
        <JobOffersPage />
      </MemoryRouter>,
    )

    await screen.findByText('Technicien froid')

    // New-offer form: deactivated département/poste must not be selectable.
    await userEvent.click(screen.getByText('Nouvelle offre'))
    expect(screen.queryByText('Ancien département (inactif)')).not.toBeInTheDocument()
    expect(screen.queryByText('Ancien poste (inactif)')).not.toBeInTheDocument()
    await userEvent.click(screen.getByText('Fermer'))

    // Editing an offer that already points to an active département/poste
    // still doesn't offer the unrelated deactivated ones.
    await userEvent.click(screen.getByText('Modifier'))
    expect(screen.queryByText('Ancien département (inactif)')).not.toBeInTheDocument()
    expect(screen.queryByText('Ancien poste (inactif)')).not.toBeInTheDocument()
  })

  it('shows the deactivated département/poste already assigned to the offer being edited', async () => {
    const offerOnInactiveDept = {
      ...OFFER,
      department_id: 2,
      department_nom: 'Ancien département',
      position_id: 11,
      position_intitule: 'Ancien poste',
    }
    mockFetch({
      '/api/recruitment/job-offers': { body: [offerOnInactiveDept] },
      '/api/recruitment/job-offer-statuses': {
        body: [{ id: 1, libelle: 'Ouverte', couleur: '#43A047' }],
      },
      '/api/departments': {
        body: [
          {
            id: 1,
            nom: 'Direction',
            description: null,
            leave_responsable_employee_id: null,
            is_active: true,
          },
          {
            id: 2,
            nom: 'Ancien département',
            description: null,
            leave_responsable_employee_id: null,
            is_active: false,
          },
        ],
      },
      '/api/positions': {
        body: [
          { id: 10, intitule: 'Technicien', department_id: 1, is_active: true },
          { id: 11, intitule: 'Ancien poste', department_id: 2, is_active: false },
        ],
      },
    })

    render(
      <MemoryRouter>
        <JobOffersPage />
      </MemoryRouter>,
    )

    await screen.findByText('Ancien département')
    await userEvent.click(screen.getByText('Modifier'))

    expect(screen.getByText('Ancien département (inactif)')).toBeInTheDocument()
    expect(screen.getByText('Ancien poste (inactif)')).toBeInTheDocument()

    // But the new-offer form still can't select it.
    await userEvent.click(screen.getByRole('button', { name: 'Annuler' }))
    await userEvent.click(screen.getByText('Nouvelle offre'))
    expect(screen.queryByText('Ancien département (inactif)')).not.toBeInTheDocument()
  })
})
