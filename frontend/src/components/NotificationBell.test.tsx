import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AuthProvider } from '../lib/auth-context'
import { mockFetch } from '../test/mockFetch'
import { NotificationBell } from './NotificationBell'

function renderBell() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <NotificationBell />
      </AuthProvider>
    </MemoryRouter>,
  )
}

const NOTIFICATION = {
  id: 1,
  type: 'leave_pending' as const,
  title: 'Nouvelle demande de congé à traiter',
  body: 'Sara Alami a soumis une demande de congé du 2026-09-20 au 2026-09-22.',
  related_entity_type: 'leave_request',
  related_entity_id: 7,
  is_read: false,
  created_at: '2026-09-15T10:00:00Z',
}

describe('NotificationBell', () => {
  it('merges real notifications with computed HR alerts for an HR user', async () => {
    mockFetch({
      '/api/auth/me': {
        body: { id: 1, email: 'rh@arihafroid.ma', role: 'hr', employee_id: null },
      },
      '/api/notifications': { body: [NOTIFICATION] },
      '/api/employees/periode-essai/alertes': {
        body: [
          {
            employee_id: 4,
            employee_nom: 'Ahmed Testeur',
            date_fin_periode_essai: '2026-09-25',
            urgence: 'semaine',
            a_evaluation_complete: false,
          },
        ],
      },
      '/api/employees/documents/alertes': { body: [] },
      '/api/recruitment/applications/stagnantes': { body: [] },
    })

    renderBell()
    await userEvent.click(await screen.findByLabelText('Notifications'))

    expect(await screen.findByText('Nouvelle demande de congé à traiter')).toBeInTheDocument()
    expect(await screen.findByText("Période d'essai — Ahmed Testeur")).toBeInTheDocument()
  })

  it('only fetches real notifications for a non-HR user, no HR-only alert calls', async () => {
    mockFetch({
      '/api/auth/me': {
        body: { id: 2, email: 'dg@arihafroid.ma', role: 'dg', employee_id: null },
      },
      '/api/notifications': { body: [NOTIFICATION] },
      // Deliberately no mocks for the HR-only alert endpoints — if the bell
      // called them anyway it would 404, surface as an error banner, and
      // the notification below would never render.
    })

    renderBell()
    await userEvent.click(await screen.findByLabelText('Notifications'))

    expect(await screen.findByText('Nouvelle demande de congé à traiter')).toBeInTheDocument()
  })
})
