import { useCallback, useEffect, useState } from 'react'

const base = import.meta.env.VITE_API_BASE_URL ?? ''

export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`${base}/api${path}`, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const result = await response.json()
  if (!response.ok) {
    const detail = result.detail ?? result
    let message: string
    if (typeof detail === 'string') message = detail
    else if (Array.isArray(detail)) message = detail.map((item: { msg: string }) => item.msg).join(' ')
    else message = [detail.message ?? detail.detail ?? 'Request failed.', ...(detail.blocked_reasons ?? [])].join(' ')
    throw new Error(message)
  }
  return result as T
}

export function useResource<T>(path: string) {
  const [data, setData] = useState<T | undefined>()
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  const [loading, setLoading] = useState(true)
  const reload = useCallback(() => setRevision(value => value + 1), [])
  useEffect(() => {
    let current = true
    setLoading(true)
    setData(undefined)
    setError('')
    api<T>(path).then(result => { if (current) setData(result) })
      .catch((failure: Error) => { if (current) setError(failure.message) })
      .finally(() => { if (current) setLoading(false) })
    return () => { current = false }
  }, [path, revision])
  return { data, error, loading, reload }
}

export function useAction(onSuccess: () => void) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  async function run(path: string, method = 'POST', body?: unknown, message = 'Saved.') {
    if (busy) return false
    setBusy(true); setError(''); setSuccess('')
    try {
      await api(path, method, body)
      setSuccess(message)
      onSuccess()
      return true
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Unable to save. Refresh and retry.')
      return false
    } finally { setBusy(false) }
  }
  return { busy, error, success, run }
}

export const key = () => crypto.randomUUID()
