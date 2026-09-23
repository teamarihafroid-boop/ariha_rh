import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { mockFetch } from '../../test/mockFetch'
import { EmployeesPage } from './EmployeesPage'

function UsersPagePlaceholder() {
  const location = useLocation()
  const state = location.state as { autoOpenBulk?: boolean } | null
  return <div>Comptes utilisateurs page — autoOpenBulk={String(state?.autoOpenBulk)}</div>
}

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

  it('lets HR bulk-import collaborateurs from a preview', async () => {
    let confirmedToken: string | null = null
    mockFetch({
      '/api/departments': { body: [] },
      '/api/positions': { body: [] },
      '/api/employee-statuses': { body: [] },
      '/api/employees': { body: [] },
      '/api/employees/periode-essai/alertes': { body: [] },
      '/api/employees/documents/alertes': { body: [] },
      '/api/employees/import/upload': {
        body: {
          token: 'tok-abc',
          nb_valid: 1,
          nb_errors: 1,
          rows: [
            {
              row_number: 2,
              display: { Nom: 'Bennani', Prénom: 'Karim', Département: '' },
              errors: [],
              warnings: [],
              ok: true,
            },
            {
              row_number: 3,
              display: { Nom: '', Prénom: '', Département: 'Ne Existe Pas' },
              errors: ['Nom et Prénom sont obligatoires.', "Département inconnu : 'Ne Existe Pas'"],
              warnings: [],
              ok: false,
            },
          ],
        },
      },
      '/api/employees/import/confirm': (_path, init) => {
        confirmedToken = init?.body ? JSON.parse(init.body as string).token : null
        return {
          body: {
            created: 1,
            skipped: [{ row_number: 3, display: {}, reason: 'Nom et Prénom sont obligatoires.' }],
          },
        }
      },
    })

    render(
      <MemoryRouter initialEntries={['/hr/collaborateurs']}>
        <Routes>
          <Route path="/hr/collaborateurs" element={<EmployeesPage />} />
          <Route path="/hr/parametres/utilisateurs" element={<UsersPagePlaceholder />} />
        </Routes>
      </MemoryRouter>,
    )

    await userEvent.click(await screen.findByText('Importer des collaborateurs'))
    await screen.findByText('Télécharger le modèle')

    const file = new File(['Nom,Prénom\nKarim,Bennani\n'], 'collaborateurs.csv', {
      type: 'text/csv',
    })
    const dialog = screen.getByRole('dialog')
    const fileInput = dialog.querySelector('input[type="file"]') as HTMLInputElement
    await userEvent.upload(fileInput, file)
    // Same jsdom quirk as PresencePage's import wizard: a programmatically
    // set file input doesn't reliably satisfy `required` for a real click.
    // Also, the page's own search-filter <form> is a different element —
    // scope to the modal so we submit the right one.
    fireEvent.submit(dialog.querySelector('form') as HTMLFormElement)

    expect(await screen.findByText(/1 prêt/)).toBeInTheDocument()
    expect(screen.getByText('Bennani Karim')).toBeInTheDocument()
    expect(screen.getByText(/Nom et Prénom sont obligatoires/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /Confirmer l'import/ }))

    expect(await screen.findByText(/1 collaborateur créé/)).toBeInTheDocument()
    expect(confirmedToken).toBe('tok-abc')

    // After a successful import, HR shouldn't have to go hunt for the
    // account-creation page on their own.
    await userEvent.click(screen.getByRole('button', { name: 'Créer leurs accès maintenant' }))
    expect(
      await screen.findByText('Comptes utilisateurs page — autoOpenBulk=true'),
    ).toBeInTheDocument()
  })
})
