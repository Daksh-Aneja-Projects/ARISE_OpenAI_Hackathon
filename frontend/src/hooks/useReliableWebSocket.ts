/**
 * useReliableWebSocket — production-grade WebSocket hook with:
 *
 *   - Exponential backoff reconnect (1s → 2s → 4s → 8s → 16s → 30s cap)
 *   - Server ping/pong keepalive (responds to {"type":"ping"} with "pong")
 *   - Jitter on reconnect delays (prevents thundering-herd on server restart)
 *   - Max reconnect attempts (configurable, default 10)
 *   - Visibility API integration: reconnects when tab becomes visible again
 *   - Clean teardown on unmount / manual close
 *
 * Usage:
 *   const { lastMessage, status, reconnectCount } = useReliableWebSocket(url, onMessage);
 *
 * status: 'connecting' | 'open' | 'closing' | 'closed' | 'failed'
 */
import { useEffect, useRef, useCallback, useState } from 'react';

export type WSStatus = 'connecting' | 'open' | 'closing' | 'closed' | 'failed';

interface UseReliableWSOptions {
  maxRetries?: number;        // Default: 10
  baseDelayMs?: number;       // Default: 1000 (1s)
  maxDelayMs?: number;        // Default: 30000 (30s)
  enabled?: boolean;          // Default: true — set false to pause connection
}

interface UseReliableWSResult {
  status: WSStatus;
  lastMessage: unknown;
  reconnectCount: number;
  send: (msg: string) => void;
  close: () => void;
}

function addJitter(ms: number): number {
  // ±20% jitter
  return ms * (0.8 + Math.random() * 0.4);
}

export function useReliableWebSocket(
  url: string | null,
  onMessage?: (data: unknown) => void,
  options: UseReliableWSOptions = {}
): UseReliableWSResult {
  const {
    maxRetries   = 10,
    baseDelayMs  = 1000,
    maxDelayMs   = 30000,
    enabled      = true,
  } = options;

  const [status, setStatus] = useState<WSStatus>('closed');
  const [lastMessage, setLastMessage] = useState<unknown>(null);
  const [reconnectCount, setReconnectCount] = useState(0);

  const wsRef        = useRef<WebSocket | null>(null);
  const retriesRef   = useRef(0);
  const mountedRef   = useRef(true);
  const timerRef     = useRef<ReturnType<typeof setTimeout> | null>(null);
  const manualClose  = useRef(false);

  const clearTimer = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  function connect() {
    if (!url || !enabled || !mountedRef.current) return;
    if (wsRef.current && wsRef.current.readyState <= WebSocket.OPEN) return;

    setStatus('connecting');
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) { ws.close(); return; }
      retriesRef.current = 0;
      setReconnectCount(0);
      setStatus('open');
    };

    ws.onmessage = (evt) => {
      if (!mountedRef.current) return;
      try {
        const data = JSON.parse(evt.data);

        // Respond to server keepalive pings
        if (data?.type === 'ping') {
          if (ws.readyState === WebSocket.OPEN) ws.send('pong');
          return;
        }

        setLastMessage(data);
        onMessage?.(data);
      } catch {
        // Non-JSON message (e.g. raw "pong") — ignore
      }
    };

    ws.onerror = () => {
      // onclose fires right after onerror, so reconnect logic is in onclose
    };

    ws.onclose = (evt) => {
      if (!mountedRef.current) return;
      setStatus('closed');
      wsRef.current = null;

      // Don't reconnect if manually closed or max retries reached
      if (manualClose.current || retriesRef.current >= maxRetries) {
        setStatus(retriesRef.current >= maxRetries ? 'failed' : 'closed');
        return;
      }

      // Exponential backoff with jitter
      const delay = addJitter(
        Math.min(baseDelayMs * Math.pow(2, retriesRef.current), maxDelayMs)
      );
      retriesRef.current += 1;
      setReconnectCount(retriesRef.current);

      timerRef.current = setTimeout(() => {
        if (mountedRef.current && !manualClose.current) { connect(); }
      }, delay);
    };
  }

  // Initial connect + reconnect on url/enabled change
  useEffect(() => {
    mountedRef.current = true;
    manualClose.current = false;
    retriesRef.current = 0;
    if (enabled && url) connect();
    return () => {
      mountedRef.current = false;
      clearTimer();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [url, enabled, connect]);

  // Reconnect when tab becomes visible (catches offline → online transitions)
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible' && !manualClose.current) {
        if (!wsRef.current || wsRef.current.readyState > WebSocket.OPEN) {
          retriesRef.current = 0;
          connect();
        }
      }
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, [connect]);

  const send = useCallback((msg: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(msg);
    }
  }, []);

  const close = useCallback(() => {
    manualClose.current = true;
    clearTimer();
    wsRef.current?.close();
    setStatus('closed');
  }, []);

  return { status, lastMessage, reconnectCount, send, close };
}

/** Convenience: build a WS URL from an HTTP/HTTPS base URL + path. */
export function buildWsUrl(basePath: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}${basePath}`;
}
