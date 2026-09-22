import { Field, Input } from './ui'

/** Optional "also create a login" block, reused wherever an Employee gets
 * created (manual creation, recruitment hire) — closes the gap where an
 * Employee record and its login used to require two separate trips. */
export function AccountCreationFields({
  enabled,
  onToggle,
  email,
  onEmailChange,
  password,
  onPasswordChange,
}: {
  enabled: boolean
  onToggle: (value: boolean) => void
  email: string
  onEmailChange: (value: string) => void
  password: string
  onPasswordChange: (value: string) => void
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
      <label className="flex items-center gap-2 text-sm font-medium text-slate-800">
        <input
          type="checkbox"
          className="accent-brand-700"
          checked={enabled}
          onChange={(e) => onToggle(e.target.checked)}
        />
        Créer aussi un compte de connexion pour ce collaborateur
      </label>
      {enabled && (
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Email de connexion">
            <Input
              type="email"
              required
              value={email}
              onChange={(e) => onEmailChange(e.target.value)}
            />
          </Field>
          <Field label="Mot de passe initial">
            <Input
              type="text"
              required
              minLength={8}
              value={password}
              onChange={(e) => onPasswordChange(e.target.value)}
            />
          </Field>
        </div>
      )}
    </div>
  )
}
