import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './lib/auth-context'
import { RequireRole } from './components/RouteGuards'
import { Login } from './routes/Login'
import { HrLayout } from './routes/hr/HrLayout'
import { LeaveQueue } from './routes/hr/LeaveQueue'
import { LeaveCalendar } from './routes/hr/LeaveCalendar'
import { Parametres } from './routes/hr/Parametres'
import { MyLeave } from './routes/employee/MyLeave'
import { LeaveOverview } from './routes/dg/LeaveOverview'

const HOME_BY_ROLE: Record<string, string> = {
  hr: '/hr/demandes',
  dg: '/dg/conges',
  employee: '/mon-conge',
}

function Home() {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/login" replace />
  return <Navigate to={HOME_BY_ROLE[user.role] ?? '/login'} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />

      <Route
        path="/hr"
        element={
          <RequireRole roles={['hr']}>
            <HrLayout />
          </RequireRole>
        }
      >
        <Route path="demandes" element={<LeaveQueue />} />
        <Route path="calendrier" element={<LeaveCalendar />} />
        <Route path="parametres" element={<Parametres />} />
      </Route>

      <Route
        path="/mon-conge"
        element={
          <RequireRole roles={['employee']}>
            <MyLeave />
          </RequireRole>
        }
      />

      <Route
        path="/dg/conges"
        element={
          <RequireRole roles={['dg']}>
            <LeaveOverview />
          </RequireRole>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
