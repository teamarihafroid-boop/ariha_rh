import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AuthProvider } from '../lib/auth-context'
import { mockFetch } from '../test/mockFetch'
import { Login } from './Login'

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/hr/demandes" element={<div>HR home</div>} />
          <Route path="/mon-conge" element={<div>Employee home</div>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('Login', () => {
  it('renders the login form', async () => {
    mockFetch({ '/api/auth/me': { status: 401 } })
    renderLogin()
    expect(await screen.findByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Mot de passe')).toBeInTheDocument()
  })

  it('submits credentials and redirects HR to the HR home', async () => {
    mockFetch({
      '/api/auth/me': { status: 401 },
      '/api/auth/login': {
        status: 200,
        body: {
          id: 1,
          email: 'rh@arihafroid.ma',
          role: 'hr',
          employee_id: null,
          department_id: null,
        },
      },
    })
    renderLogin()

    const user = userEvent.setup()
    await user.type(await screen.findByLabelText('Email'), 'rh@arihafroid.ma')
    await user.type(screen.getByLabelText('Mot de passe'), 'ChangeMoi123!')
    await user.click(screen.getByRole('button', { name: 'Se connecter' }))

    await waitFor(() => expect(screen.getByText('HR home')).toBeInTheDocument())
  })

  it('shows an error message on invalid credentials', async () => {
    mockFetch({
      '/api/auth/me': { status: 401 },
      '/api/auth/login': { status: 401, body: { detail: 'Identifiants invalides.' } },
    })
    renderLogin()

    const user = userEvent.setup()
    await user.type(await screen.findByLabelText('Email'), 'rh@arihafroid.ma')
    await user.type(screen.getByLabelText('Mot de passe'), 'wrong')
    await user.click(screen.getByRole('button', { name: 'Se connecter' }))

    expect(await screen.findByText('Identifiants invalides.')).toBeInTheDocument()
  })
})
