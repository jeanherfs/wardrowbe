import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { createElement } from 'react'

describe('local credentials provider', () => {
  beforeEach(() => {
    vi.resetModules()
    process.env.LOCAL_AUTH_ENABLED = 'true'
    delete process.env.OIDC_ISSUER_URL
    delete process.env.DEV_MODE
  })

  it('exposes a local provider when local auth is enabled', async () => {
    const { authOptions } = await import('@/lib/auth')
    const providers = authOptions.providers.map((provider: any) => provider.options?.id || provider.id)

    expect(providers).toContain('local-credentials')
  })

  it('authorizes credentials through the backend local login endpoint', async () => {
    const { authOptions } = await import('@/lib/auth')
    const provider = authOptions.providers.find((candidate: any) => candidate.options?.id === 'local-credentials') as any
    vi.mocked(global.fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 'user-id',
        external_id: 'local-user-id',
        email: 'mail@jeanherfs.nl',
        display_name: 'Jean Herfs',
        access_token: 'backend-token',
      }),
    } as Response)

    const result = await provider.options.authorize(
      { email: 'mail@jeanherfs.nl', password: 'temporary-password' },
      {} as Request,
    )

    expect(result).toMatchObject({ id: 'local-user-id', email: 'mail@jeanherfs.nl', accessToken: 'backend-token' })
    expect(global.fetch).toHaveBeenCalledWith(
      'http://backend:8000/api/v1/auth/local-login',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('shows the email field and hides display name in local mode', async () => {
    const { default: LoginPage } = await import('@/app/login/page')
    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ configured: true, mode: 'local' }),
    } as Response)

    render(createElement(LoginPage))

    expect(await screen.findByLabelText('email')).toBeInTheDocument()
    expect(screen.queryByLabelText('displayName')).not.toBeInTheDocument()
  })
})
