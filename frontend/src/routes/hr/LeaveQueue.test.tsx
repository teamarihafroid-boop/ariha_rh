import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { mockFetch } from '../../test/mockFetch'
import { LeaveQueue } from './LeaveQueue'

const PENDING_REQUEST = {
  id: 42,
  employee_id: 1,
  employee_nom: 'Sara Alami',
  leave_type_id: 1,
  leave_type_libelle: 'Congé payé',
  date_debut: '2026-09-07',
  date_fin: '2026-09-11',
  nb_jours: '5.0',
  commentaire: null,
  status: 'pending',
  submitted_by_user_id: 3,
  decided_by_user_id: null,
  decision_comment: null,
  decided_at: null,
  created_at: '2026-08-28T00:00:00Z',
}

describe('LeaveQueue (HR)', () => {
  it('renders the pending queue and approves a request against the right endpoint', async () => {
    let approveCalled: { path: string; body: unknown } | null = null
    mockFetch({
      '/api/leave-requests': { body: [PENDING_REQUEST] },
      '/api/leave-requests/42/approve': (path, init) => {
        approveCalled = { path, body: init?.body ? JSON.parse(init.body as string) : null }
        return { body: { ...PENDING_REQUEST, status: 'approved' } }
      },
    })

    render(<LeaveQueue />)
    const user = userEvent.setup()

    await screen.findByText('Sara Alami')
    await user.click(screen.getByRole('button', { name: 'Approuver' }))

    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Approuver' }))

    await waitFor(() => expect(approveCalled).not.toBeNull())
    expect(approveCalled!.path).toBe('/api/leave-requests/42/approve')
  })

  it('requires a comment before rejecting', async () => {
    const rejectFn = vi.fn()
    mockFetch({
      '/api/leave-requests': { body: [PENDING_REQUEST] },
      '/api/leave-requests/42/reject': () => {
        rejectFn()
        return { body: { ...PENDING_REQUEST, status: 'rejected' } }
      },
    })

    render(<LeaveQueue />)
    const user = userEvent.setup()

    await screen.findByText('Sara Alami')
    await user.click(screen.getByRole('button', { name: 'Refuser' }))

    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Refuser' }))

    expect(await screen.findByText(/motif est obligatoire/i)).toBeInTheDocument()
    expect(rejectFn).not.toHaveBeenCalled()
  })
})
