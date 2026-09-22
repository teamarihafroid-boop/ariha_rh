export const EMPLOYEE_DOCUMENT_TYPES = [
  'CIN',
  'Contrat signé',
  'CV',
  'Diplômes',
  'Certificats / Attestations de travail',
  'Photos',
  'RIB',
  "Certificat d'aptitude physique",
  "Déclaration sur l'honneur",
  'Autre',
]

export const CANDIDATE_ATTACHMENT_TYPES = ['CV', 'Lettre de motivation', 'Diplôme', 'Autre']

export const EMPLOYEE_EQUIPMENT_TYPES = [
  'Tenue de travail',
  'Téléphone',
  'Ordinateur portable',
  'Véhicule de service',
  "Badge d'accès",
  'Clés',
  'Outillage',
  'EPI (équipement de protection individuelle)',
  'Carte carburant',
]

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} Ko`
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`
}
