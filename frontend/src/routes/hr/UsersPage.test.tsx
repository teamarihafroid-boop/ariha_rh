import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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

    render(<UsersPage />)

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

    render(<UsersPage />)
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
})
