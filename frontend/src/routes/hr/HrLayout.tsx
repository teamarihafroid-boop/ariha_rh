import { NavLink, Outlet } from 'react-router-dom'

const tabClass = ({ isActive }: { isActive: boolean }) =>
  `border-b-2 px-1 pb-2 text-sm font-medium ${
    isActive
      ? 'border-blue-700 text-blue-800'
      : 'border-transparent text-slate-500 hover:text-slate-800'
  }`

export function HrLayout() {
  return (
    <div>
      <nav className="mb-6 flex gap-6 border-b border-slate-200">
        <NavLink to="/hr/demandes" className={tabClass} end>
          Demandes de congé
        </NavLink>
        <NavLink to="/hr/calendrier" className={tabClass}>
          Calendrier
        </NavLink>
        <NavLink to="/hr/parametres" className={tabClass}>
          Paramètres
        </NavLink>
      </nav>
      <Outlet />
    </div>
  )
}
