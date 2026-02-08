type WsHandler = (data: WsMessage) => void;

export interface WsMessage {
  type: "log" | "status" | "progress" | "complete" | "error";
  timestamp: string;
  data: Record<string, unknown>;
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
        const msg: WsMessage = JSON.parse(e.data);
        onMessage(msg);
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
