import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { mockFetch } from '../../test/mockFetch'
import { OrgChartPage } from './OrgChartPage'

describe('OrgChartPage', () => {
  it('renders departments and their collaborators', async () => {
    mockFetch({
      '/api/employees/orgchart': {
        body: {
          direction: [],
          departements: [
            {
              department_id: 1,
              department_nom: 'Direction',
              collaborateurs: [
                {
                  id: 1,
                  full_name: 'Sara Alami',
                  department_id: 1,
                  department_nom: 'Direction',
                  position_intitule: null,
                  niveau: 'employe',
                  rapporte_a: null,
                  enfants: [],
                },
              ],
              postes_ouverts: [],
            },
          ],
        },
      },
    })

    render(<OrgChartPage />)

    expect(await screen.findByText('Sara Alami')).toBeInTheDocument()
    expect(screen.getByText('Direction')).toBeInTheDocument()
  })
})
