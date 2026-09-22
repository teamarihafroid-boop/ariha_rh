import { useEffect, useState } from 'react'
import {
  api,
  ApiError,
  type OrgChart,
  type OrgChartDepartment,
  type OrgChartNiveau,
  type OrgChartNode,
  type OrgChartVacant,
} from '../../lib/api'
import { Card, ErrorBanner, PageHeader } from '../../components/ui'
import './OrgChartTree.css'

const NIVEAU_CLASS: Record<OrgChartNiveau, string> = {
  direction: 'orgchart-direction',
  equipe: 'orgchart-departement',
  responsable: 'orgchart-responsable',
  employe: 'orgchart-employe',
}

const LEGEND: [string, string][] = [
  ['orgchart-direction', 'Direction Générale'],
  ['orgchart-departement', 'Départements'],
  ['orgchart-responsable', 'Responsables'],
  ['orgchart-employe', 'Employé(e)'],
  ['orgchart-recrutement', 'Recrutement'],
]

function TreeNode({ node }: { node: OrgChartNode }) {
  return (
    <li>
      <div className={`orgchart-box ${NIVEAU_CLASS[node.niveau]}`}>
        <div className="orgchart-name">{node.full_name}</div>
        {node.position_intitule && (
          <div className="orgchart-position">{node.position_intitule}</div>
        )}
        {node.rapporte_a && (
          <div className="orgchart-reports-to">
            rapporte à {node.rapporte_a.nom_complet}
            {node.rapporte_a.department_nom ? ` (${node.rapporte_a.department_nom})` : ''}
          </div>
        )}
      </div>
      {node.enfants.length > 0 && (
        <ul>
          {node.enfants.map((child) => (
            <TreeNode key={child.id} node={child} />
          ))}
        </ul>
      )}
    </li>
  )
}

function VacantNode({ vacant }: { vacant: OrgChartVacant }) {
  return (
    <li>
      <div className="orgchart-box orgchart-recrutement">
        <div className="orgchart-name">{vacant.titre}</div>
        <div className="orgchart-position">
          Poste ouvert{vacant.ville ? ` — ${vacant.ville}` : ''}
        </div>
      </div>
    </li>
  )
}

function DepartmentTree({ dept }: { dept: OrgChartDepartment }) {
  const hasChildren = dept.collaborateurs.length > 0 || dept.postes_ouverts.length > 0
  return (
    <Card className="overflow-x-auto p-4">
      <div className="orgchart-tree">
        <ul>
          <li>
            <div className="orgchart-box orgchart-departement">
              <div className="orgchart-name">{dept.department_nom}</div>
            </div>
            {hasChildren && (
              <ul>
                {dept.collaborateurs.map((node) => (
                  <TreeNode key={node.id} node={node} />
                ))}
                {dept.postes_ouverts.map((vacant) => (
                  <VacantNode key={`job-${vacant.id}`} vacant={vacant} />
                ))}
              </ul>
            )}
          </li>
        </ul>
      </div>
    </Card>
  )
}

export function OrgChartPage() {
  const [chart, setChart] = useState<OrgChart | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<OrgChart>('/employees/orgchart')
      .then(setChart)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur de chargement.'))
  }, [])

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <PageHeader
          title="Organigramme"
          subtitle="Basé sur les collaborateurs actifs et leur responsable hiérarchique."
        />
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs">
          {LEGEND.map(([cls, label]) => (
            <div key={cls} className="flex items-center gap-1.5">
              <span className={`orgchart-swatch ${cls}`} />
              <span className="text-slate-600">{label}</span>
            </div>
          ))}
        </div>
      </div>
      <ErrorBanner message={error} />

      {chart && chart.direction.length > 0 && (
        <Card className="mb-6 overflow-x-auto p-4">
          <div className="orgchart-tree">
            <ul>
              {chart.direction.map((node) => (
                <TreeNode key={node.id} node={node} />
              ))}
            </ul>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {chart?.departements.map((dept) => (
          <DepartmentTree key={dept.department_id} dept={dept} />
        ))}
      </div>

      {chart && chart.direction.length === 0 && chart.departements.length === 0 && (
        <p className="text-sm text-slate-400">Aucun collaborateur actif à afficher.</p>
      )}
    </div>
  )
}
