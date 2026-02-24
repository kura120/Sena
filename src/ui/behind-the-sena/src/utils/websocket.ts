export type WebSocketMessage<T = unknown> = {
  type: string;
  data?: T;
  timestamp?: string;
};

export type SubscriptionRequest = {
  type: "subscribe";
  channels: string[];
};

type SocketOptions = {
  onMessage?: (payload: WebSocketMessage) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (event: Event) => void;
};

type MessageHandler = (payload: WebSocketMessage) => void;

let cachedWsBaseUrl: string | null = null;
let wsBaseUrlPromise: Promise<string> | null = null;

// ── Singleton WebSocket ──────────────────────────────────────────────────────
// One persistent connection for the entire app runtime. Components register
// handlers via addMessageHandler() on mount and unregister on unmount — the
// socket itself is never closed by individual components.

let _sharedSocket: WebSocket | null = null;
let _sharedSocketPath = "/ws";
let _sharedChannels: string[] = ["processing", "memory", "personality"];
const _messageHandlers = new Set<MessageHandler>();
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let _connecting = false;
const _RECONNECT_DELAY_MS = 3000;

function _scheduleReconnect(): void {
  if (_reconnectTimer) return;
  _reconnectTimer = setTimeout(() => {
    _reconnectTimer = null;
    void _ensureConnected();
  }, _RECONNECT_DELAY_MS);
}

async function _ensureConnected(): Promise<void> {
  if (_connecting) return;
  if (
    _sharedSocket &&
    (_sharedSocket.readyState === WebSocket.OPEN ||
      _sharedSocket.readyState === WebSocket.CONNECTING)
  )
    return;

  _connecting = true;
  try {
    const baseUrl = await getWsBaseUrl();
    const normalizedBase = baseUrl.replace(/\/+$/, "");
    const normalizedPath = _sharedSocketPath.startsWith("/")
      ? _sharedSocketPath
      : `/${_sharedSocketPath}`;
    const socket = new WebSocket(`${normalizedBase}${normalizedPath}`);

    socket.addEventListener("open", () => {
      _connecting = false;
      sendSubscription(socket, _sharedChannels);
    });

    socket.addEventListener("message", (event) => {
      const payload = safeParse(event.data);
      _messageHandlers.forEach((h) => h(payload));
    });

    socket.addEventListener("close", () => {
      _connecting = false;
      _sharedSocket = null;
      // Auto-reconnect as long as there are active handlers
      if (_messageHandlers.size > 0) {
        _scheduleReconnect();
      }
    });

    socket.addEventListener("error", () => {
      _connecting = false;
    });

    _sharedSocket = socket;
  } catch {
    _connecting = false;
    _scheduleReconnect();
  }
}

/**
 * Ensure the singleton WebSocket is connected.
 * Safe to call multiple times — only one connection is ever created.
 */
export async function connectSharedSocket(
  path = "/ws",
  channels = ["processing", "memory", "personality"],
): Promise<void> {
  _sharedSocketPath = path;
  _sharedChannels = channels;
  return _ensureConnected();
}

/**
 * Register a message handler on the singleton socket.
 * Returns an unsubscribe function — call it on component unmount.
 * The socket itself stays alive after unsubscribe.
 */
export function addMessageHandler(handler: MessageHandler): () => void {
  _messageHandlers.add(handler);
  // Ensure connected when the first handler registers
  void _ensureConnected();
  return () => {
    _messageHandlers.delete(handler);
  };
}

export async function getWsBaseUrl(): Promise<string> {
  if (cachedWsBaseUrl) {
    return cachedWsBaseUrl;
  }

  if (!wsBaseUrlPromise) {
    wsBaseUrlPromise = (async () => {
      if (window?.sena?.getWsBaseUrl) {
        try {
          const baseUrl = await window.sena.getWsBaseUrl();
          cachedWsBaseUrl = baseUrl;
          return baseUrl;
        } catch {
          // Fall through to default
        }
      }

      cachedWsBaseUrl = "ws://127.0.0.1:8000";
      return cachedWsBaseUrl;
    })();
  }

  return wsBaseUrlPromise;
}

export function clearWsBaseUrlCache(): void {
  cachedWsBaseUrl = null;
  wsBaseUrlPromise = null;
}

export async function openWebSocket(
  path: string,
  options: SocketOptions = {},
): Promise<WebSocket> {
  const baseUrl = await getWsBaseUrl();
  const normalizedBase = baseUrl.replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const socket = new WebSocket(`${normalizedBase}${normalizedPath}`);

  if (options.onOpen) {
    socket.addEventListener("open", options.onOpen);
  }

  if (options.onClose) {
    socket.addEventListener("close", options.onClose);
  }

  if (options.onError) {
    socket.addEventListener("error", options.onError);
  }

  if (options.onMessage) {
    socket.addEventListener("message", (event) => {
      options.onMessage?.(safeParse(event.data));
    });
  }

  return socket;
}

export function sendSubscription(socket: WebSocket, channels: string[]): void {
  const payload: SubscriptionRequest = {
    type: "subscribe",
    channels,
  };

  socket.send(JSON.stringify(payload));
}

export function closeWebSocket(socket: WebSocket): void {
  if (
    socket.readyState === WebSocket.OPEN ||
    socket.readyState === WebSocket.CONNECTING
  ) {
    socket.close();
  }
}

function safeParse(value: string): WebSocketMessage {
  try {
    return JSON.parse(value);
  } catch {
    return { type: "unknown", data: value };
  }
}
