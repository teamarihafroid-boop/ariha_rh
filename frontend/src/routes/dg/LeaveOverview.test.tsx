import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { mockFetch } from '../../test/mockFetch'
import { LeaveOverview } from './LeaveOverview'

describe('LeaveOverview (DG)', () => {
  it('renders requests read-only with no action buttons', async () => {
    mockFetch({
      '/api/leave-requests': {
        body: [
          {
            id: 1,
            employee_id: 1,
            employee_nom: 'Sara Alami',
            leave_type_id: 1,
            leave_type_libelle: 'Congé payé',
            date_debut: '2026-09-07',
            date_fin: '2026-09-11',
            nb_jours: '5.0',
            commentaire: null,
            status: 'pending',
            submitted_by_user_id: 1,
            decided_by_user_id: null,
            decision_comment: null,
            decided_at: null,
            created_at: '2026-08-28T00:00:00Z',
          },
        ],
      },
      '/api/leave-calendar': { body: { conges: [], jours_feries: [] } },
    })

    render(<LeaveOverview />)

    expect(await screen.findByText('Sara Alami')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /approuver/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /refuser/i })).not.toBeInTheDocument()
  })
})
