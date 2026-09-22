import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import { AccountCreationFields } from './AccountCreationFields'

function Harness() {
  const [enabled, setEnabled] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  return (
    <AccountCreationFields
      enabled={enabled}
      onToggle={setEnabled}
      email={email}
      onEmailChange={setEmail}
      password={password}
      onPasswordChange={setPassword}
    />
  )
}

describe('AccountCreationFields', () => {
  it('hides the email/password inputs until the checkbox is checked', async () => {
    render(<Harness />)

    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('checkbox'))

    const inputs = screen.getAllByRole('textbox')
    expect(inputs).toHaveLength(2)
  })

  it('lets the user type an email and password once enabled', async () => {
    render(<Harness />)
    await userEvent.click(screen.getByRole('checkbox'))

    const [emailInput, passwordInput] = screen.getAllByRole('textbox')
    await userEvent.type(emailInput, 'karim@example.com')
    await userEvent.type(passwordInput, 'SuperSecret1')

    expect(emailInput).toHaveValue('karim@example.com')
    expect(passwordInput).toHaveValue('SuperSecret1')
  })
})
