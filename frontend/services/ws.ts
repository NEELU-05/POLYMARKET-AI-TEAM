// frontend/services/ws.ts
const WS_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/^http/, "ws");

type WsCallback = (data: any) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private listeners: Record<string, Set<WsCallback>> = {};
  private isConnecting = false;

  constructor() {
    // Determine if we're in browser
    if (typeof window !== "undefined") {
      this.connect();
    }
  }

  private connect() {
    if (this.ws || this.isConnecting) return;
    this.isConnecting = true;
    
    try {
      this.ws = new WebSocket(`${WS_BASE}/api/ws/events`);

      this.ws.onopen = () => {
        this.isConnecting = false;
        console.log("WebSocket connected");
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.notifyListeners(data.type || "unknown", data);
          // Also notify specific topics if it's an event_bus message
          if (data.type === "event_bus" && data.topic) {
            this.notifyListeners(`topic:${data.topic}`, data);
          }
        } catch (e) {
          console.error("WebSocket message parse error", e);
        }
      };

      this.ws.onclose = () => {
        this.isConnecting = false;
        this.ws = null;
        this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        this.isConnecting = false;
        this.ws?.close();
      };
    } catch (e) {
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (!this.reconnectTimer && typeof window !== "undefined") {
      this.reconnectTimer = setTimeout(() => {
        this.reconnectTimer = null;
        this.connect();
      }, 3000);
    }
  }

  public subscribe(type: string, callback: WsCallback) {
    if (!this.listeners[type]) {
      this.listeners[type] = new Set();
    }
    this.listeners[type].add(callback);
    return () => this.unsubscribe(type, callback);
  }

  public unsubscribe(type: string, callback: WsCallback) {
    if (this.listeners[type]) {
      this.listeners[type].delete(callback);
    }
  }

  private notifyListeners(type: string, data: any) {
    if (this.listeners[type]) {
      this.listeners[type].forEach(cb => cb(data));
    }
    // generic listener
    if (this.listeners["*"]) {
      this.listeners["*"].forEach(cb => cb(data));
    }
  }
}

export const wsService = new WebSocketService();
