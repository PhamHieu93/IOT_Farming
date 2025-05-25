import React, { createContext, useContext, useState, useEffect, useRef } from 'react';

const WebSocketContext = createContext(null);

export const useWebSocket = () => useContext(WebSocketContext);

export const WebSocketProvider = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef(null);
  
  // Initialize WebSocket connection
  useEffect(() => {
    // Replace with your actual WebSocket server URL
    const wsUrl = "ws://localhost:5432";
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;
    
    socket.onopen = () => {
      console.log("WebSocket connected");
      setIsConnected(true);
    };
    
    socket.onclose = () => {
      console.log("WebSocket disconnected");
      setIsConnected(false);
      
      // Try to reconnect after a delay
      setTimeout(() => {
        console.log("Attempting to reconnect...");
        // This will trigger the useEffect again
        setIsConnected(false);
      }, 5000);
    };
    
    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
    
    return () => {
      if (socket) {
        socket.close();
      }
    };
  }, []);
  
  // Send a message through the WebSocket
  const sendMessage = (message) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
      return true;
    } else {
      console.error("WebSocket is not connected");
      return false;
    }
  };
  
  // Add a listener for specific message types
  const addMessageListener = (callback) => {
    if (socketRef.current) {
      const messageHandler = (event) => {
        const message = JSON.parse(event.data);
        callback(message);
      };
      
      socketRef.current.addEventListener('message', messageHandler);
      
      // Return function to remove the listener
      return () => {
        if (socketRef.current) {
          socketRef.current.removeEventListener('message', messageHandler);
        }
      };
    }
    return () => {};
  };
  
  const value = {
    isConnected,
    sendMessage,
    addMessageListener
  };
  
  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};