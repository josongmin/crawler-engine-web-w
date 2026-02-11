import { useEffect, useRef } from "react";
import { createWs, type WsMessage } from "@/shared/api/ws";
import { useWorkflowStore } from "@/entities/workflow/model/store";

interface RunOverlayProps {
  runId: string;
  onComplete?: () => void;
}

export function RunOverlay({ runId, onComplete }: RunOverlayProps) {
  const updateNodeStatus = useWorkflowStore((s) => s.updateNodeStatus);
  const setIsRunning = useWorkflowStore((s) => s.setIsRunning);
  const mountedRef = useRef(true);
  const wsRef = useRef<ReturnType<typeof createWs> | null>(null);

  useEffect(() => {
    mountedRef.current = true;

    const ws = createWs(`/ws/workflow-runs/${runId}`, (msg: WsMessage) => {
      if (!mountedRef.current) return;

      switch (msg.type) {
        case "node_status": {
          const { node_id, status } = msg.data as { node_id: string; status: string };
          updateNodeStatus(node_id, status);
          break;
        }
        case "run_completed":
        case "run_error": {
          setIsRunning(false);
          onComplete?.();
          break;
        }
      }
    });

    wsRef.current = ws;

    return () => {
      mountedRef.current = false;
      ws.close();
    };
  }, [runId, updateNodeStatus, setIsRunning, onComplete]);

  return null;
}
