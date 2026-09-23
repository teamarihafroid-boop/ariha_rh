import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { mockFetch } from '../../test/mockFetch'
import { UsersPage } from './UsersPage'

const USERS = [
  {
    id: 1,
    email: 'rh@arihafroid.ma',
    role: 'hr' as const,
    employee_id: null,
    employee_nom: null,
    is_active: true,
    last_login_at: null,
    created_at: '2026-01-01T00:00:00Z',
  },
]

const AVAILABLE_EMPLOYEES = [{ id: 5, full_name: 'Karim Idrissi', department_id: null }]

describe('UsersPage', () => {
  it('lists existing accounts', async () => {
    mockFetch({
      '/api/users': { body: USERS },
      '/api/users/employees-sans-compte': { body: AVAILABLE_EMPLOYEES },
    })

    render(
      <MemoryRouter>
        <UsersPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('rh@arihafroid.ma')).toBeInTheDocument()
  })

  it('submits a create-account request with the entered fields', async () => {
    let capturedBody: Record<string, unknown> | null = null
    mockFetch({
      '/api/users': (_url, init) => {
        if (init?.method === 'POST') {
          capturedBody = JSON.parse(init.body as string) as Record<string, unknown>
          return { status: 201, body: { ...capturedBody, id: 2, employee_nom: 'Karim Idrissi' } }
        }
        return { body: USERS }
      },
      '/api/users/employees-sans-compte': { body: AVAILABLE_EMPLOYEES },
    })

    render(
      <MemoryRouter>
        <UsersPage />
      </MemoryRouter>,
    )
    await userEvent.click(await screen.findByText('Nouveau compte'))

    // Field/Label/Input in this codebase aren't htmlFor/id-linked, so query by
    // role+order instead of getByLabelText (matches the pattern already used
    // in CandidatesPage.test.tsx for the same reason).
    const [emailInput, passwordInput] = screen.getAllByRole('textbox')
    await userEvent.type(emailInput, 'karim@example.com')
    await userEvent.type(passwordInput, 'SuperSecret1')
    const [, employeeSelect] = screen.getAllByRole('combobox')
    await userEvent.selectOptions(employeeSelect, '5')
    await userEvent.click(screen.getByText('Créer'))

    expect(await screen.findByText('rh@arihafroid.ma')).toBeInTheDocument()
    expect(capturedBody).toMatchObject({
      email: 'karim@example.com',
      password: 'SuperSecret1',
      role: 'employee',
      employee_id: 5,
    })
  })

  it('pre-selects only collaborateurs not covered by a responsable congé, and creates the selected accounts', async () => {
    let bulkBody: Record<string, unknown> | null = null
    mockFetch({
      '/api/users': { body: USERS },
      '/api/users/employees-sans-compte': { body: AVAILABLE_EMPLOYEES },
      '/api/users/account-candidates': {
        body: [
          {
            id: 5,
            full_name: 'Karim Idrissi',
            matricule: null,
            department_nom: 'Technique',
            position_intitule: null,
            coverage_note:
              'Aucun responsable congé désigné pour ce département — accès individuel recommandé.',
            suggested_email: 'karim.idrissi@arihafroid.ma',
          },
          {
            id: 6,
            full_name: 'Omar Fassi',
            matricule: null,
            department_nom: 'Avec responsable',
            position_intitule: null,
            coverage_note:
              'Couvert par Nadia Chraibi (responsable congé) — compte non indispensable.',
            suggested_email: 'omar.fassi@arihafroid.ma',
          },
        ],
      },
      '/api/users/bulk': (_url, init) => {
        bulkBody = JSON.parse(init?.body as string) as Record<string, unknown>
        return {
          status: 201,
          body: {
            results: [
              {
                employee_id: 5,
                employee_nom: 'Karim Idrissi',
                user_id: 9,
                email: 'karim.idrissi@arihafroid.ma',
                password: 'Ab3xQ9rT2z',
                error: null,
              },
            ],
          },
        }
      },
    })

    render(
      <MemoryRouter>
        <UsersPage />
      </MemoryRouter>,
    )
    await userEvent.click(await screen.findByText('Créer des comptes en masse'))

    await screen.findByText('Karim Idrissi')
    // Omar is covered by a responsable, so his checkbox starts unchecked;
    // Karim's isn't covered, so his starts checked.
    const checkboxes = screen.getAllByRole('checkbox')
    expect(checkboxes[0]).toBeChecked()
    expect(checkboxes[1]).not.toBeChecked()
    expect(screen.getByText('1 sélectionné(s) sur 2')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /Créer 1 compte/ }))

    expect(await screen.findByText(/1 compte\(s\) créé/)).toBeInTheDocument()
    expect(screen.getByText('karim.idrissi@arihafroid.ma')).toBeInTheDocument()
    expect(screen.getByText('Ab3xQ9rT2z')).toBeInTheDocument()
    expect(bulkBody).toEqual({ items: [{ employee_id: 5 }] })
  })

  it('auto-opens the bulk-creation modal when arriving with autoOpenBulk navigation state', async () => {
    mockFetch({
      '/api/users': { body: USERS },
      '/api/users/employees-sans-compte': { body: AVAILABLE_EMPLOYEES },
      '/api/users/account-candidates': { body: [] },
    })

    render(
      <MemoryRouter
        initialEntries={[
          { pathname: '/hr/parametres/utilisateurs', state: { autoOpenBulk: true } },
        ]}
      >
        <UsersPage />
      </MemoryRouter>,
    )

    expect(
      await screen.findByText('Tous les collaborateurs ont déjà un compte.'),
    ).toBeInTheDocument()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })
})
