import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AuthProvider } from '../../lib/auth-context'
import { mockFetch } from '../../test/mockFetch'
import { MyLeave } from './MyLeave'

const BASE_HANDLERS = {
  '/api/leave-balances': { body: [] },
  '/api/leave-requests': { body: [] },
  '/api/leave-types': {
    body: [{ id: 1, libelle: 'Congé payé', couleur: '#0288D1', deduit_du_solde: true }],
  },
}

function renderMyLeave() {
  return render(
    <AuthProvider>
      <MyLeave />
    </AuthProvider>,
  )
}

describe('MyLeave', () => {
  it('shows a colleague picker when the current user is the department leave-responsable', async () => {
    mockFetch({
      ...BASE_HANDLERS,
      '/api/auth/me': {
        body: {
          id: 5,
          email: 'responsable@arihafroid.ma',
          role: 'employee',
          employee_id: 10,
          department_id: 5,
        },
      },
      '/api/departments': {
        body: [
          { id: 5, nom: 'Avec responsable', description: null, leave_responsable_employee_id: 10 },
        ],
      },
      '/api/employees': {
        body: [{ id: 11, full_name: 'Omar Fassi', department_id: 5 }],
      },
    })

    renderMyLeave()

    expect(await screen.findByText('Pour qui ?')).toBeInTheDocument()
    expect(await screen.findByText('Omar Fassi')).toBeInTheDocument()
  })

  it('hides the colleague picker for a regular employee', async () => {
    mockFetch({
      ...BASE_HANDLERS,
      '/api/auth/me': {
        body: {
          id: 6,
          email: 'employee@arihafroid.ma',
          role: 'employee',
          employee_id: 12,
          department_id: 5,
        },
      },
      '/api/departments': {
        body: [
          { id: 5, nom: 'Avec responsable', description: null, leave_responsable_employee_id: 10 },
        ],
      },
    })

    renderMyLeave()

    expect(await screen.findByText('Nouvelle demande')).toBeInTheDocument()
    expect(screen.queryByText('Pour qui ?')).not.toBeInTheDocument()
  })
})
