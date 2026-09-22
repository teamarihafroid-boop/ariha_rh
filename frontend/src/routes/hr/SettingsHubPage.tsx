import type { ComponentType, SVGProps } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, PageHeader } from '../../components/ui'
import { IconBuilding, IconFlag, IconTag, IconUsers } from '../../components/icons'

const TILES: {
  to: string
  label: string
  description: string
  icon: ComponentType<SVGProps<SVGSVGElement>>
}[] = [
  {
    to: '/hr/parametres/departements-postes',
    label: 'Départements & Postes',
    description: "Gérez les départements et l'intitulé des postes de l'entreprise.",
    icon: IconBuilding,
  },
  {
    to: '/hr/parametres/responsables',
    label: 'Responsables congés',
    description:
      'Désignez qui peut soumettre une demande de congé pour un collègue de son département.',
    icon: IconUsers,
  },
  {
    to: '/hr/parametres/types-conge',
    label: 'Types de congé',
    description: 'Congé payé, récupération, maladie… et qui peut les demander.',
    icon: IconTag,
  },
  {
    to: '/hr/parametres/feries',
    label: 'Jours fériés',
    description: 'Jours fériés officiels pris en compte dans les calculs de congé.',
    icon: IconFlag,
  },
  {
    to: '/hr/parametres/codes-presence',
    label: 'Codes de présence',
    description: 'Codes utilisés pour interpréter les imports de pointage (P, A, M…).',
    icon: IconTag,
  },
  {
    to: '/hr/parametres/utilisateurs',
    label: 'Comptes utilisateurs',
    description: "Créez un accès à l'application, changez un rôle, ou désactivez un compte.",
    icon: IconUsers,
  },
]

export function SettingsHubPage() {
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader
        title="Paramètres"
        subtitle="Configuration de référence : départements, congés, présence et comptes."
      />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {TILES.map((tile) => {
          const Icon = tile.icon
          return (
            <button key={tile.to} onClick={() => navigate(tile.to)} className="text-left">
              <Card className="h-full p-4 transition-shadow hover:shadow-md">
                <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50">
                  <Icon className="h-5 w-5 text-brand-700" />
                </div>
                <div className="mb-1 text-sm font-semibold text-slate-800">{tile.label}</div>
                <p className="text-xs text-slate-500">{tile.description}</p>
              </Card>
            </button>
          )
        })}
      </div>
    </div>
  )
}
