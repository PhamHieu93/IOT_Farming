import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
// Import Socket.IO client
import { io } from 'socket.io-client';

const WebSocketContext = createContext(null);

export const useWebSocket = () => useContext(WebSocketContext);

export const WebSocketProvider = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [sectorStates, setSectorStates] = useState({});
  
  // Add state for sensor data
  const [sensorData, setSensorData] = useState({
    temperature: null,
    humidity: null,
    light: null,
    lastUpdated: null
  });
  
  const socketRef = useRef(null);

  const connect = () => {
    // Disconnect existing connection if any
    if (socketRef.current) {
      socketRef.current.disconnect();
    }    
    
    // Get the backend URL from environment variable or use a default
    //const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || window.location.origin;
    const BACKEND_URL = 'http://localhost:3000';
    console.log("Attempting Socket.IO connection to", BACKEND_URL);
    
    // Create Socket.IO connection
    const socket = io(BACKEND_URL, {
      path: '/socket.io/',
      transports: ['websocket', 'polling'], // Allow fallback to polling
      reconnection: true,
      reconnectionAttempts: Infinity,
      timeout: 10000 // Increase timeout to 10s
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
      // Listen for command responses
    socket.on('command_response', (response) => {
      console.log('Command response:', response);
      setLastMessage({ event: 'command_response', data: response });
    });

    socket.on('type_change_response', (response) => {
      console.log('Type change response:', response);
      setLastMessage({ event: 'type_change_response', data: response });
    });
    
    // Listen for all messages
    socket.onAny((event, ...args) => {
      console.log(`Event ${event} received:`, args[0]);
      setLastMessage({ event, data: args[0] });
    });
    
    // Add listeners for sensor data updates
    socket.on('temperature_data', (data) => {
      console.log('Temperature data received:', data);
      if (data && data.data) {
        setSensorData(prev => ({
          ...prev,
          temperature: data.data.value,
          lastUpdated: new Date()
        }));
      }
    });
    
    socket.on('humidity_data', (data) => {
      console.log('Humidity data received:', data);
      if (data && data.data) {
        setSensorData(prev => ({
          ...prev,
          humidity: data.data.value,
          lastUpdated: new Date()
        }));
      }
    });
    
    socket.on('light_data', (data) => {
      console.log('Light data received:', data);
      if (data && data.data) {
        setSensorData(prev => ({
          ...prev,
          light: data.data.value,
          lastUpdated: new Date()
        }));
      }
    });
    
    // Combined sensor update from hardware
    socket.on('sensor_update', (data) => {
      console.log('Sensor update received:', data);
      if (data && data.data) {
        const updateData = data.data;
        setSensorData(prev => ({
          ...prev,
          temperature: updateData.temperature || prev.temperature,
          humidity: updateData.humidity || prev.humidity,
          light: updateData.light || prev.light,
          sector: updateData.sector,
          lastUpdated: new Date()
        }));
      }
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
    // Fix the sendDeviceCommand function to handle additional payload
    const sendDeviceCommand = (sector, device, status, type, additionalData = {}) => {
    if (socketRef.current && socketRef.current.connected) {
      console.log("Sending device command:", { sector, device, status, type, ...additionalData });
      socketRef.current.emit('device_command', {
        sector,
        device,
        status,
        type,
        ...additionalData
      }, (response) => {
        // Handle acknowledgment
        if (response && response.error) {
          console.error("Command error:", response.error);
        } else {
          console.log("Command successfully sent:", response);
        }
      });
      return true;
    } else {
      console.error("Socket.IO is not connected");
      // Try to reconnect
      connect();
      return false;
    }
  };

  // Function to change control type with additional data
  const changeControlType = (sector, device, type, status, additionalData = {}) => {
    if (socketRef.current && socketRef.current.connected) {
      socketRef.current.emit('control_type_change', {
        sector,
        device,
        type,
        status,
        ...additionalData
      });
      return true;
    } else {
      console.error("Socket.IO is not connected");
      // Try to reconnect
      connect();
      return false;
    }
  };

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
    sensorData,
    sectorStates,
    setSectorStates,
    sendMessage,
    sendDeviceCommand,
    changeControlType,
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