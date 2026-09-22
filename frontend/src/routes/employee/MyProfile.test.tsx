import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { mockFetch } from '../../test/mockFetch'
import { MyProfile } from './MyProfile'

describe('MyProfile', () => {
  it('renders the current employee recap with no edit affordances', async () => {
    mockFetch({
      '/api/employees/me': {
        body: {
          id: 1,
          matricule: null,
          nom: 'Alami',
          prenom: 'Sara',
          full_name: 'Sara Alami',
          nom_arabe: null,
          prenom_arabe: null,
          date_naissance: null,
          date_embauche: '2023-03-01',
          date_sortie: null,
          date_fin_periode_essai: null,
          email: 'employe@arihafroid.ma',
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
          department_id: 1,
          department_nom: 'Direction',
          position_id: null,
          position_intitule: 'Collaborateur',
          status_id: null,
          status_libelle: null,
          manager_id: null,
          manager_nom: null,
          emergency_contacts: [],
          probation_evaluations: [],
        },
      },
    })

    render(<MyProfile />)

    expect(await screen.findByText('Sara Alami')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /modifier/i })).not.toBeInTheDocument()
  })
})
