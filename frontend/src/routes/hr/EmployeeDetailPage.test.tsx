import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { mockFetch } from '../../test/mockFetch'
import { EmployeeDetailPage } from './EmployeeDetailPage'

const EMPLOYEE = {
  id: 4,
  matricule: 'TEST-001',
  nom: 'Testeur',
  prenom: 'Ahmed',
  full_name: 'Ahmed Testeur',
  nom_arabe: null,
  prenom_arabe: null,
  date_naissance: null,
  lieu_naissance: null,
  date_embauche: '2024-01-15',
  date_sortie: null,
  motif_sortie: null,
  date_fin_periode_essai: null,
  email: null,
  telephone: null,
  ville: null,
  adresse: null,
  cin: null,
  cnss: null,
  type_contrat: null,
  categorie_professionnelle: null,
  salaire_base: null,
  salaire_net: null,
  notes: null,
  equipe: null,
  department_id: 1,
  department_nom: 'Direction',
  position_id: null,
  position_intitule: null,
  status_id: null,
  status_libelle: null,
  manager_id: null,
  manager_nom: null,
  emergency_contacts: [],
  probation_evaluations: [],
  documents: [
    {
      id: 3,
      type_document: 'Contrat',
      nom_fichier: 'contrat-ahmed.pdf',
      content_type: 'application/pdf',
      taille_octets: 51200,
      date_expiration: '2027-01-15',
      uploaded_by_email: 'rh@arihafroid.ma',
      created_at: '2026-09-05T00:00:00Z',
    },
  ],
  equipements: [],
}

describe('EmployeeDetailPage', () => {
  it('renders the fetched employee profile', async () => {
    mockFetch({
      '/api/employees/4': { body: EMPLOYEE },
      '/api/departments': { body: [] },
      '/api/positions': { body: [] },
      '/api/employee-statuses': { body: [] },
      '/api/employees': { body: [] },
      '/api/leave-balances': { body: [] },
      '/api/leave-requests': { body: [] },
      '/api/attendance/etat/resume': { body: null },
    })

    render(
      <MemoryRouter initialEntries={['/hr/collaborateurs/4']}>
        <Routes>
          <Route path="/hr/collaborateurs/:id" element={<EmployeeDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('Ahmed Testeur')).toBeInTheDocument()
  })

  it('lists uploaded documents on the Documents tab', async () => {
    mockFetch({
      '/api/employees/4': { body: EMPLOYEE },
      '/api/departments': { body: [] },
      '/api/positions': { body: [] },
      '/api/employee-statuses': { body: [] },
      '/api/employees': { body: [] },
      '/api/leave-balances': { body: [] },
      '/api/leave-requests': { body: [] },
      '/api/attendance/etat/resume': { body: null },
    })

    render(
      <MemoryRouter initialEntries={['/hr/collaborateurs/4']}>
        <Routes>
          <Route path="/hr/collaborateurs/:id" element={<EmployeeDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText('Ahmed Testeur')
    await userEvent.click(screen.getByText('Documents'))

    expect(await screen.findByText('contrat-ahmed.pdf')).toBeInTheDocument()
  })

  it('blocks the CDI download and opens the edit form when contract fields are missing', async () => {
    mockFetch({
      '/api/employees/4': { body: EMPLOYEE },
      '/api/departments': { body: [] },
      '/api/positions': { body: [] },
      '/api/employee-statuses': { body: [] },
      '/api/employees': { body: [] },
      '/api/leave-balances': { body: [] },
      '/api/leave-requests': { body: [] },
      '/api/attendance/etat/resume': { body: null },
    })
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)

    render(
      <MemoryRouter initialEntries={['/hr/collaborateurs/4']}>
        <Routes>
          <Route path="/hr/collaborateurs/:id" element={<EmployeeDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText('Ahmed Testeur')
    await userEvent.click(screen.getByText('Télécharger le contrat CDI'))

    expect(openSpy).not.toHaveBeenCalled()
    expect(
      await screen.findByText(/Complétez ces champs avant de télécharger le contrat CDI/),
    ).toBeInTheDocument()
    // Dropped straight into the edit form on the Infos tab.
    expect(screen.getByText('Enregistrer')).toBeInTheDocument()

    openSpy.mockRestore()
  })

  it('downloads the CDI directly once every contract field is already filled in', async () => {
    const complete = {
      ...EMPLOYEE,
      cin: 'BE123456',
      date_naissance: '1990-01-01',
      lieu_naissance: 'Casablanca',
      adresse: '12 Rue Test',
      salaire_net: '5000',
    }
    mockFetch({
      '/api/employees/4': { body: complete },
      '/api/departments': { body: [] },
      '/api/positions': { body: [] },
      '/api/employee-statuses': { body: [] },
      '/api/employees': { body: [] },
      '/api/leave-balances': { body: [] },
      '/api/leave-requests': { body: [] },
      '/api/attendance/etat/resume': { body: null },
    })
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)

    render(
      <MemoryRouter initialEntries={['/hr/collaborateurs/4']}>
        <Routes>
          <Route path="/hr/collaborateurs/:id" element={<EmployeeDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText('Ahmed Testeur')
    await userEvent.click(screen.getByText('Télécharger le contrat CDI'))

    expect(openSpy).toHaveBeenCalledWith('/api/employees/4/contrat-cdi', '_blank')
    expect(screen.queryByText('Enregistrer')).not.toBeInTheDocument()

    openSpy.mockRestore()
  })

  it('keeps a deactivated département/poste selected (labeled) instead of showing blank', async () => {
    const employeeWithInactiveDept = {
      ...EMPLOYEE,
      department_id: 9,
      department_nom: 'Ancien département',
      position_id: 5,
      position_intitule: 'Ancien poste',
    }
    mockFetch({
      '/api/employees/4': { body: employeeWithInactiveDept },
      '/api/departments': {
        body: [
          {
            id: 9,
            nom: 'Ancien département',
            description: null,
            leave_responsable_employee_id: null,
            is_active: false,
          },
        ],
      },
      '/api/positions': {
        body: [{ id: 5, intitule: 'Ancien poste', department_id: 9, is_active: false }],
      },
      '/api/employee-statuses': { body: [] },
      '/api/employees': { body: [] },
      '/api/leave-balances': { body: [] },
      '/api/leave-requests': { body: [] },
      '/api/attendance/etat/resume': { body: null },
    })

    const { container } = render(
      <MemoryRouter initialEntries={['/hr/collaborateurs/4']}>
        <Routes>
          <Route path="/hr/collaborateurs/:id" element={<EmployeeDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText('Ahmed Testeur')
    await userEvent.click(screen.getByText('Modifier'))

    const deptSelect = container.querySelector('select') as HTMLSelectElement
    expect(deptSelect.value).toBe('9')
    expect(screen.getByText('Ancien département (inactif)')).toBeInTheDocument()
    expect(screen.getByText('Ancien poste (inactif)')).toBeInTheDocument()
  })

  it('shows the solde and leave request history on the Congés tab', async () => {
    mockFetch({
      '/api/employees/4': { body: EMPLOYEE },
      '/api/departments': { body: [] },
      '/api/positions': { body: [] },
      '/api/employee-statuses': { body: [] },
      '/api/employees': { body: [] },
      '/api/leave-balances': {
        body: [
          {
            employee_id: 4,
            leave_type_id: 1,
            leave_type_libelle: 'Congé payé',
            annee: 2026,
            jours_acquis: '18.0',
            jours_pris: '5.0',
            solde: '13.0',
          },
        ],
      },
      '/api/leave-requests': {
        body: [
          {
            id: 8,
            employee_id: 4,
            employee_nom: 'Ahmed Testeur',
            leave_type_id: 1,
            leave_type_libelle: 'Congé payé',
            has_certificate: true,
            date_debut: '2026-09-07',
            date_fin: '2026-09-11',
            nb_jours: '5.0',
            commentaire: null,
            status: 'approved',
            submitted_by_user_id: 1,
            decided_by_user_id: 1,
            decision_comment: null,
            decided_at: '2026-09-06T00:00:00Z',
            created_at: '2026-09-05T00:00:00Z',
          },
        ],
      },
      '/api/attendance/etat/resume': { body: null },
    })

    render(
      <MemoryRouter initialEntries={['/hr/collaborateurs/4']}>
        <Routes>
          <Route path="/hr/collaborateurs/:id" element={<EmployeeDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText('Ahmed Testeur')
    await userEvent.click(screen.getByText('Congés'))

    expect(await screen.findByText('13.0 j')).toBeInTheDocument()
    expect(screen.getAllByText('Congé payé').length).toBeGreaterThan(0)
    expect(screen.getByText('Certificat')).toBeInTheDocument()
  })

  it('shows the monthly summary on the Présence tab', async () => {
    mockFetch({
      '/api/employees/4': { body: EMPLOYEE },
      '/api/departments': { body: [] },
      '/api/positions': { body: [] },
      '/api/employee-statuses': { body: [] },
      '/api/employees': { body: [] },
      '/api/leave-balances': { body: [] },
      '/api/leave-requests': { body: [] },
      '/api/attendance/etat/resume': {
        body: {
          employee_id: 4,
          mois: 9,
          annee: 2026,
          jours_ouvres_mois: '25.0',
          jours_travailles: '20.0',
          conge_paye: '5.0',
          recuperation: '0.0',
          conge_exceptionnel: '0.0',
          absence_maladie: '0.0',
          conge_sans_solde: '0.0',
          absence: '0.0',
          mission: 2,
          jours_non_travailles: '5.0',
        },
      },
    })

    render(
      <MemoryRouter initialEntries={['/hr/collaborateurs/4']}>
        <Routes>
          <Route path="/hr/collaborateurs/:id" element={<EmployeeDetailPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText('Ahmed Testeur')
    await userEvent.click(screen.getByRole('button', { name: 'Présence' }))

    expect(await screen.findByText('20.0 j')).toBeInTheDocument()
    expect(screen.getByText('sur 25.0 j ouvrés')).toBeInTheDocument()
    expect(screen.getByText('2 j')).toBeInTheDocument()
  })
})
