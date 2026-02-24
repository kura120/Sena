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

let cachedWsBaseUrl: string | null = null;
let wsBaseUrlPromise: Promise<string> | null = null;

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
