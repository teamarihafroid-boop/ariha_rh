import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './lib/auth-context'
import { RequireRole } from './components/RouteGuards'
import { Login } from './routes/Login'
import { HrLayout } from './routes/hr/HrLayout'
import { LeaveQueue } from './routes/hr/LeaveQueue'
import { LeaveCalendar } from './routes/hr/LeaveCalendar'
import { ResponsablesPage } from './routes/hr/ResponsablesPage'
import { DepartmentsPositionsPage } from './routes/hr/DepartmentsPositionsPage'
import { LeaveTypesPage } from './routes/hr/LeaveTypesPage'
import { LeaveBalancesPage } from './routes/hr/LeaveBalancesPage'
import { HolidaysPage } from './routes/hr/HolidaysPage'
import { PresencePage } from './routes/hr/PresencePage'
import { AttendanceCodesPage } from './routes/hr/AttendanceCodesPage'
import { EmployeesPage } from './routes/hr/EmployeesPage'
import { EmployeeDetailPage } from './routes/hr/EmployeeDetailPage'
import { OrgChartPage } from './routes/hr/OrgChartPage'
import { JobOffersPage } from './routes/hr/JobOffersPage'
import { CandidatesPage } from './routes/hr/CandidatesPage'
import { RecruitmentPipelinePage } from './routes/hr/RecruitmentPipelinePage'
import { UsersPage } from './routes/hr/UsersPage'
import { SettingsHubPage } from './routes/hr/SettingsHubPage'
import { MyLeave } from './routes/employee/MyLeave'
import { MyProfile } from './routes/employee/MyProfile'
import { LeaveOverview } from './routes/dg/LeaveOverview'
import { EmployeesOverview } from './routes/dg/EmployeesOverview'
import { RecruitmentOverview } from './routes/dg/RecruitmentOverview'

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
        <Route path="soldes" element={<LeaveBalancesPage />} />
        <Route path="parametres" element={<SettingsHubPage />} />
        <Route path="parametres/departements-postes" element={<DepartmentsPositionsPage />} />
        <Route path="parametres/responsables" element={<ResponsablesPage />} />
        <Route path="parametres/types-conge" element={<LeaveTypesPage />} />
        <Route path="parametres/feries" element={<HolidaysPage />} />
        <Route path="parametres/codes-presence" element={<AttendanceCodesPage />} />
        <Route path="parametres/utilisateurs" element={<UsersPage />} />
        <Route path="presence" element={<PresencePage />} />
        <Route path="collaborateurs" element={<EmployeesPage />} />
        <Route path="collaborateurs/:id" element={<EmployeeDetailPage />} />
        <Route path="organigramme" element={<OrgChartPage />} />
        <Route path="recrutement/offres" element={<JobOffersPage />} />
        <Route path="recrutement/candidats" element={<CandidatesPage />} />
        <Route path="recrutement/pipeline" element={<RecruitmentPipelinePage />} />
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
        path="/mon-profil"
        element={
          <RequireRole roles={['employee']}>
            <MyProfile />
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

      <Route
        path="/dg/collaborateurs"
        element={
          <RequireRole roles={['dg']}>
            <EmployeesOverview />
          </RequireRole>
        }
      />

      <Route
        path="/dg/organigramme"
        element={
          <RequireRole roles={['dg']}>
            <OrgChartPage />
          </RequireRole>
        }
      />

      <Route
        path="/dg/recrutement"
        element={
          <RequireRole roles={['dg']}>
            <RecruitmentOverview />
          </RequireRole>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
