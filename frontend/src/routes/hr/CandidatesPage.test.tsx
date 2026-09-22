import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { mockFetch } from '../../test/mockFetch'
import { CandidatesPage } from './CandidatesPage'

const JOB_OFFER = {
  id: 7,
  titre: 'Technicien froid',
  ville: null,
  department_id: null,
  department_nom: 'Technique',
  position_id: null,
  position_intitule: null,
  status_id: 1,
  status_libelle: 'Ouverte',
  description: null,
  responsable: null,
  date_creation: '2026-01-01T00:00:00Z',
  date_cloture: null,
}

const CANDIDATE = {
  id: 1,
  nom_complet: 'Karim Idrissi',
  telephone: '0600112233',
  email: 'karim@example.com',
  ville: 'Rabat',
  annees_experience: null,
  experience_resume: null,
  competences: null,
  diplomes: null,
  langues: null,
  favori: false,
  notes: null,
  employee_id: null,
  date_ajout: '2026-09-01T00:00:00Z',
  attachments: [
    {
      id: 5,
      type_document: 'CV',
      nom_fichier: 'cv-karim.pdf',
      content_type: 'application/pdf',
      taille_octets: 20480,
      uploaded_by_email: 'rh@arihafroid.ma',
      created_at: '2026-09-02T00:00:00Z',
    },
  ],
  applications: [],
}

describe('CandidatesPage', () => {
  it('lists candidates returned by the API', async () => {
    mockFetch({
      '/api/recruitment/candidates': { body: [CANDIDATE] },
      '/api/recruitment/job-offers': { body: [JOB_OFFER] },
    })

    render(
      <MemoryRouter>
        <CandidatesPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Karim Idrissi')).toBeInTheDocument()
  })

  it('shows existing attachments when editing a candidate', async () => {
    mockFetch({
      '/api/recruitment/candidates': { body: [CANDIDATE] },
      '/api/recruitment/job-offers': { body: [JOB_OFFER] },
    })

    render(
      <MemoryRouter>
        <CandidatesPage />
      </MemoryRouter>,
    )
    await userEvent.click(await screen.findByText('Modifier'))

    expect(await screen.findByText('CV — cv-karim.pdf')).toBeInTheDocument()
  })

  it('pre-fills the create form from an extracted CV', async () => {
    mockFetch({
      '/api/recruitment/candidates': { body: [] },
      '/api/recruitment/job-offers': { body: [JOB_OFFER] },
      '/api/recruitment/candidates/extract-cv': {
        body: {
          nom_complet: 'Nadia Chraibi',
          telephone: null,
          email: 'nadia@example.com',
          ville: null,
          experience_resume: null,
          competences: null,
          diplomes: null,
          langues: null,
        },
      },
    })

    const { container } = render(
      <MemoryRouter>
        <CandidatesPage />
      </MemoryRouter>,
    )
    await userEvent.click(await screen.findByText('Nouveau candidat'))

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['cv content'], 'cv.pdf', { type: 'application/pdf' })
    await userEvent.upload(fileInput, file)
    await userEvent.click(screen.getByText('Extraire les infos'))

    expect(await screen.findByDisplayValue('Nadia Chraibi')).toBeInTheDocument()
    expect(screen.getByDisplayValue('nadia@example.com')).toBeInTheDocument()
  })

  it('still works when the job-offers fetch fails — no page-wide error', async () => {
    mockFetch({
      '/api/recruitment/candidates': { body: [CANDIDATE] },
      '/api/recruitment/job-offers': { status: 500, body: { detail: 'boom' } },
    })

    render(
      <MemoryRouter>
        <CandidatesPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Karim Idrissi')).toBeInTheDocument()
    expect(screen.queryByText('boom')).not.toBeInTheDocument()
  })

  it('links the new candidate to the chosen offer on create', async () => {
    const postSpy = vi.fn()
    mockFetch({
      '/api/recruitment/candidates': (_path, init) => {
        if (init?.method === 'POST') {
          postSpy(JSON.parse(init.body as string))
          return { status: 201, body: { candidate: { ...CANDIDATE, id: 99 }, duplicates: [] } }
        }
        return { body: [] }
      },
      '/api/recruitment/job-offers': { body: [JOB_OFFER] },
      '/api/recruitment/applications': (_path, init) => {
        postSpy({ application: JSON.parse(init?.body as string) })
        return { status: 201, body: {} }
      },
    })

    const { container } = render(
      <MemoryRouter>
        <CandidatesPage />
      </MemoryRouter>,
    )
    await userEvent.click(await screen.findByText('Nouveau candidat'))
    await userEvent.type(
      container.querySelector('input[required]') as HTMLInputElement,
      'Test Candidat',
    )
    await userEvent.selectOptions(container.querySelector('select') as HTMLSelectElement, '7')
    await userEvent.click(screen.getByText('Créer'))

    await vi.waitFor(() =>
      expect(postSpy).toHaveBeenCalledWith({
        application: { candidate_id: 99, job_offer_id: 7, responsable: null },
      }),
    )
  })

  it('links a hired candidate straight to their employee fiche', async () => {
    mockFetch({
      '/api/recruitment/candidates': { body: [{ ...CANDIDATE, employee_id: 42 }] },
      '/api/recruitment/job-offers': { body: [] },
    })

    render(
      <MemoryRouter initialEntries={['/hr/recrutement/candidats']}>
        <Routes>
          <Route path="/hr/recrutement/candidats" element={<CandidatesPage />} />
          <Route path="/hr/collaborateurs/:id" element={<div>Fiche de l'employé 42</div>} />
        </Routes>
      </MemoryRouter>,
    )

    await userEvent.click(await screen.findByText('Embauché — voir la fiche →'))

    expect(await screen.findByText("Fiche de l'employé 42")).toBeInTheDocument()
  })

  it('shows which offer a non-hired candidate is currently in the pipeline for', async () => {
    mockFetch({
      '/api/recruitment/candidates': {
        body: [
          {
            ...CANDIDATE,
            applications: [
              {
                id: 1,
                job_offer_id: 7,
                job_offer_titre: 'Technicien froid',
                stage_libelle: 'Reçu',
              },
            ],
          },
        ],
      },
      '/api/recruitment/job-offers': { body: [] },
    })

    render(
      <MemoryRouter>
        <CandidatesPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Technicien froid')).toBeInTheDocument()
  })
})
