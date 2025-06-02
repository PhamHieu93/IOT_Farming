import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';

// Event emitter for sensor data alerts
const sensorDataListeners = new Set();

export const subscribeSensorData = (callback) => {
  sensorDataListeners.add(callback);
  return () => sensorDataListeners.delete(callback);
};

export const publishSensorData = (data) => {
  sensorDataListeners.forEach(callback => callback(data));
};

// Cache management for auth token
let cachedToken = null;
let tokenExpiry = null;

/**
 * Get authentication token with caching
 */
async function getToken(forceRefresh = false) {
  if (!forceRefresh && cachedToken && tokenExpiry && Date.now() < tokenExpiry) {
    console.log('Using cached token:', cachedToken);
    return cachedToken;
  }

  try {
    const response = await fetch('https://app.coreiot.io/api/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        username: 'Phinguu@gmail.com',
        password: 'phingu',
      }),
    });

    if (!response.ok) {
      throw new Error(`Login failed: ${response.status}`);
    }

    const data = await response.json();
    cachedToken = data.token;
    tokenExpiry = Date.now() + (30 * 60 * 1000); 
    console.log('New token received:', cachedToken);

    return cachedToken;
  } catch (error) {
    console.error('Failed to get token:', error);
    throw error;
  }
}

/**
 * Fetch telemetry data with retry mechanism
 */
async function fetchTelemetryData(entityType, entityId, startTs, endTs) {
  const maxRetries = 3;
  let retries = 0;

  while (retries < maxRetries) {
    try {
      const token = await getToken();

      // Add debug logging
      console.log('Fetching telemetry with:', {
        entityType,
        entityId,
        startTs,
        endTs
      });

      // Modified URL structure to match CoreIoT API format
      const baseUrl = `https://app.coreiot.io/api/plugins/telemetry/${entityType}/${entityId}/values/timeseries`;
      
      // Update keys to match what's shown in CoreIOT
      const params = new URLSearchParams({
        keys: 'temperature,humidity,light,temperature_predict,humidity_predict,light_predict',  // Added prediction keys
        startTs: String(startTs),
        endTs: String(endTs),
        interval: '100000',
        limit: '200',
        agg: 'AVG'
      }).toString();

      // Log the full URL for debugging
      console.log('Fetching from:', `${baseUrl}?${params}`);

      const response = await fetch(`${baseUrl}?${params}`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'X-Authorization': `Bearer ${token}`
        },
      });

      if (response.status === 401) {
        console.log('Token expired, refreshing...');
        await getToken(true);
        retries++;
        continue;
      }

      if (!response.ok) {
        console.error('Response status:', response.status);
        const responseText = await response.text();
        console.error('Response text:', responseText);
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('Telemetry data received:', result);
      return result;
    } catch (error) {
      console.error(`Attempt ${retries + 1}/${maxRetries} failed:`, error);
      retries++;
      if (retries === maxRetries) {
        throw error;
      }
      await new Promise(resolve => setTimeout(resolve, Math.min(1000 * Math.pow(2, retries), 10000)));
    }
  }
}

// Device configuration
const DEVICE_INFO = {
  '1': {
    name: 'IOT-FARMING',
    desc: 'IOT Farming Device',
    // Update with the device's UUID from the IOT-FARMING device
    // entityId: '2c3e3830-3c55-11ee-aae0-0f85903b3644',  
    entityId: '524e3830-3c55-11f0-aae0-0f85903b3644' // This is an example, replace with actual UUID
  },
  // Add more devices as needed with valid entityIds
};

// Utility functions
function formatTime(ts) {
  const date = new Date(ts);
  return `${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`;
}

function getMinMax(arr) {
  if (!arr || arr.length === 0) return [0, 1];
  const min = Math.min(...arr);
  const max = Math.max(...arr);
  return [min, max === min ? min + 1 : max];
}

/**
 * Custom hook for fetching telemetry data
 */
function useTelemetryData(entityType, entityId, interval = 10000) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    
    // Validate inputs
    if (!entityType || !entityId) {
      setError('Missing required parameters: entityType and entityId must be provided');
      setLoading(false);
      return;
    }

    async function fetchData() {
      try {
        // Get current time in milliseconds and ensure we're using UTC
        const endTs = Date.now(); // Current time in milliseconds
        const startTs = endTs - (15 * 60 * 1000); // 30 minutes ago
        
        console.log('Fetching telemetry data with:', {
          entityType,
          entityId,
          startTs,
          endTs
        });
        
        const result = await fetchTelemetryData(entityType, entityId, startTs, endTs);
        
        if (mounted) {
          setData(result);
          setError(null);
        }
      } catch (err) {
        if (mounted) {
          setError(err.message);
          console.error('Error fetching telemetry data:', err);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    fetchData();
    const intervalId = setInterval(fetchData, interval);

    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, [entityType, entityId, interval]);

  return { data, loading, error };
}

/**
 * Send attributes to CoreIoT device
 * @param {string} entityType - Type of entity (e.g., 'DEVICE')
 * @param {string} entityId - ID of the entity
 * @param {Object} attributes - Key-value pairs of attributes to send
 */
async function sendAttributes(entityType, entityId, attributes) {
  const maxRetries = 2;
  let retries = 0;

  while (retries < maxRetries) {
    try {
      const token = await getToken();
      
      // Log the request details
      const url = `https://app.coreiot.io/api/plugins/telemetry/${entityType}/${entityId}/SERVER_SCOPE`;
      console.log('Sending attributes to CoreIoT:', {
        entityType,
        entityId,
        attributes,
        url
      });
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(attributes)
      });

      if (response.status === 401) {
        console.log('Token expired, refreshing...');
        await getToken(true);
        retries++;
        continue;
      }

      if (!response.ok) {
        // Try to get more details about the error
        const errorText = await response.text();
        console.error('Server response:', {
          status: response.status,
          statusText: response.statusText,
          body: errorText
        });
        throw new Error(`HTTP error! status: ${response.status}, details: ${errorText}`);
      }

      // Check if there's actually content in the response
      const contentLength = response.headers.get('Content-Length');
      const contentType = response.headers.get('Content-Type');
      
      if (contentLength === '0' || !contentType?.includes('application/json')) {
        // If there's no content or it's not JSON, just return success
        console.log('Attributes sent successfully (no response body)');
        return { success: true };
      }

      // Only try to parse JSON if we expect JSON content
      const text = await response.text();
      const result = text ? JSON.parse(text) : { success: true };
      console.log('Attributes sent successfully:', result);
      return result;
    } catch (error) {
      console.error(`Attempt ${retries + 1}/${maxRetries} failed:`, error);
      retries++;
      if (retries === maxRetries) {
        throw error;
      }
      // Wait before retrying
      await new Promise(resolve => setTimeout(resolve, Math.min(1000 * Math.pow(2, retries), 10000)));
    }
  }
}

/**
 * DeviceDetail component
 */
function DeviceDetail() {
  const { id } = useParams();

  if (!id) {
    return (
      <div className="error-container">
        <h1>Error</h1>
        <p>No device ID provided</p>
      </div>
    );
  }

  const device = DEVICE_INFO[id];
  if (!device) {
    return (
      <div className="error-container">
        <h1>Error</h1>
        <p>Device not found: {id}</p>
        <p>Available devices: {Object.keys(DEVICE_INFO).join(', ')}</p>
      </div>
    );
  }

  if (!device.entityId) {
    return (
      <div className="error-container">
        <h1>Error</h1>
        <p>No entity ID configured for device: {id}</p>
      </div>
    );
  }

  const { data, loading, error } = useTelemetryData('DEVICE', device.entityId);

  // Prepare chart data
  const chartData = React.useMemo(() => {
    if (!data?.temperature) return [];
    return data.temperature.map((point, idx) => ({
      time: formatTime(point.ts),
      temperature: parseFloat(point.value),
      humidity: data.humidity?.[idx] ? parseFloat(data.humidity[idx].value) : undefined,
      light: data.light?.[idx] ? parseFloat(data.light[idx].value) : undefined,

      temperature_predict: data.temperature_predict?.[idx] ? parseFloat(data.temperature_predict[idx].value) : undefined,
      humidity_predict: data.humidity_predict?.[idx] ? parseFloat(data.humidity_predict[idx].value) : undefined,
      light_predict: data.light_predict?.[idx] ? parseFloat(data.light_predict[idx].value) : undefined,
    }));
  }, [data]);

  // Calculate min/max values for charts
  const [tempMin, tempMax] = getMinMax(chartData.map(d => d.temperature));
  const [humMin, humMax] = getMinMax(chartData.map(d => d.humidity));
  const [lightMin, lightMax] = getMinMax(chartData.map(d => d.light));
  const [temp_preMin, temp_preMax] = getMinMax(chartData.map(d => d.temperature_predict));
  const [hum_preMin, hum_preMax] = getMinMax(chartData.map(d => d.humidity_predict));
  const [light_preMin, light_preMax] = getMinMax(chartData.map(d => d.light_predict));


  if (error) {
    return (
      <div className="error-container">
        <h1>Error</h1>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="device-detail">
      {/* Your existing JSX for charts */}
    </div>
  );
}

export {
  getToken,
  fetchTelemetryData,
  sendAttributes,  // Add this to exports
  DEVICE_INFO,
  useTelemetryData,
  DeviceDetail as default,
};