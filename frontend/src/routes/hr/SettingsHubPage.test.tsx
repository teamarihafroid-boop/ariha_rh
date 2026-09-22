import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { SettingsHubPage } from './SettingsHubPage'

describe('SettingsHubPage', () => {
  it('lists all six settings areas as tiles and navigates on click', async () => {
    render(
      <MemoryRouter initialEntries={['/hr/parametres']}>
        <Routes>
          <Route path="/hr/parametres" element={<SettingsHubPage />} />
          <Route
            path="/hr/parametres/utilisateurs"
            element={<div>Comptes utilisateurs page</div>}
          />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('Départements & Postes')).toBeInTheDocument()
    expect(screen.getByText('Responsables congés')).toBeInTheDocument()
    expect(screen.getByText('Types de congé')).toBeInTheDocument()
    expect(screen.getByText('Jours fériés')).toBeInTheDocument()
    expect(screen.getByText('Codes de présence')).toBeInTheDocument()
    expect(screen.getByText('Comptes utilisateurs')).toBeInTheDocument()

    await userEvent.click(screen.getByText('Comptes utilisateurs'))
    expect(await screen.findByText('Comptes utilisateurs page')).toBeInTheDocument()
  })
})
