import { getStoredAccessToken } from '@/shared/api/authTokenStorage'

type StompHeaders = Record<string, string>

interface StompFrame {
  command: string
  headers: StompHeaders
  body: string
}

interface StompSubscription {
  id: string
  unsubscribe: () => void
}

interface LiveRealtimeClientOptions {
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: unknown) => void
}

const NULL = '\u0000'
const HEARTBEAT_OUTGOING_MS = 10_000
const CONNECT_TIMEOUT_MS = 8_000
const RECONNECT_BASE_MS = 1_000
const RECONNECT_MAX_MS = 15_000
const LIVE_REALTIME_API_ENABLED =
  import.meta.env.VITE_LIVE_REALTIME_API_ENABLED === 'true' ||
  import.meta.env.VITE_LIVE_WATCH_API_ENABLED === 'true'

let subscriptionSequence = 0

export class LiveRealtimeClient {
  private socket: WebSocket | null = null
  private subscriptions = new Map<string, (body: unknown, frame: StompFrame) => void>()
  private receiveBuffer = ''
  private isConnected = false
  private heartbeatTimer: number | null = null
  private reconnectTimer: number | null = null
  private connectTimer: number | null = null
  private reconnectAttempts = 0
  private shouldReconnect = false

  constructor(private readonly options: LiveRealtimeClientOptions = {}) {}

  connect() {
    if (this.socket && this.socket.readyState !== WebSocket.CLOSED) {
      return
    }

    this.shouldReconnect = true
    const socket = new WebSocket(resolveWebSocketUrl())
    this.socket = socket

    // 연결이 열리지도 닫히지도 않고 멈춰 있으면(핸드셰이크 지연 등) 강제로 닫아 재연결을 태운다.
    this.clearConnectTimer()
    this.connectTimer = window.setTimeout(() => {
      if (!this.isConnected) {
        socket.close()
      }
    }, CONNECT_TIMEOUT_MS)

    socket.addEventListener('open', () => {
      const accessToken = getStoredAccessToken()
      const headers: StompHeaders = {
        'accept-version': '1.2',
        'heart-beat': `${HEARTBEAT_OUTGOING_MS},0`,
      }

      if (accessToken) {
        headers.Authorization = `Bearer ${accessToken}`
      }

      this.sendFrame('CONNECT', headers)
    })

    socket.addEventListener('message', (event) => {
      this.handleRawMessage(String(event.data))
    })

    socket.addEventListener('close', () => {
      this.stopHeartbeat()
      this.clearConnectTimer()
      this.isConnected = false
      this.options.onDisconnect?.()
      this.scheduleReconnect()
    })

    socket.addEventListener('error', (event) => {
      this.options.onError?.(event)
    })
  }

  disconnect() {
    this.shouldReconnect = false
    this.clearReconnectTimer()
    this.clearConnectTimer()

    if (!this.socket) return

    if (this.socket.readyState === WebSocket.OPEN) {
      this.sendFrame('DISCONNECT')
    }

    this.stopHeartbeat()
    this.socket.close()
    this.socket = null
    this.subscriptions.clear()
    this.receiveBuffer = ''
    this.isConnected = false
  }

  connected() {
    return this.isConnected
  }

  subscribe(destination: string, handler: (body: unknown, frame: StompFrame) => void): StompSubscription {
    const id = `sub-${++subscriptionSequence}`
    this.subscriptions.set(id, handler)
    this.sendFrame('SUBSCRIBE', {
      id,
      destination,
      ack: 'auto',
    })

    return {
      id,
      unsubscribe: () => {
        this.subscriptions.delete(id)
        this.sendFrame('UNSUBSCRIBE', { id })
      },
    }
  }

  publish(destination: string, body: unknown) {
    this.sendFrame(
      'SEND',
      {
        destination,
        'content-type': 'application/json',
      },
      JSON.stringify(body),
    )
  }

  private handleRawMessage(message: string) {
    this.receiveBuffer += message

    const frames = this.receiveBuffer.split(NULL)
    this.receiveBuffer = frames.pop() ?? ''

    frames.forEach((rawFrame) => {
      const frame = parseFrame(rawFrame)

      if (!frame) return

      if (frame.command === 'CONNECTED') {
        this.isConnected = true
        this.reconnectAttempts = 0
        this.clearConnectTimer()
        // 재연결이면 죽은 소켓의 이전 구독 핸들러를 비우고 onConnect에서 다시 등록한다.
        this.subscriptions.clear()
        this.startHeartbeat()
        this.options.onConnect?.()
        return
      }

      if (frame.command === 'MESSAGE') {
        const subscriptionId = frame.headers.subscription
        const handler = subscriptionId ? this.subscriptions.get(subscriptionId) : null

        handler?.(parseFrameBody(frame.body), frame)
        return
      }

      if (frame.command === 'ERROR') {
        this.options.onError?.(parseFrameBody(frame.body) ?? frame.body)
      }
    })
  }

  private sendFrame(command: string, headers: StompHeaders = {}, body = '') {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return
    }

    const headerLines = Object.entries(headers).map(
      ([key, value]) => `${key}:${escapeHeader(value)}`,
    )
    this.socket.send(`${command}\n${headerLines.join('\n')}\n\n${body}${NULL}`)
  }

  private startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatTimer = window.setInterval(() => {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.socket.send('\n')
      }
    }, HEARTBEAT_OUTGOING_MS)
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer === null) {
      return
    }

    window.clearInterval(this.heartbeatTimer)
    this.heartbeatTimer = null
  }

  // 예기치 않게 끊기면(초기 연결 실패·중간 단절) 백오프로 자동 재연결한다.
  // 재연결 성공(CONNECTED) 시 onConnect가 다시 불려 앱이 구독을 다시 얹는다.
  private scheduleReconnect() {
    if (!this.shouldReconnect || this.reconnectTimer !== null) {
      return
    }

    const delay = Math.min(RECONNECT_BASE_MS * 2 ** this.reconnectAttempts, RECONNECT_MAX_MS)
    this.reconnectAttempts += 1
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null
      this.socket = null
      this.receiveBuffer = ''
      this.connect()
    }, delay)
  }

  private clearReconnectTimer() {
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  private clearConnectTimer() {
    if (this.connectTimer !== null) {
      window.clearTimeout(this.connectTimer)
      this.connectTimer = null
    }
  }
}

export const isLiveRealtimeApiEnabled = () => LIVE_REALTIME_API_ENABLED

function resolveWebSocketUrl() {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '/api'

  if (/^https?:\/\//.test(apiBaseUrl)) {
    const url = new URL(apiBaseUrl)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    url.pathname = '/ws'
    url.search = ''
    return url.toString()
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws`
}

function parseFrame(rawFrame: string): StompFrame | null {
  const normalizedFrame = rawFrame.replace(/^\n+/, '')

  if (!normalizedFrame.trim()) {
    return null
  }

  const [head = '', ...bodyParts] = normalizedFrame.split('\n\n')
  const [command = '', ...headerLines] = head.split('\n')
  const headers = headerLines.reduce<StompHeaders>((acc, line) => {
    const separatorIndex = line.indexOf(':')

    if (separatorIndex <= 0) {
      return acc
    }

    acc[line.slice(0, separatorIndex)] = unescapeHeader(line.slice(separatorIndex + 1))
    return acc
  }, {})

  return {
    command,
    headers,
    body: bodyParts.join('\n\n'),
  }
}

function parseFrameBody(body: string) {
  if (!body) {
    return null
  }

  try {
    return JSON.parse(body) as unknown
  } catch {
    return body
  }
}

function escapeHeader(value: string) {
  return value.replace(/\\/g, '\\\\').replace(/\n/g, '\\n').replace(/:/g, '\\c')
}

function unescapeHeader(value: string) {
  return value.replace(/\\c/g, ':').replace(/\\n/g, '\n').replace(/\\\\/g, '\\')
}
