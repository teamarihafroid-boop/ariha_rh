import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { mockFetch } from '../../test/mockFetch'
import { DepartmentsPositionsPage } from './DepartmentsPositionsPage'

const DEPARTMENT = {
  id: 1,
  nom: 'Technique',
  description: 'Maintenance et froid industriel',
  leave_responsable_employee_id: null,
  is_active: true,
}

const POSITION = {
  id: 1,
  intitule: 'Technicien',
  department_id: 1,
  is_active: true,
}

describe('DepartmentsPositionsPage', () => {
  it('lists departments and positions, showing the poste linked to its département', async () => {
    mockFetch({
      '/api/departments': { body: [DEPARTMENT] },
      '/api/positions': { body: [POSITION] },
    })

    render(<DepartmentsPositionsPage />)

    expect((await screen.findAllByText('Technique')).length).toBeGreaterThan(0)
    expect(screen.getByText('Technicien')).toBeInTheDocument()
  })

  it('creates a new department', async () => {
    const postSpy = vi.fn()
    mockFetch({
      '/api/departments': (_path, init) => {
        if (init?.method === 'POST') {
          postSpy(JSON.parse(init.body as string))
          return { status: 201, body: { ...DEPARTMENT, id: 2, nom: 'Qualité' } }
        }
        return { body: [DEPARTMENT] }
      },
      '/api/positions': { body: [POSITION] },
    })

    render(<DepartmentsPositionsPage />)
    await screen.findAllByText('Technique')

    const nameInputs = screen.getAllByRole('textbox')
    await userEvent.type(nameInputs[0], 'Qualité')
    await userEvent.click(screen.getAllByText('Ajouter')[0])

    await vi.waitFor(() =>
      expect(postSpy).toHaveBeenCalledWith({ nom: 'Qualité', description: null }),
    )
  })

  it('deactivates a position', async () => {
    const putSpy = vi.fn()
    mockFetch({
      '/api/departments': { body: [DEPARTMENT] },
      '/api/positions': { body: [POSITION] },
      '/api/positions/1': (_path, init) => {
        putSpy(JSON.parse(init?.body as string))
        return { body: { ...POSITION, is_active: false } }
      },
    })

    render(<DepartmentsPositionsPage />)
    const positionCell = await screen.findByText('Technicien')
    const positionRow = positionCell.closest('tr') as HTMLTableRowElement

    await userEvent.click(within(positionRow).getByText('Désactiver'))

    await vi.waitFor(() =>
      expect(putSpy).toHaveBeenCalledWith({
        intitule: 'Technicien',
        department_id: 1,
        is_active: false,
      }),
    )
  })
})
