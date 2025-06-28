import { useEffect, useRef, useState, useCallback } from 'react';

interface WebSocketMessage {
  topic: string;
  timestamp: string;
  data: Record<string, unknown>;
}

interface UseWebSocketOptions {
  topics?: string[];
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

interface AIDecision {
  decision_id: number;
  symbol: string;
  action: string;
  confidence: number;
  quantity: number;
  suggested_price: number;
  reasoning: string;
  timestamp: string;
}

interface TradeExecution {
  trade_id: number;
  symbol: string;
  action: string;
  quantity: number;
  price: number;
  timestamp: string;
  status: string;
}

interface EngineStatus {
  is_running: boolean;
  last_run: string;
  next_run: string;
  run_count: number;
  errors: string[];
}

interface PortfolioUpdate {
  total_value: number;
  cash_balance: number;
  profit_loss: number;
  profit_loss_percent: number;
  holdings: Array<{
    symbol: string;
    quantity: number;
    average_price: number;
    current_price: number;
    market_value: number;
    profit_loss: number;
    profit_loss_percent: number;
  }>;
}

export const useWebSocket = (options: UseWebSocketOptions = {}) => {
  const {
    topics = [],
    onMessage,
    onConnect,
    onDisconnect,
    reconnectInterval = 10000, // Increased to 10 seconds
    maxReconnectAttempts = 3 // Reduced attempts
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [reconnectCount, setReconnectCount] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const clientIdRef = useRef<string | null>(null);

  // Generate unique client ID
  useEffect(() => {
    clientIdRef.current = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  const sendMessage = useCallback((message: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  const subscribe = useCallback((topicsToSubscribe: string[]) => {
    return sendMessage({
      type: 'subscribe',
      topics: topicsToSubscribe
    });
  }, [sendMessage]);

  const unsubscribe = useCallback((topicsToUnsubscribe: string[]) => {
    return sendMessage({
      type: 'unsubscribe',
      topics: topicsToUnsubscribe
    });
  }, [sendMessage]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    setConnectionState('connecting');

    try {
      const wsUrl = `ws://localhost:8001/ws/${clientIdRef.current}`;
      console.log('🔌 Attempting WebSocket connection to:', wsUrl);
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('🔗 WebSocket connected');
        setIsConnected(true);
        setConnectionState('connected');
        setReconnectCount(0);
        
        // Subscribe to topics
        if (topics.length > 0) {
          subscribe(topics);
        }
        
        onConnect?.();
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
          onMessage?.(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log('🔌 WebSocket disconnected. Code:', event.code, 'Reason:', event.reason);
        setIsConnected(false);
        setConnectionState('disconnected');
        onDisconnect?.();

        // Only attempt to reconnect if it wasn't a manual close and we haven't exceeded max attempts
        if (event.code !== 1000 && reconnectCount < maxReconnectAttempts) {
          setReconnectCount(prev => prev + 1);
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`🔄 Attempting to reconnect... (${reconnectCount + 1}/${maxReconnectAttempts})`);
            connect();
          }, reconnectInterval);
        } else if (reconnectCount >= maxReconnectAttempts) {
          console.log('❌ Max reconnection attempts reached');
          setConnectionState('error');
        }
      };

      wsRef.current.onerror = (error) => {
        console.warn('WebSocket error (connection issue, will retry):', error.type);
        // Don't immediately set error state, let onclose handle reconnection
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionState('error');
    }
  }, [topics, onConnect, onMessage, onDisconnect, reconnectCount, maxReconnectAttempts, reconnectInterval, subscribe]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setConnectionState('disconnected');
    setReconnectCount(0);
  }, []);

  const ping = useCallback(() => {
    return sendMessage({
      type: 'ping',
      timestamp: new Date().toISOString()
    });
  }, [sendMessage]);

  // Auto-connect on mount with delay
  useEffect(() => {
    const connectToServer = () => {
      // Add a delay to ensure backend is ready
      const timer = setTimeout(() => {
        connect();
      }, 3000); // 3 second delay
      
      return () => clearTimeout(timer);
    };
    
    const cleanup = connectToServer();

    // Cleanup on unmount
    return () => {
      if (cleanup) cleanup();
      disconnect();
    };
  }, [connect, disconnect]);

  // Ping interval to keep connection alive
  useEffect(() => {
    if (!isConnected) return;

    const pingInterval = setInterval(() => {
      ping();
    }, 30000); // Ping every 30 seconds

    return () => clearInterval(pingInterval);
  }, [isConnected, ping]);

  return {
    isConnected,
    connectionState,
    lastMessage,
    reconnectCount,
    connect,
    disconnect,
    sendMessage,
    subscribe,
    unsubscribe,
    ping
  };
};

// Hook for trading-specific WebSocket updates
export const useTradingWebSocket = () => {
  const [aiDecisions, setAiDecisions] = useState<AIDecision[]>([]);
  const [tradeExecutions, setTradeExecutions] = useState<TradeExecution[]>([]);
  const [engineStatus, setEngineStatus] = useState<EngineStatus | null>(null);
  const [portfolioUpdates, setPortfolioUpdates] = useState<PortfolioUpdate | null>(null);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (message.topic) {
      case 'ai_decisions':
        if (message.data.type === 'new_decision') {
          setAiDecisions(prev => [message.data.decision as AIDecision, ...prev.slice(0, 9)]); // Keep last 10
        }
        break;
      
      case 'trades':
        if (message.data.type === 'trade_executed') {
          setTradeExecutions(prev => [message.data.trade as TradeExecution, ...prev.slice(0, 9)]); // Keep last 10
        }
        break;
      
      case 'engine_status':
        if (message.data.type === 'status_change') {
          setEngineStatus(message.data.status as EngineStatus);
        }
        break;
      
      case 'portfolio':
        if (message.data.type === 'portfolio_updated') {
          setPortfolioUpdates(message.data.portfolio as PortfolioUpdate);
        }
        break;
    }
  }, []);

  const { isConnected, connectionState, ...wsControls } = useWebSocket({
    topics: ['ai_decisions', 'trades', 'engine_status', 'portfolio'],
    onMessage: handleMessage
  });

  return {
    isConnected,
    connectionState,
    aiDecisions,
    tradeExecutions,
    engineStatus,
    portfolioUpdates,
    ...wsControls
  };
};
