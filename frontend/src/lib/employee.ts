import type { Employee, EmployeeFormInput } from './api'

/** Strips the computed/read-only fields the API adds on top of an
 * EmployeeFormInput (joins like department_nom, nested lists like
 * documents) so a fetched Employee can be sent straight back on a PUT. */
export function employeeToFormInput(e: Employee): EmployeeFormInput {
  const {
    id: _id,
    full_name: _full_name,
    department_nom: _department_nom,
    position_intitule: _position_intitule,
    status_libelle: _status_libelle,
    manager_nom: _manager_nom,
    emergency_contacts: _emergency_contacts,
    probation_evaluations: _probation_evaluations,
    documents: _documents,
    equipements: _equipements,
    ...rest
  } = e
  return rest
}

// The CDI contract template leaves these blank when missing — none of them
// are collected by the recruitment "hire" form, so a just-hired employee
// is guaranteed to be missing all five until RH fills them in.
const REQUIRED_CONTRACT_FIELDS: [keyof Employee, string][] = [
  ['cin', 'CIN'],
  ['date_naissance', 'Date de naissance'],
  ['lieu_naissance', 'Lieu de naissance'],
  ['adresse', 'Adresse'],
  ['salaire_net', 'Salaire net'],
]

export function missingContractFieldLabels(employee: Employee): string[] {
  return REQUIRED_CONTRACT_FIELDS.filter(([key]) => !employee[key]).map(([, label]) => label)
}
