import type {
  ButtonHTMLAttributes,
  HTMLAttributes,
  InputHTMLAttributes,
  LabelHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-xl border border-slate-200 bg-white shadow-sm transition-shadow duration-200 ${className}`}
    >
      {children}
    </div>
  )
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'danger' }) {
  const base =
    'rounded-lg px-3.5 py-2 text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed ' +
    'transition-[background-color,box-shadow,transform] duration-150 active:scale-[0.98]'
  const variants = {
    primary: 'bg-accent-600 text-white hover:bg-accent-700 shadow-sm shadow-accent-600/20',
    secondary: 'bg-slate-100 text-slate-800 hover:bg-slate-200',
    danger: 'bg-red-600 text-white hover:bg-red-700',
  }
  return <button className={`${base} ${variants[variant]} ${className}`} {...props} />
}

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-800',
  approved: 'bg-emerald-100 text-emerald-800',
  rejected: 'bg-red-100 text-red-800',
  cancelled: 'bg-slate-200 text-slate-600',
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'En attente',
  approved: 'Approuvée',
  rejected: 'Refusée',
  cancelled: 'Annulée',
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status] ?? 'bg-slate-100 text-slate-700'}`}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  )
}

/** Badge tinted from a hex color coming from the data itself (e.g. an
 * EmployeeStatus/LeaveType row's own `couleur`), rather than a hardcoded
 * status->class map. */
export function ColorBadge({ label, color }: { label: string; color: string | null }) {
  const c = color ?? '#94A3B8'
  return (
    <span
      className="inline-block rounded-full px-2 py-0.5 text-xs font-medium"
      style={{ backgroundColor: `${c}1A`, color: c }}
    >
      {label}
    </span>
  )
}

/** Groups related fields under a small-caps heading — used to break up
 * long forms/detail views (identité, contact, contrat, ...) into
 * scannable blocks instead of one flat wall of fields. */
export function FormSection({
  title,
  description,
  className = '',
  children,
}: {
  title: string
  description?: string
  className?: string
  children: ReactNode
}) {
  return (
    <div className={`border-t border-slate-100 pt-4 first:border-t-0 first:pt-0 ${className}`}>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h3>
      {description && <p className="mt-0.5 text-xs text-slate-400">{description}</p>}
      <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">{children}</div>
    </div>
  )
}

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-xl font-bold text-slate-900">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
    </div>
  )
}

export function ErrorBanner({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
      {message}
    </div>
  )
}

export function Table({ children, ...props }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="overflow-x-auto">
      <table
        className="w-full text-left text-sm [&_tbody_tr]:transition-colors [&_tbody_tr:hover]:bg-slate-50"
        {...props}
      >
        {children}
      </table>
    </div>
  )
}

export function Modal({
  title,
  children,
  onClose,
  maxWidthClassName = 'max-w-md',
}: {
  title: string
  children: ReactNode
  onClose: () => void
  maxWidthClassName?: string
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 animate-[fadeIn_150ms_ease-out]"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`flex max-h-[90vh] w-full ${maxWidthClassName} flex-col rounded-xl bg-white p-6 shadow-lg animate-[scaleIn_150ms_ease-out]`}
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-4 flex-none text-base font-semibold text-slate-900">{title}</h2>
        <div className="overflow-y-auto pr-1">{children}</div>
      </div>
    </div>
  )
}

const FIELD_CLASS =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition-colors focus:border-brand-600 focus:ring-2 focus:ring-brand-600/15'

export function Label(props: LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className="mb-1 block text-sm font-medium text-slate-700" {...props} />
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  const { className = '', ...rest } = props
  return <input className={`${FIELD_CLASS} ${className}`} {...rest} />
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  const { className = '', ...rest } = props
  return <select className={`${FIELD_CLASS} ${className}`} {...rest} />
}

export function Textarea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const { className = '', ...rest } = props
  return <textarea className={`${FIELD_CLASS} ${className}`} {...rest} />
}

/** A label + control pair, sized to sit in a grid/flex form row. */
export function Field({
  label,
  htmlFor,
  className = '',
  children,
}: {
  label: string
  htmlFor?: string
  className?: string
  children: ReactNode
}) {
  return (
    <div className={className}>
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
    </div>
  )
}
