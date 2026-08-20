const BASE = '/api'

async function request(path, options) {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = body && body.detail ? body.detail : response.statusText
    throw new Error(detail)
  }
  return body
}

export const api = {
  status: () => request('/status'),
  decisions: (limit = 30) => request(`/decisions?limit=${limit}`),
  backtestReport: () => request('/backtest-report'),
  bootstrap: (mode) => request('/actions/bootstrap', { method: 'POST', body: JSON.stringify({ mode }) }),
  healthcheck: () => request('/actions/healthcheck', { method: 'POST' }),
  scan: (payload) => request('/actions/scan', { method: 'POST', body: JSON.stringify(payload) }),
  backtest: (payload) => request('/actions/backtest', { method: 'POST', body: JSON.stringify(payload) }),
}
