import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { mockFetch } from '../../test/mockFetch'
import { EmployeesOverview } from './EmployeesOverview'

describe('EmployeesOverview (DG)', () => {
  it('lists employees read-only', async () => {
    mockFetch({
      '/api/employees': { body: [{ id: 1, full_name: 'Sara Alami', department_id: 1 }] },
    })

    render(<EmployeesOverview />)

    expect(await screen.findByText('Sara Alami')).toBeInTheDocument()
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('shows read-only documents in the detail modal, no upload control', async () => {
    mockFetch({
      '/api/employees': { body: [{ id: 1, full_name: 'Sara Alami', department_id: 1 }] },
      '/api/employees/1': {
        body: {
          id: 1,
          matricule: 'c122',
          cin: null,
          cnss: null,
          email: null,
          telephone: null,
          position_intitule: null,
          department_nom: null,
          date_embauche: null,
          status_libelle: null,
          salaire_base: null,
          salaire_net: null,
          full_name: 'Sara Alami',
          documents: [
            {
              id: 7,
              type_document: 'CV',
              nom_fichier: 'cv-sara.pdf',
              content_type: 'application/pdf',
              taille_octets: 10240,
              date_expiration: null,
              uploaded_by_email: 'rh@arihafroid.ma',
              created_at: '2026-09-05T00:00:00Z',
            },
          ],
        },
      },
    })

    render(<EmployeesOverview />)
    await userEvent.click(await screen.findByText('Sara Alami'))

    expect(await screen.findByText('CV — cv-sara.pdf')).toBeInTheDocument()
    expect(screen.queryByText('Téléverser')).not.toBeInTheDocument()
  })
})
