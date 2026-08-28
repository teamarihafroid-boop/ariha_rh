import { vi } from 'vitest'

type Handler = (url: string, init?: RequestInit) => { status?: number; body?: unknown } | undefined

/** Minimal fetch mock: register handlers by exact path, falls back to 404. */
export function mockFetch(handlers: Record<string, Handler | { status?: number; body?: unknown }>) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string | URL, init?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.toString()
      const path = url.replace(/^https?:\/\/[^/]+/, '')
      const pathname = path.split('?')[0]
      const handler = handlers[path] ?? handlers[pathname]
      const result = typeof handler === 'function' ? handler(path, init) : handler
      const status = result?.status ?? (result ? 200 : 404)
      const body = result?.body ?? { detail: 'not mocked' }
      return new Response(JSON.stringify(body), {
        status,
        headers: { 'content-type': 'application/json' },
      })
    }),
  )
}
