import { useEffect, useRef, useState } from 'react'

export type SocketEvent = { event: string; payload: any; server_time?: string }

/**
 * Authenticated WebSocket hook. The token is read from the httpOnly session
 * only indirectly: the backend accepts the same token via a short-lived
 * /api/auth/socket-token endpoint, which this hook obtains before connecting.
 */
export function useSocket(enabled: boolean, onEvent: (event: SocketEvent) => void) {
  const [connected, setConnected] = useState(false)
  const [reconnects, setReconnects] = useState(0)
  const callback = useRef(onEvent)
  callback.current = onEvent

  useEffect(() => {
    if (!enabled) return
    let socket: WebSocket | null = null
    let retry: ReturnType<typeof setTimeout> | null = null
    let cancelled = false

    const connect = async () => {
      try {
        const response = await fetch('/api/auth/socket-token', { credentials: 'include' })
        if (!response.ok) return
        const { token } = await response.json()
        if (cancelled) return
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        socket = new WebSocket(`${protocol}//${window.location.host}/ws?token=${encodeURIComponent(token)}`)
        socket.onopen = () => { setConnected(true) }
        socket.onmessage = (message) => {
          try { callback.current(JSON.parse(message.data)) } catch { /* ignore malformed frames */ }
        }
        socket.onclose = () => {
          setConnected(false)
          if (!cancelled) {
            setReconnects((n) => n + 1)
            retry = setTimeout(connect, 2000)
          }
        }
        socket.onerror = () => socket?.close()
      } catch {
        if (!cancelled) retry = setTimeout(connect, 3000)
      }
    }
    connect()
    return () => {
      cancelled = true
      if (retry) clearTimeout(retry)
      socket?.close()
    }
  }, [enabled])

  return { connected, reconnects }
}
