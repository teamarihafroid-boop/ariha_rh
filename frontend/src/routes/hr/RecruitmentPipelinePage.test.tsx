import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { mockFetch } from '../../test/mockFetch'
import { RecruitmentPipelinePage } from './RecruitmentPipelinePage'

const JOB_OFFERS = [
  {
    id: 1,
    titre: 'Technicien froid',
    ville: null,
    department_id: null,
    department_nom: null,
    position_id: null,
    position_intitule: null,
    status_id: 1,
    status_libelle: 'Ouverte',
    status_couleur: '#43A047',
    description: null,
    responsable: null,
    date_creation: '2026-09-01T00:00:00Z',
    date_cloture: null,
    candidatures_count: 1,
  },
]

const STAGES = [{ id: 1, libelle: 'Reçu', ordre: 1, couleur: '#607D8B', is_hire_stage: false }]

const APPLICATIONS = [
  {
    id: 1,
    candidate_id: 1,
    candidate_nom: 'Karim Idrissi',
    candidate_ville: 'Rabat',
    job_offer_id: 1,
    job_offer_titre: 'Technicien froid',
    stage_id: 1,
    stage_libelle: 'Reçu',
    responsable: null,
    date_creation: '2026-09-01T00:00:00Z',
    date_dernier_mouvement: '2026-09-01T00:00:00Z',
  },
]

describe('RecruitmentPipelinePage', () => {
  it('renders stage columns and application cards for the selected offer', async () => {
    mockFetch({
      '/api/recruitment/job-offers': { body: JOB_OFFERS },
      '/api/recruitment/application-stages': { body: STAGES },
      '/api/recruitment/candidates': { body: [] },
      '/api/departments': { body: [] },
      '/api/positions': { body: [] },
      '/api/recruitment/applications': { body: APPLICATIONS },
    })

    render(
      <MemoryRouter>
        <RecruitmentPipelinePage />
      </MemoryRouter>,
    )

    expect((await screen.findAllByText('Reçu')).length).toBeGreaterThan(0)
    expect(await screen.findByText('Karim Idrissi')).toBeInTheDocument()
  })

  it('bulk-imports CVs for the selected offer and shows a per-file result', async () => {
    mockFetch({
      '/api/recruitment/job-offers': { body: JOB_OFFERS },
      '/api/recruitment/application-stages': { body: STAGES },
      '/api/recruitment/candidates': { body: [] },
      '/api/departments': { body: [] },
      '/api/positions': { body: [] },
      '/api/recruitment/applications': { body: APPLICATIONS },
      '/api/recruitment/job-offers/1/bulk-import-cvs': {
        status: 200,
        body: {
          items: [
            {
              filename: 'cv-sami.pdf',
              status: 'created',
              message: null,
              candidate: { id: 5, nom_complet: 'Sami Radi' },
              application: { id: 9 },
            },
          ],
        },
      },
    })

    const { container } = render(
      <MemoryRouter>
        <RecruitmentPipelinePage />
      </MemoryRouter>,
    )
    await screen.findByText('Karim Idrissi')

    await userEvent.click(screen.getByText('Importer des CV'))
    await screen.findByText('Importer des CV — Technicien froid')

    const fileInput = container.querySelector('input[type="file"][multiple]') as HTMLInputElement
    const file = new File(['cv content'], 'cv-sami.pdf', { type: 'application/pdf' })
    await userEvent.upload(fileInput, file)
    await userEvent.click(screen.getByText('Importer'))

    expect(await screen.findByText('Sami Radi')).toBeInTheDocument()
    expect(screen.getByText('Ajouté au pipeline')).toBeInTheDocument()
  })

  it('disables bulk import until an offer is selected', async () => {
    mockFetch({
      '/api/recruitment/job-offers': { body: [] },
      '/api/recruitment/application-stages': { body: STAGES },
      '/api/recruitment/candidates': { body: [] },
      '/api/departments': { body: [] },
      '/api/positions': { body: [] },
    })

    render(
      <MemoryRouter>
        <RecruitmentPipelinePage />
      </MemoryRouter>,
    )
    await screen.findByText('Pipeline de recrutement')

    expect(screen.getByText('Importer des CV').closest('button')).toBeDisabled()
  })

  it('asks RH to fill the missing contract fields before the CDI can be downloaded', async () => {
    const hireStages = [
      { id: 1, libelle: 'Reçu', ordre: 1, couleur: '#607D8B', is_hire_stage: false },
      { id: 2, libelle: 'Accepté', ordre: 2, couleur: '#43A047', is_hire_stage: true },
    ]
    const applications = [
      {
        id: 1,
        candidate_id: 1,
        candidate_nom: 'Sami Radi',
        candidate_ville: 'Rabat',
        job_offer_id: 1,
        job_offer_titre: 'Technicien froid',
        stage_id: 2,
        stage_libelle: 'Accepté',
        responsable: null,
        date_creation: '2026-09-01T00:00:00Z',
        date_dernier_mouvement: '2026-09-01T00:00:00Z',
      },
    ]
    // The hired employee comes back with only what the hire form actually
    // collects — no CIN/date de naissance/lieu de naissance/adresse/salaire.
    const hiredEmployeeIncomplete = {
      id: 77,
      matricule: null,
      nom: 'Radi',
      prenom: 'Sami',
      full_name: 'Sami Radi',
      nom_arabe: null,
      prenom_arabe: null,
      date_naissance: null,
      lieu_naissance: null,
      date_embauche: '2026-09-16',
      date_sortie: null,
      motif_sortie: null,
      date_fin_periode_essai: null,
      email: null,
      telephone: null,
      ville: null,
      adresse: null,
      cin: null,
      cnss: null,
      type_contrat: null,
      categorie_professionnelle: null,
      salaire_base: null,
      salaire_net: null,
      notes: null,
      equipe: null,
      department_id: null,
      department_nom: null,
      position_id: null,
      position_intitule: null,
      status_id: 1,
      status_libelle: 'Actif',
      manager_id: null,
      manager_nom: null,
      emergency_contacts: [],
      probation_evaluations: [],
      documents: [],
      equipements: [],
    }
    const hiredEmployeeComplete = {
      ...hiredEmployeeIncomplete,
      cin: 'BE123456',
      date_naissance: '1990-01-01',
      lieu_naissance: 'Casablanca',
      adresse: '12 Rue Test',
      salaire_net: '5000',
    }

    let putBody: unknown = null
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)

    mockFetch({
      '/api/recruitment/job-offers': { body: JOB_OFFERS },
      '/api/recruitment/application-stages': { body: hireStages },
      '/api/recruitment/candidates': { body: [] },
      '/api/departments': { body: [] },
      '/api/positions': { body: [] },
      '/api/recruitment/applications': { body: applications },
      '/api/recruitment/applications/1/hire-preview': {
        body: {
          prenom_suggere: 'Sami',
          nom_suggere: 'Radi',
          telephone: null,
          email: null,
          ville: null,
          department_id: null,
          department_nom: null,
          cv_disponible: false,
        },
      },
      '/api/recruitment/applications/1/hire': { status: 201, body: hiredEmployeeIncomplete },
      '/api/employees/77': (_path, init) => {
        putBody = JSON.parse(init?.body as string)
        return { status: 200, body: hiredEmployeeComplete }
      },
    })

    render(
      <MemoryRouter>
        <RecruitmentPipelinePage />
      </MemoryRouter>,
    )
    await userEvent.click(await screen.findByText("Proposer l'embauche"))
    await screen.findByText("Proposer l'embauche — Sami Radi")
    await userEvent.click(screen.getByText("Confirmer l'embauche"))

    // Blocked: the "same look" direct download link is gone, replaced by
    // the missing-fields form, and the save button starts disabled.
    await screen.findByText('Embauche confirmée')
    expect(screen.queryByText('Télécharger le contrat CDI')).not.toBeInTheDocument()
    const saveButton = screen.getByText('Enregistrer et télécharger le contrat')
    expect(saveButton.closest('button')).toBeDisabled()

    const [cinInput, dateInput, lieuInput, adresseInput, salaireInput] = document.querySelectorAll(
      'div[role="dialog"] input',
    )
    await userEvent.type(cinInput, 'BE123456')
    await userEvent.type(dateInput, '1990-01-01')
    await userEvent.type(lieuInput, 'Casablanca')
    await userEvent.type(adresseInput, '12 Rue Test')
    await userEvent.type(salaireInput, '5000')

    expect(saveButton.closest('button')).not.toBeDisabled()
    await userEvent.click(saveButton)

    await vi.waitFor(() =>
      expect(openSpy).toHaveBeenCalledWith('/api/employees/77/contrat-cdi', '_blank'),
    )
    expect(putBody).toMatchObject({ cin: 'BE123456', salaire_net: '5000' })

    openSpy.mockRestore()
  })

  it('preselects the offer named in the ?offre= query param (deep link from Offres)', async () => {
    const secondOffer = {
      ...JOB_OFFERS[0],
      id: 2,
      titre: 'Comptable',
      candidatures_count: 0,
    }
    mockFetch({
      '/api/recruitment/job-offers': { body: [JOB_OFFERS[0], secondOffer] },
      '/api/recruitment/application-stages': { body: STAGES },
      '/api/recruitment/candidates': { body: [] },
      '/api/departments': { body: [] },
      '/api/positions': { body: [] },
      '/api/recruitment/applications': { body: APPLICATIONS },
    })

    render(
      <MemoryRouter initialEntries={['/hr/recrutement/pipeline?offre=2']}>
        <RecruitmentPipelinePage />
      </MemoryRouter>,
    )

    const select = await screen.findByDisplayValue('Comptable (0)')
    expect(select).toBeInTheDocument()
  })
})
