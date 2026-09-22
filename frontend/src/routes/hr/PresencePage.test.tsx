import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { mockFetch } from '../../test/mockFetch'
import { PresencePage } from './PresencePage'

const CODES = [
  {
    id: 1,
    libelle: 'Présent',
    code_court: 'P',
    couleur: '#43A047',
    compte_absence: false,
    is_active: true,
  },
  {
    id: 2,
    libelle: 'Absence non justifiée',
    code_court: 'A',
    couleur: '#E53935',
    compte_absence: true,
    is_active: true,
  },
]

const PREVIEW = {
  token: 'tok-123',
  columns: ['Nom', '01', '02'],
  sample_rows: [{ Nom: 'Sara Alami', '01': 'PRESENT', '02': 'P' }],
  guessed_identifier_column: 'Nom',
  guessed_day_columns: ['01', '02'],
  nb_rows: 1,
  unmapped_values: ['PRESENT'],
}

describe('PresencePage', () => {
  it('shows both export buttons pointing at the right endpoints', async () => {
    mockFetch({
      '/api/attendance/codes': { body: CODES },
      '/api/attendance/imports': { body: [] },
    })

    render(<PresencePage />)

    const monthly = await screen.findByRole('link', { name: 'Exporter en Excel' })
    expect(monthly.getAttribute('href')).toContain('/api/attendance/export?')

    const detail = screen.getByRole('link', { name: 'Détail journalier' })
    expect(detail.getAttribute('href')).toContain('/api/attendance/export/detail?')
  })

  it('lets HR map an unrecognized pointeuse value to a code before confirming', async () => {
    let importedBody: Record<string, unknown> | null = null
    mockFetch({
      '/api/attendance/codes': { body: CODES },
      '/api/attendance/imports': { body: [] },
      '/api/attendance/upload': { body: PREVIEW },
      '/api/attendance/import': (_path, init) => {
        importedBody = init?.body ? JSON.parse(init.body as string) : null
        return {
          body: {
            id: 1,
            nom_fichier: 'pointage.csv',
            mois: 9,
            annee: 2026,
            nb_lignes_importees: 1,
            nb_lignes_non_reconnues: 0,
            noms_non_reconnus: [],
          },
        }
      },
    })

    render(<PresencePage />)
    const user = userEvent.setup()

    const file = new File(['Nom,01,02\nSara Alami,PRESENT,P\n'], 'pointage.csv', {
      type: 'text/csv',
    })
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(fileInput, file)
    // jsdom doesn't always recognize a programmatically-set file input as
    // satisfying `required`, which silently blocks a real click-triggered
    // submit — fire the submit event directly instead.
    fireEvent.submit(document.querySelector('form') as HTMLFormElement)

    expect(await screen.findAllByText('PRESENT')).toHaveLength(2)
    expect(screen.getByText(/Valeurs non reconnues/)).toBeInTheDocument()

    const mappingSelect = screen
      .getAllByRole('combobox')
      .find((el) =>
        Array.from((el as HTMLSelectElement).options).some((o) =>
          o.textContent?.includes('Présent (P)'),
        ),
      ) as HTMLSelectElement
    await user.selectOptions(mappingSelect, '1')

    await user.click(screen.getByRole('button', { name: "Confirmer l'import" }))

    await waitFor(() => expect(importedBody).not.toBeNull())
    expect(importedBody!.code_map).toEqual({ PRESENT: 1 })
  })
})
