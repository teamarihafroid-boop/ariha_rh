import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { mockFetch } from '../../test/mockFetch'
import { EmployeesPage } from './EmployeesPage'

describe('EmployeesPage', () => {
  it('lists employees with their scan context (matricule, poste, département, statut)', async () => {
    mockFetch({
      '/api/departments': {
        body: [{ id: 1, nom: 'Direction', description: null, leave_responsable_employee_id: null }],
      },
      '/api/positions': { body: [] },
      '/api/employee-statuses': { body: [] },
      '/api/employees': {
        body: [
          {
            id: 1,
            full_name: 'Sara Alami',
            matricule: 'MAT-001',
            department_id: 1,
            department_nom: 'Direction',
            position_intitule: 'Responsable RH',
            status_libelle: 'Actif',
            status_couleur: '#43A047',
          },
        ],
      },
      '/api/employees/periode-essai/alertes': { body: [] },
      '/api/employees/documents/alertes': { body: [] },
    })

    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Sara Alami')).toBeInTheDocument()
    expect(screen.getByText('MAT-001')).toBeInTheDocument()
    expect(screen.getByText('Responsable RH')).toBeInTheDocument()
    // "Direction" also appears as a department-filter <option>, so scope to the table row.
    expect(screen.getAllByText('Direction').length).toBeGreaterThan(0)
    expect(screen.getByText('Actif')).toBeInTheDocument()
  })

  it('shows a banner for documents nearing expiry', async () => {
    mockFetch({
      '/api/departments': { body: [] },
      '/api/positions': { body: [] },
      '/api/employee-statuses': { body: [] },
      '/api/employees': { body: [{ id: 1, full_name: 'Sara Alami', department_id: 1 }] },
      '/api/employees/periode-essai/alertes': { body: [] },
      '/api/employees/documents/alertes': {
        body: [
          {
            employee_id: 1,
            employee_nom: 'Sara Alami',
            document_id: 9,
            type_document: 'CIN scanné',
            date_expiration: '2026-09-20',
            urgence: 'urgent',
          },
        ],
      },
    })

    render(
      <MemoryRouter>
        <EmployeesPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Documents à renouveler — 1')).toBeInTheDocument()
  })
})
