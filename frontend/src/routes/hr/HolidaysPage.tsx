import { useEffect, useState, type FormEvent } from 'react'
import { api, ApiError, type Holiday } from '../../lib/api'
import { Button, Card, ErrorBanner, Field, Input, PageHeader, Table } from '../../components/ui'

export function HolidaysPage() {
  const [holidays, setHolidays] = useState<Holiday[]>([])
  const [year, setYear] = useState(new Date().getFullYear())
  const [newDate, setNewDate] = useState('')
  const [newLibelle, setNewLibelle] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = async () => {
    try {
      const all = await api.get<Holiday[]>('/holidays')
      setHolidays(all)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur de chargement.')
    }
  }

  useEffect(() => {
    load()
  }, [])

  const generateFixed = async () => {
    setBusy(true)
    setError(null)
    try {
      await api.post(`/holidays/generate-fixed?annee=${year}`)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    } finally {
      setBusy(false)
    }
  }

  const addManual = async (e: FormEvent) => {
    e.preventDefault()
    if (!newDate || !newLibelle) return
    setError(null)
    try {
      await api.post('/holidays', { date: newDate, libelle: newLibelle })
      setNewDate('')
      setNewLibelle('')
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const remove = async (id: number) => {
    setError(null)
    try {
      await api.delete(`/holidays/${id}`)
      await load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Erreur.')
    }
  }

  const holidaysForYear = holidays.filter((h) => new Date(h.date).getFullYear() === year)

  return (
    <div>
      <PageHeader
        title="Jours fériés"
        subtitle="Les jours fériés civils à date fixe peuvent être générés automatiquement. Les fêtes religieuses mobiles (Aïd al-Fitr, Aïd al-Adha, ...) changent de date chaque année selon le calendrier lunaire et doivent être ajoutées manuellement une fois confirmées."
      />
      <ErrorBanner message={error} />

      <Card className="mb-4 flex flex-wrap items-end gap-3 p-4">
        <Field label="Année">
          <Input
            type="number"
            className="w-24 py-1.5"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          />
        </Field>
        <Button variant="secondary" onClick={generateFixed} disabled={busy}>
          {busy ? 'Génération…' : 'Générer les jours fériés fixes'}
        </Button>
      </Card>

      <Card className="mb-4 p-4">
        <h3 className="mb-3 text-sm font-semibold text-slate-700">
          Ajouter une fête mobile (ou tout autre jour férié)
        </h3>
        <form onSubmit={addManual} className="flex flex-wrap items-end gap-3">
          <Field label="Date">
            <Input
              type="date"
              required
              className="py-1.5"
              value={newDate}
              onChange={(e) => setNewDate(e.target.value)}
            />
          </Field>
          <Field label="Libellé" className="min-w-[10rem] flex-1">
            <Input
              required
              placeholder="ex. Aïd al-Fitr"
              className="py-1.5"
              value={newLibelle}
              onChange={(e) => setNewLibelle(e.target.value)}
            />
          </Field>
          <Button type="submit">Ajouter</Button>
        </form>
      </Card>

      <Card>
        <Table>
          <thead className="border-b border-slate-200 text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2">Date</th>
              <th className="px-4 py-2">Libellé</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {holidaysForYear.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-slate-400" colSpan={3}>
                  Aucun jour férié pour {year}.
                </td>
              </tr>
            )}
            {holidaysForYear.map((h) => (
              <tr key={h.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-3 text-slate-600">{h.date}</td>
                <td className="px-4 py-3 text-slate-600">{h.libelle}</td>
                <td className="px-4 py-3 text-right">
                  <button
                    className="text-sm text-red-600 hover:underline"
                    onClick={() => remove(h.id)}
                  >
                    Supprimer
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>
    </div>
  )
}
