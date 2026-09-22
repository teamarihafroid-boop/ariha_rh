import type {
  Department,
  EmployeeFormInput,
  EmployeeLite,
  EmployeeStatus,
  Position,
} from '../lib/api'
import { Field, FormSection, Input, Select, Textarea } from './ui'

export function EmployeeForm({
  value,
  onChange,
  departments,
  positions,
  statuses,
  managers,
}: {
  value: EmployeeFormInput
  onChange: (value: EmployeeFormInput) => void
  departments: Department[]
  positions: Position[]
  statuses: EmployeeStatus[]
  managers: EmployeeLite[]
}) {
  const set = <K extends keyof EmployeeFormInput>(key: K, v: EmployeeFormInput[K]) =>
    onChange({ ...value, [key]: v })

  const str = (v: string) => (v === '' ? null : v)

  return (
    <div className="space-y-5">
      <FormSection title="Identité">
        <Field label="Prénom">
          <Input required value={value.prenom} onChange={(e) => set('prenom', e.target.value)} />
        </Field>
        <Field label="Nom">
          <Input required value={value.nom} onChange={(e) => set('nom', e.target.value)} />
        </Field>
        <Field label="Matricule">
          <Input
            value={value.matricule ?? ''}
            onChange={(e) => set('matricule', str(e.target.value))}
          />
        </Field>
        <Field label="Prénom (arabe)">
          <Input
            dir="rtl"
            value={value.prenom_arabe ?? ''}
            onChange={(e) => set('prenom_arabe', str(e.target.value))}
          />
        </Field>
        <Field label="Nom (arabe)">
          <Input
            dir="rtl"
            value={value.nom_arabe ?? ''}
            onChange={(e) => set('nom_arabe', str(e.target.value))}
          />
        </Field>
        <Field label="CIN">
          <Input value={value.cin ?? ''} onChange={(e) => set('cin', str(e.target.value))} />
        </Field>
        <Field label="Date de naissance">
          <Input
            type="date"
            value={value.date_naissance ?? ''}
            onChange={(e) => set('date_naissance', str(e.target.value))}
          />
        </Field>
        <Field label="Lieu de naissance">
          <Input
            value={value.lieu_naissance ?? ''}
            onChange={(e) => set('lieu_naissance', str(e.target.value))}
          />
        </Field>
      </FormSection>

      <FormSection title="Contact">
        <Field label="Email">
          <Input
            type="email"
            value={value.email ?? ''}
            onChange={(e) => set('email', str(e.target.value))}
          />
        </Field>
        <Field label="Téléphone">
          <Input
            value={value.telephone ?? ''}
            onChange={(e) => set('telephone', str(e.target.value))}
          />
        </Field>
        <Field label="Ville">
          <Input value={value.ville ?? ''} onChange={(e) => set('ville', str(e.target.value))} />
        </Field>
        <Field label="Adresse" className="sm:col-span-2 lg:col-span-2">
          <Input
            value={value.adresse ?? ''}
            onChange={(e) => set('adresse', str(e.target.value))}
          />
        </Field>
      </FormSection>

      <FormSection title="Poste & organisation">
        <Field label="Département">
          <Select
            value={value.department_id ?? ''}
            onChange={(e) => set('department_id', e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">—</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.nom}
                {!d.is_active ? ' (inactif)' : ''}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Poste">
          <Select
            value={value.position_id ?? ''}
            onChange={(e) => set('position_id', e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">—</option>
            {positions.map((p) => (
              <option key={p.id} value={p.id}>
                {p.intitule}
                {!p.is_active ? ' (inactif)' : ''}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Statut">
          <Select
            value={value.status_id ?? ''}
            onChange={(e) => set('status_id', e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">—</option>
            {statuses.map((s) => (
              <option key={s.id} value={s.id}>
                {s.libelle}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Responsable hiérarchique">
          <Select
            value={value.manager_id ?? ''}
            onChange={(e) => set('manager_id', e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">—</option>
            {managers.map((m) => (
              <option key={m.id} value={m.id}>
                {m.full_name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Équipe">
          <Input
            placeholder="Logistique, Caisse, ... (regroupement affiché sur l'organigramme)"
            value={value.equipe ?? ''}
            onChange={(e) => set('equipe', str(e.target.value))}
          />
        </Field>
      </FormSection>

      <FormSection title="Contrat & rémunération">
        <Field label="Type de contrat">
          <Input
            placeholder="CDI, CDD, ..."
            value={value.type_contrat ?? ''}
            onChange={(e) => set('type_contrat', str(e.target.value))}
          />
        </Field>
        <Field label="Catégorie">
          <Select
            value={value.categorie_professionnelle ?? ''}
            onChange={(e) => set('categorie_professionnelle', str(e.target.value))}
          >
            <option value="">—</option>
            <option value="cadre">Cadre</option>
            <option value="salarie">Salarié</option>
          </Select>
        </Field>
        <Field label="CNSS">
          <Input value={value.cnss ?? ''} onChange={(e) => set('cnss', str(e.target.value))} />
        </Field>
        <Field label="Salaire de base">
          <Input
            type="number"
            step="0.01"
            value={value.salaire_base ?? ''}
            onChange={(e) => set('salaire_base', str(e.target.value))}
          />
        </Field>
        <Field label="Salaire net">
          <Input
            type="number"
            step="0.01"
            value={value.salaire_net ?? ''}
            onChange={(e) => set('salaire_net', str(e.target.value))}
          />
        </Field>
        <Field label="Date d'embauche">
          <Input
            type="date"
            value={value.date_embauche ?? ''}
            onChange={(e) => set('date_embauche', str(e.target.value))}
          />
        </Field>
        <Field label="Fin de période d'essai">
          <Input
            type="date"
            value={value.date_fin_periode_essai ?? ''}
            onChange={(e) => set('date_fin_periode_essai', str(e.target.value))}
          />
        </Field>
      </FormSection>

      <FormSection title="Fin de contrat" description="À remplir uniquement lors d'un départ.">
        <Field label="Date de sortie">
          <Input
            type="date"
            value={value.date_sortie ?? ''}
            onChange={(e) => set('date_sortie', str(e.target.value))}
          />
        </Field>
        <Field label="Motif de sortie">
          <Input
            value={value.motif_sortie ?? ''}
            onChange={(e) => set('motif_sortie', str(e.target.value))}
          />
        </Field>
      </FormSection>

      <FormSection title="Notes">
        <Field label="Notes" className="sm:col-span-2 lg:col-span-3">
          <Textarea
            rows={3}
            value={value.notes ?? ''}
            onChange={(e) => set('notes', str(e.target.value))}
          />
        </Field>
      </FormSection>
    </div>
  )
}

export const EMPTY_EMPLOYEE_FORM: EmployeeFormInput = {
  matricule: null,
  nom: '',
  prenom: '',
  nom_arabe: null,
  prenom_arabe: null,
  date_naissance: null,
  lieu_naissance: null,
  date_embauche: null,
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
  position_id: null,
  status_id: null,
  manager_id: null,
}
