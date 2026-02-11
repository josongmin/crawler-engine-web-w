type WsHandler = (data: WsMessage) => void;

export interface WsMessage {
  type:
    | "log"
    | "status"
    | "progress"
    | "complete"
    | "error"
    | "node_status"
    | "node_log"
    | "node_states"
    | "run_started"
    | "run_completed"
    | "run_error";
  timestamp: string;
  data: Record<string, unknown>;
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null;
}

function isWsMessage(v: unknown): v is WsMessage {
  if (!isRecord(v)) return false;
  const type = v.type;
  const timestamp = v.timestamp;
  const data = v.data;
  const validTypes = [
    "log",
    "status",
    "progress",
    "complete",
    "error",
    "node_status",
    "node_log",
    "node_states",
    "run_started",
    "run_completed",
    "run_error",
  ];
  return typeof type === "string" && validTypes.includes(type) && typeof timestamp === "string" && isRecord(data);
}

/**
 * Auto-reconnecting WebSocket wrapper.
 */
export function createWs(path: string, onMessage: WsHandler) {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${protocol}//${location.host}${path}`;

  let ws: WebSocket | null = null;
  let retries = 0;
  let closed = false;

  function connect() {
    ws = new WebSocket(url);

    ws.onopen = () => {
      retries = 0;
    };

    ws.onmessage = (e) => {
      try {
        if (typeof e.data !== "string") return;
        const parsed = JSON.parse(e.data) as unknown;
        if (isWsMessage(parsed)) {
          onMessage(parsed);
        }
      } catch {
        /* ignore malformed messages */
      }
    };

    ws.onclose = () => {
      if (closed) return;
      const delay = Math.min(1000 * 2 ** retries, 10_000);
      retries++;
      setTimeout(connect, delay);
    };

    ws.onerror = () => ws?.close();
  }

  connect();

  return {
    close() {
      closed = true;
      ws?.close();
    },
    send(data: unknown) {
      ws?.send(JSON.stringify(data));
    },
  };
}
