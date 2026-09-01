import { useEffect, useState, type FormEvent } from 'react'
import { api, ApiError, type ImportResult, type UploadPreview } from '../../lib/api'
import { Button, Card, ErrorBanner, Field, Input, PageHeader, Table } from '../../components/ui'

const MONTHS_FR = [
  'Janvier',
  'Février',
  'Mars',
  'Avril',
  'Mai',
  'Juin',
  'Juillet',
  'Août',
  'Septembre',
  'Octobre',
  'Novembre',
  'Décembre',
]

export function PresencePage() {
  return (
    <div>
      <PageHeader
        title="Présence"
        subtitle="Importer un pointage mensuel et exporter l'état de présence consolidé (pointage + congés + jours fériés)."
      />
      <ImportWizard />
      <div className="mt-8">
        <ExportPanel />
      </div>
      <div className="mt-8">
        <ImportHistory />
      </div>
    </div>
  )
}

function MonthYearFields({
  mois,
  annee,
  onMoisChange,
  onAnneeChange,
}: {
  mois: number
  annee: number
  onMoisChange: (v: number) => void
  onAnneeChange: (v: number) => void
}) {
  return (
    <>
      <Field label="Mois">
        <select
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={mois}
          onChange={(e) => onMoisChange(Number(e.target.value))}
        >
          {MONTHS_FR.map((m, i) => (
            <option key={m} value={i + 1}>
              {m}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Année">
        <Input
          type="number"
          className="w-24 py-2"
          value={annee}
          onChange={(e) => onAnneeChange(Number(e.target.value))}
        />
      </Field>
    </>
  )
}

function ImportWizard() {
  const today = new Date()
  const [file, setFile] = useState<File | null>(null)
  const [mois, setMois] = useState(today.getMonth() + 1)
  const [annee, setAnnee] = useState(today.getFullYear())
  const [preview, setPreview] = useState<UploadPreview | null>(null)
  const [identifierColumn, setIdentifierColumn] = useState('')
  const [dayColumns, setDayColumns] = useState<string[]>([])
  const [result, setResult] = useState<ImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const analyze = async (e: FormEvent) => {
    e.preventDefault()
    if (!file) return
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const data = await api.upload<UploadPreview>('/attendance/upload', formData)
      setPreview(data)
      setIdentifierColumn(data.guessed_identifier_column ?? '')
      setDayColumns(data.guessed_day_columns)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    } finally {
      setBusy(false)
    }
  }

  const toggleDayColumn = (col: string) => {
    setDayColumns((prev) => (prev.includes(col) ? prev.filter((c) => c !== col) : [...prev, col]))
  }

  const confirmImport = async () => {
    if (!preview) return
    setBusy(true)
    setError(null)
    try {
      const data = await api.post<ImportResult>('/attendance/import', {
        token: preview.token,
        identifier_column: identifierColumn,
        day_columns: dayColumns,
        mois,
        annee,
      })
      setResult(data)
      setPreview(null)
      setFile(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    } finally {
      setBusy(false)
    }
  }

  const reset = () => {
    setPreview(null)
    setFile(null)
    setResult(null)
    setError(null)
  }

  return (
    <Card className="p-4">
      <h2 className="mb-3 text-sm font-semibold text-slate-700">Importer un pointage</h2>
      <ErrorBanner message={error} />

      {result && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          <div className="font-medium">
            {result.nb_lignes_importees} ligne(s) importée(s) pour {MONTHS_FR[result.mois - 1]}{' '}
            {result.annee}.
          </div>
          {result.nb_lignes_non_reconnues > 0 && (
            <div className="mt-2 text-amber-800">
              {result.nb_lignes_non_reconnues} non reconnue(s) — aucune donnée écrite pour ces
              lignes, corrigez le fichier ou la fiche collaborateur puis réimportez :
              <div className="mt-1 font-medium">{result.noms_non_reconnus.join(', ')}</div>
            </div>
          )}
          <button
            className="mt-3 text-xs font-medium text-brand-700 hover:underline"
            onClick={reset}
          >
            Nouvel import
          </button>
        </div>
      )}

      {!preview && !result && (
        <form onSubmit={analyze} className="flex flex-wrap items-end gap-3">
          <Field label="Fichier (.xlsx ou .csv)">
            <input
              type="file"
              required
              accept=".xlsx,.csv"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block text-sm text-slate-700"
            />
          </Field>
          <MonthYearFields
            mois={mois}
            annee={annee}
            onMoisChange={setMois}
            onAnneeChange={setAnnee}
          />
          <Button type="submit" disabled={!file || busy}>
            {busy ? 'Analyse…' : 'Analyser le fichier'}
          </Button>
        </form>
      )}

      {preview && (
        <div>
          <p className="mb-3 text-sm text-slate-600">
            {preview.nb_rows} ligne(s) détectée(s). Vérifiez la colonne d'identification et les
            colonnes de jour avant de confirmer.
          </p>

          <Field label="Colonne d'identification (nom ou matricule)" className="mb-3 max-w-sm">
            <select
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={identifierColumn}
              onChange={(e) => setIdentifierColumn(e.target.value)}
            >
              <option value="">— choisir —</option>
              {preview.columns.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </Field>

          <div className="mb-4">
            <div className="mb-1.5 text-sm font-medium text-slate-700">Colonnes de jour</div>
            <div className="flex flex-wrap gap-2">
              {preview.columns
                .filter((c) => c !== identifierColumn)
                .map((c) => (
                  <label
                    key={c}
                    className={`cursor-pointer rounded-full border px-2.5 py-1 text-xs font-medium ${
                      dayColumns.includes(c)
                        ? 'border-brand-600 bg-brand-50 text-brand-700'
                        : 'border-slate-300 text-slate-600'
                    }`}
                  >
                    <input
                      type="checkbox"
                      className="hidden"
                      checked={dayColumns.includes(c)}
                      onChange={() => toggleDayColumn(c)}
                    />
                    {c}
                  </label>
                ))}
            </div>
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  {preview.columns.map((c) => (
                    <th key={c} className="whitespace-nowrap px-2 py-1.5">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.sample_rows.map((row, i) => (
                  <tr key={i} className="border-t border-slate-100">
                    {preview.columns.map((c) => (
                      <td key={c} className="whitespace-nowrap px-2 py-1.5 text-slate-600">
                        {row[c]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex gap-2">
            <Button
              disabled={!identifierColumn || dayColumns.length === 0 || busy}
              onClick={confirmImport}
            >
              {busy ? 'Import…' : "Confirmer l'import"}
            </Button>
            <Button variant="secondary" onClick={reset}>
              Annuler
            </Button>
          </div>
        </div>
      )}
    </Card>
  )
}

function ExportPanel() {
  const today = new Date()
  const [mois, setMois] = useState(today.getMonth() + 1)
  const [annee, setAnnee] = useState(today.getFullYear())

  return (
    <Card className="p-4">
      <h2 className="mb-3 text-sm font-semibold text-slate-700">
        Exporter l'état de présence mensuel
      </h2>
      <div className="flex flex-wrap items-end gap-3">
        <MonthYearFields
          mois={mois}
          annee={annee}
          onMoisChange={setMois}
          onAnneeChange={setAnnee}
        />
        <a
          href={`/api/attendance/export?mois=${mois}&annee=${annee}`}
          target="_blank"
          rel="noreferrer"
          className="rounded-lg bg-accent-600 px-3.5 py-2 text-sm font-semibold text-white shadow-sm shadow-accent-600/20 hover:bg-accent-700"
        >
          Exporter en Excel
        </a>
      </div>
    </Card>
  )
}

function ImportHistory() {
  const [imports, setImports] = useState<ImportResult[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<ImportResult[]>('/attendance/imports')
      .then(setImports)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Erreur.'))
  }, [])

  return (
    <div>
      <h2 className="mb-3 text-sm font-semibold text-slate-700">Historique des imports</h2>
      <ErrorBanner message={error} />
      <Card>
        <Table>
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Fichier</th>
              <th className="px-4 py-2">Période</th>
              <th className="px-4 py-2">Importées</th>
              <th className="px-4 py-2">Non reconnues</th>
            </tr>
          </thead>
          <tbody>
            {imports.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={4}>
                  Aucun import.
                </td>
              </tr>
            )}
            {imports.map((i) => (
              <tr key={i.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-3 text-slate-600">{i.nom_fichier}</td>
                <td className="px-4 py-3 text-slate-600">
                  {MONTHS_FR[i.mois - 1]} {i.annee}
                </td>
                <td className="px-4 py-3 text-slate-600">{i.nb_lignes_importees}</td>
                <td className="px-4 py-3 text-slate-600">{i.nb_lignes_non_reconnues}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </div>
  )
}
