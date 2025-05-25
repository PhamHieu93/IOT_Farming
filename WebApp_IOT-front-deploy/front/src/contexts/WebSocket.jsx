import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
// Import Socket.IO client
import { io } from 'socket.io-client';

const WebSocketContext = createContext(null);

export const useWebSocket = () => useContext(WebSocketContext);

export const WebSocketProvider = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const socketRef = useRef(null);

  const connect = () => {
    // Disconnect existing connection if any
    if (socketRef.current) {
      socketRef.current.disconnect();
    }
    
    console.log("Attempting Socket.IO connection to http://localhost:3000");
    
    // Create Socket.IO connection
    const socket = io('http://localhost:3000', {
      reconnection: true,
      reconnectionAttempts: Infinity
    });
    
    socketRef.current = socket;
    
    socket.on('connect', () => {
      console.log("Socket.IO connected!");
      setIsConnected(true);
      
      // Send a test ping once connected
      socket.emit('ping');
    });
    
    socket.on('disconnect', () => {
      console.log("Socket.IO disconnected");
      setIsConnected(false);
    });
    
    socket.on('connect_error', (err) => {
      console.error("Connection error:", err.message);
    });
    
    // Listen for the pong response
    socket.on('pong', (data) => {
      console.log("Received pong:", data);
      setLastMessage(data);
    });
    
    // Listen for all messages
    socket.onAny((event, ...args) => {
      console.log(`Event ${event} received:`, args[0]);
      setLastMessage({ event, data: args[0] });
    });
  };
  
  // Initialize connection
  useEffect(() => {
    connect();
    
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);
  
  // Send a message through Socket.IO
  const sendMessage = (event, message) => {
    if (socketRef.current && socketRef.current.connected) {
      socketRef.current.emit(event, message);
      return true;
    } else {
      console.error("Socket.IO is not connected");
      return false;
    }
  };
  
  // Add a listener for specific message types
  const addMessageListener = (event, callback) => {
    if (socketRef.current) {
      socketRef.current.on(event, callback);
      
      // Return function to remove the listener
      return () => {
        if (socketRef.current) {
          socketRef.current.off(event, callback);
        }
      };
    }
    return () => {};
  };
  
  const value = {
    isConnected,
    lastMessage,
    sendMessage,
    addMessageListener,
    reconnect: connect
  };
  
  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};

export default WebSocketProvider;