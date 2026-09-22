import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { mockFetch } from '../../test/mockFetch'
import { LeaveQueue } from './LeaveQueue'

function renderLeaveQueue(initialEntries: string[] = ['/hr/demandes']) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <LeaveQueue />
    </MemoryRouter>,
  )
}

const PENDING_REQUEST = {
  id: 42,
  employee_id: 1,
  employee_nom: 'Sara Alami',
  leave_type_id: 1,
  leave_type_libelle: 'Congé payé',
  has_certificate: true,
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
      '/api/employees': { body: [] },
      '/api/leave-types': { body: [] },
      '/api/leave-requests/42/approve': (path, init) => {
        approveCalled = { path, body: init?.body ? JSON.parse(init.body as string) : null }
        return { body: { ...PENDING_REQUEST, status: 'approved' } }
      },
    })

    renderLeaveQueue()
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
      '/api/employees': { body: [] },
      '/api/leave-types': { body: [] },
      '/api/leave-requests/42/reject': () => {
        rejectFn()
        return { body: { ...PENDING_REQUEST, status: 'rejected' } }
      },
    })

    renderLeaveQueue()
    const user = userEvent.setup()

    await screen.findByText('Sara Alami')
    await user.click(screen.getByRole('button', { name: 'Refuser' }))

    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Refuser' }))

    expect(await screen.findByText(/motif est obligatoire/i)).toBeInTheDocument()
    expect(rejectFn).not.toHaveBeenCalled()
  })

  it('hides the certificate link for a leave type without one', async () => {
    const approvedNoCertificate = {
      ...PENDING_REQUEST,
      id: 43,
      status: 'approved',
      leave_type_libelle: 'Maladie',
      has_certificate: false,
    }
    mockFetch({
      '/api/leave-requests': { body: [approvedNoCertificate] },
      '/api/employees': { body: [] },
      '/api/leave-types': { body: [] },
    })

    renderLeaveQueue()
    await screen.findByText('Sara Alami')

    expect(screen.queryByText('Certificat')).not.toBeInTheDocument()
  })

  it('lets HR create a leave request for any collaborateur, including HR-only types', async () => {
    const employees = [
      {
        id: 7,
        full_name: 'Nadia Chraibi',
        matricule: null,
        department_id: null,
        department_nom: null,
        position_intitule: null,
        status_libelle: null,
        status_couleur: null,
      },
    ]
    const leaveTypes = [
      {
        id: 5,
        libelle: 'Exceptionnel (mariage/naissance/décès)',
        couleur: '#546E7A',
        deduit_du_solde: false,
        accrual_legal: false,
        is_active: true,
        code_court: 'EXC',
        employee_requestable: false,
        certificate_kind: null,
      },
    ]
    let createCalled: { body: Record<string, unknown> } | null = null
    mockFetch({
      '/api/employees': { body: employees },
      '/api/leave-types': { body: leaveTypes },
      '/api/leave-requests': (_path, init) => {
        if (init?.method === 'POST') {
          createCalled = { body: init.body ? JSON.parse(init.body as string) : {} }
          return { status: 201, body: { ...PENDING_REQUEST, id: 99 } }
        }
        return { body: [] }
      },
    })

    const { container } = renderLeaveQueue()
    const user = userEvent.setup()

    await user.click(screen.getByRole('button', { name: 'Nouvelle demande' }))
    await screen.findByText('Nouvelle demande pour un collaborateur')

    // Unlike the employee self-service form, HR's picker isn't filtered to
    // employee_requestable types — "Exceptionnel" must still be selectable.
    expect(screen.getByRole('option', { name: /Exceptionnel/ })).toBeInTheDocument()

    const selects = screen.getAllByRole('combobox')
    await user.selectOptions(selects[0], '7')

    const dateInputs = container.querySelectorAll('input[type="date"]')
    await user.type(dateInputs[0], '2026-10-01')
    await user.type(dateInputs[1], '2026-10-02')
    await user.click(screen.getByRole('button', { name: 'Créer la demande' }))

    await waitFor(() => expect(createCalled).not.toBeNull())
    expect(createCalled!.body.employee_id).toBe(7)
    expect(createCalled!.body.leave_type_id).toBe(5)
  })

  it('filters to one collaborateur and defaults to full history when linked with ?employee_id=', async () => {
    let requestedPath = ''
    mockFetch({
      '/api/employees': { body: [] },
      '/api/leave-types': { body: [] },
      '/api/leave-requests': (path) => {
        requestedPath = path
        return { body: [{ ...PENDING_REQUEST, status: 'approved' }] }
      },
    })

    const { container } = renderLeaveQueue(['/hr/demandes?employee_id=1'])
    await screen.findByRole('button', { name: /Retirer le filtre/ })
    expect(container.textContent).toContain('Filtré pour Sara Alami')

    await waitFor(() => expect(requestedPath).toContain('employee_id=1'))
    // Defaults to "Historique complet", not just pending, when arriving filtered.
    expect(requestedPath).not.toContain('status=')
  })
})
