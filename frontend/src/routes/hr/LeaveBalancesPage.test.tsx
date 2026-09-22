import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { mockFetch } from '../../test/mockFetch'
import { LeaveBalancesPage } from './LeaveBalancesPage'

function renderPage() {
  return render(
    <MemoryRouter>
      <LeaveBalancesPage />
    </MemoryRouter>,
  )
}

const EMPLOYEES = [
  {
    id: 1,
    full_name: 'Sara Alami',
    matricule: 'M-001',
    department_id: 1,
    department_nom: 'Technique',
    position_intitule: 'Technicienne',
    status_libelle: 'Actif',
    status_couleur: '#43A047',
  },
  {
    id: 2,
    full_name: 'Omar Fassi',
    matricule: 'M-002',
    department_id: 2,
    department_nom: 'Commercial',
    position_intitule: 'Commercial',
    status_libelle: 'Actif',
    status_couleur: '#43A047',
  },
]

const LEAVE_TYPES = [
  {
    id: 1,
    libelle: 'Congé payé',
    couleur: '#0288D1',
    deduit_du_solde: true,
    accrual_legal: true,
    is_active: true,
    code_court: 'CP',
    employee_requestable: true,
    certificate_kind: 'conge_paye',
  },
  {
    id: 2,
    libelle: 'Récupération',
    couleur: '#43A047',
    deduit_du_solde: true,
    accrual_legal: false,
    is_active: true,
    code_court: 'REC',
    employee_requestable: true,
    certificate_kind: 'recuperation',
  },
  {
    id: 3,
    libelle: 'Sans solde',
    couleur: '#8E24AA',
    deduit_du_solde: false,
    accrual_legal: false,
    is_active: true,
    code_court: 'SS',
    employee_requestable: true,
    certificate_kind: null,
  },
]

const BALANCES = [
  {
    employee_id: 1,
    leave_type_id: 1,
    leave_type_libelle: 'Congé payé',
    annee: 2026,
    jours_acquis: '18.0',
    jours_pris: '5.0',
    solde: '13.0',
  },
  {
    employee_id: 2,
    leave_type_id: 2,
    leave_type_libelle: 'Récupération',
    annee: 2026,
    jours_acquis: '3.0',
    jours_pris: '1.0',
    solde: '2.0',
  },
]

describe('LeaveBalancesPage', () => {
  it('shows every collaborateur with a solde column per deduit_du_solde leave type only', async () => {
    mockFetch({
      '/api/employees': { body: EMPLOYEES },
      '/api/leave-types': { body: LEAVE_TYPES },
      '/api/leave-balances': { body: BALANCES },
    })

    renderPage()

    expect(await screen.findByText('Sara Alami')).toBeInTheDocument()
    expect(screen.getByText('Omar Fassi')).toBeInTheDocument()

    // "Sans solde" isn't deduit_du_solde, so it shouldn't get a column.
    expect(screen.queryByText('Sans solde')).not.toBeInTheDocument()
    expect(screen.getByText('Congé payé')).toBeInTheDocument()
    expect(screen.getByText('Récupération')).toBeInTheDocument()

    expect(screen.getByText('13.0 j')).toBeInTheDocument()
    expect(screen.getByText('2.0 j')).toBeInTheDocument()
  })

  it('filters the list with the search box', async () => {
    mockFetch({
      '/api/employees': { body: EMPLOYEES },
      '/api/leave-types': { body: LEAVE_TYPES },
      '/api/leave-balances': { body: BALANCES },
    })

    renderPage()
    await screen.findByText('Sara Alami')

    await userEvent.type(screen.getByPlaceholderText('Nom, matricule, département…'), 'Omar')

    expect(screen.queryByText('Sara Alami')).not.toBeInTheDocument()
    expect(screen.getByText('Omar Fassi')).toBeInTheDocument()
  })
})
