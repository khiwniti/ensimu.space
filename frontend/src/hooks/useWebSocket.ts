/**
 * React hook for WebSocket connection management.
 * Provides real-time communication with the backend for workflow updates and HITL checkpoints.
 * Uses standardized protocol for consistent message handling.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  StandardWebSocketMessage,
  WebSocketConnectionParams,
  MessageType,
  buildWebSocketUrl,
  parseWebSocketMessage,
  createHeartbeatMessage,
  createStandardMessage,
  validateMessage,
  isValidationError,
  isHandlerError,
  extractErrorDetails,
  getWebSocketBaseUrl,
} from '../utils/websocketUtils';

export interface WebSocketOptions {
  connectionParams: WebSocketConnectionParams;
  baseUrl?: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  onMessage?: (message: StandardWebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  onValidationError?: (error: string, details?: string) => void;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error';
  lastMessage: StandardWebSocketMessage | null;
  sendMessage: (type: MessageType, data: Record<string, any>) => boolean;
  sendRawMessage: (message: StandardWebSocketMessage) => boolean;
  disconnect: () => void;
  reconnect: () => void;
  stats: {
    messagesSent: number;
    messagesReceived: number;
    reconnectAttempts: number;
    validationErrors: number;
    handlerErrors: number;
    lastConnectedAt: Date | null;
    lastDisconnectedAt: Date | null;
  };
}

export const useWebSocket = (options: WebSocketOptions): UseWebSocketReturn => {
  const {
    connectionParams,
    baseUrl,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
    heartbeatInterval = 30000,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    onValidationError,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [lastMessage, setLastMessage] = useState<StandardWebSocketMessage | null>(null);
  const [stats, setStats] = useState({
    messagesSent: 0,
    messagesReceived: 0,
    reconnectAttempts: 0,
    validationErrors: 0,
    handlerErrors: 0,
    lastConnectedAt: null as Date | null,
    lastDisconnectedAt: null as Date | null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const shouldReconnectRef = useRef(true);

  // Build standardized WebSocket URL
  const buildUrl = useCallback(() => {
    const wsBaseUrl = baseUrl || getWebSocketBaseUrl();
    return buildWebSocketUrl(wsBaseUrl, connectionParams);
  }, [baseUrl, connectionParams]);

  // Send heartbeat message
  const sendHeartbeat = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const heartbeatMessage = createHeartbeatMessage();
      wsRef.current.send(JSON.stringify(heartbeatMessage));
    }
  }, []);

  // Start heartbeat timer
  const startHeartbeat = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearInterval(heartbeatTimeoutRef.current);
    }

    heartbeatTimeoutRef.current = setInterval(sendHeartbeat, heartbeatInterval);
  }, [sendHeartbeat, heartbeatInterval]);

  // Stop heartbeat timer
  const stopHeartbeat = useCallback(() => {
    if (heartbeatTimeoutRef.current) {
      clearInterval(heartbeatTimeoutRef.current);
      heartbeatTimeoutRef.current = null;
    }
  }, []);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    setConnectionState('connecting');

    try {
      const wsUrl = buildUrl();
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        setIsConnected(true);
        setConnectionState('connected');
        setStats(prev => ({
          ...prev,
          lastConnectedAt: new Date(),
        }));

        reconnectAttemptsRef.current = 0;
        startHeartbeat();
        onConnect?.();
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message = parseWebSocketMessage(event.data);
          
          if (!message) {
            setStats(prev => ({
              ...prev,
              validationErrors: prev.validationErrors + 1,
            }));
            return;
          }

          setLastMessage(message);
          setStats(prev => ({
            ...prev,
            messagesReceived: prev.messagesReceived + 1,
          }));

          // Handle error messages
          if (message.type === MessageType.ERROR) {
            const errorDetails = extractErrorDetails(message);
            
            if (isValidationError(message)) {
              setStats(prev => ({
                ...prev,
                validationErrors: prev.validationErrors + 1,
              }));
              onValidationError?.(errorDetails.error, errorDetails.details);
            } else if (isHandlerError(message)) {
              setStats(prev => ({
                ...prev,
                handlerErrors: prev.handlerErrors + 1,
              }));
            }
          }

          // Don't call onMessage for heartbeat responses
          if (message.type !== MessageType.HEARTBEAT) {
            onMessage?.(message);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          setStats(prev => ({
            ...prev,
            validationErrors: prev.validationErrors + 1,
          }));
        }
      };

      wsRef.current.onclose = () => {
        setIsConnected(false);
        setConnectionState('disconnected');
        setStats(prev => ({
          ...prev,
          lastDisconnectedAt: new Date(),
        }));

        stopHeartbeat();
        onDisconnect?.();

        // Attempt to reconnect if enabled and not manually disconnected
        if (shouldReconnectRef.current && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          setStats(prev => ({
            ...prev,
            reconnectAttempts: prev.reconnectAttempts + 1,
          }));

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };

      wsRef.current.onerror = (error) => {
        setConnectionState('error');
        onError?.(error);
      };

    } catch (error) {
      setConnectionState('error');
      console.error('Error creating WebSocket connection:', error);
    }
  }, [buildUrl, onConnect, onMessage, onDisconnect, onError, startHeartbeat, stopHeartbeat, maxReconnectAttempts, reconnectInterval]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    stopHeartbeat();

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setConnectionState('disconnected');
  }, [stopHeartbeat]);

  // Reconnect to WebSocket
  const reconnect = useCallback(() => {
    disconnect();
    shouldReconnectRef.current = true;
    reconnectAttemptsRef.current = 0;
    
    // Small delay before reconnecting
    setTimeout(() => {
      connect();
    }, 100);
  }, [disconnect, connect]);

  // Send message through WebSocket with type and data
  const sendMessage = useCallback((type: MessageType, data: Record<string, any>): boolean => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket is not connected. Cannot send message.');
      return false;
    }

    try {
      const message = createStandardMessage(type, data);
      wsRef.current.send(JSON.stringify(message));
      
      setStats(prev => ({
        ...prev,
        messagesSent: prev.messagesSent + 1,
      }));

      return true;
    } catch (error) {
      console.error('Error sending WebSocket message:', error);
      return false;
    }
  }, []);

  // Send raw message through WebSocket
  const sendRawMessage = useCallback((message: StandardWebSocketMessage): boolean => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket is not connected. Cannot send message.');
      return false;
    }

    try {
      // Validate message before sending
      if (!validateMessage(message)) {
        console.error('Invalid message structure:', message);
        return false;
      }

      wsRef.current.send(JSON.stringify(message));
      
      setStats(prev => ({
        ...prev,
        messagesSent: prev.messagesSent + 1,
      }));

      return true;
    } catch (error) {
      console.error('Error sending WebSocket message:', error);
      return false;
    }
  }, []);

  // Connect on mount
  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();

    // Cleanup on unmount
    return () => {
      shouldReconnectRef.current = false;
      disconnect();
    };
  }, [connect, disconnect]);

  // Reconnect when URL or params change
  useEffect(() => {
    if (isConnected) {
      reconnect();
    }
  }, [url, params, isConnected, reconnect]);

  return {
    isConnected,
    connectionState,
    lastMessage,
    sendMessage,
    sendRawMessage,
    disconnect,
    reconnect,
    stats,
  };
};
