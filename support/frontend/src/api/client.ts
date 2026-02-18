/**
 * Cliente API: cookie-session (withCredentials), CSRF desde cookie.
 * Base URL desde VITE_API_BASE_URL; en dev con proxy puede ser relativo.
 */
import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

const baseURL =
  ((import.meta.env.VITE_API_BASE_URL as string) || '').replace(/\/?$/, '') + '/api'

function getCsrfToken(): string | null {
  const name = 'csrftoken'
  const cookies = document.cookie.split(';')
  for (const c of cookies) {
    const [key, value] = c.trim().split('=')
    if (key === name) return decodeURIComponent(value || '')
  }
  return null
}

const client: AxiosInstance = axios.create({
  baseURL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
})

client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getCsrfToken()
  if (token) {
    config.headers.set('X-CSRFToken', token)
  }
  return config
})

client.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      window.dispatchEvent(new CustomEvent('auth:logout'))
    }
    return Promise.reject(err)
  }
)

export function setIdempotencyKey(headers: Record<string, string>): void {
  headers['Idempotency-Key'] = crypto.randomUUID()
}

export default client
