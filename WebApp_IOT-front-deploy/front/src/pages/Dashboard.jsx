import React, { useState, memo, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";
import "./Dashboard.scss";
import {
    BarChart, Bar, LineChart, Line, AreaChart, Area,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";
import { FiArrowUp, FiArrowDown } from "react-icons/fi";
import { FaWater } from "react-icons/fa";
import { useWebSocket } from '../contexts/WebSocket';

const SensorCard = memo(({ sensor }) => {
    const getSensorData = (id) => {
        const now = new Date();
        return Array.from({ length: 6 }, (_, i) => {
            const d = new Date(now);
            d.setHours(d.getHours() - (5 - i));
            return {
                name: d.getHours() + ':00',
                value: Math.floor(Math.random() * 20) +
                    (id === 'temp' ? 20 :
                        id === 'humidity' ? 50 :
                            id === 'co2' ? 400 :
                                id === 'lux' ? 1000 :
                                    id === 'vpd' ? 1 : 0)
            };
        });
    };

    return (
        <div className={`sensor-card ${sensor.id}`}>
            <div className="sensor-info">
                <span className="sensor-name">{sensor.name}</span>
                <h4 className="sensor-value">{sensor.value}{sensor.unit}</h4>
                {sensor.change !== null && (
                    <div className={`sensor-change ${sensor.positive ? 'positive' : 'negative'}`}>
                        {sensor.positive ? <FiArrowUp /> : <FiArrowDown />}
                        {sensor.change}%
                    </div>
                )}
            </div>
            <div className="sensor-graph">
                <ResponsiveContainer width="100%" height={60}>
                    {sensor.id === 'wifi' ? (
                        <div className="wifi-status">
                            <div className="wifi-bars">
                                {[1, 2, 3].map((bar) => (
                                    <div
                                        key={bar}
                                        className={`wifi-bar ${bar <= 2 ? 'active' : ''}`}
                                        style={{ height: `${bar * 12 + 8}px` }}
                                    />
                                ))}
                            </div>
                        </div>
                    ) : (
                        <AreaChart data={getSensorData(sensor.id)}>
                            <Area
                                type="monotone"
                                dataKey="value"
                                stroke={sensor.id === 'temp' ? '#8884d8' :
                                    sensor.id === 'humidity' ? '#82ca9d' :
                                        sensor.id === 'co2' ? '#ff7300' :
                                            sensor.id === 'lux' ? '#ffc658' :
                                                '#00c6ff'}
                                fill={sensor.id === 'temp' ? 'rgba(136, 132, 216, 0.2)' :
                                    sensor.id === 'humidity' ? 'rgba(130, 202, 157, 0.2)' :
                                        sensor.id === 'co2' ? 'rgba(255, 115, 0, 0.2)' :
                                            sensor.id === 'lux' ? 'rgba(255, 198, 88, 0.2)' :
                                                'rgba(0, 198, 255, 0.2)'}
                                strokeWidth={2}
                            />
                        </AreaChart>
                    )}
                </ResponsiveContainer>
            </div>
        </div>
    );
});

const data = [
    { name: "Jan", temp: 22, humidity: 65, lux: 1200, co2: 420, vpd: 1.2 },
    { name: "Feb", temp: 23, humidity: 63, lux: 1350, co2: 440, vpd: 1.3 },
    { name: "Mar", temp: 24, humidity: 60, lux: 1500, co2: 460, vpd: 1.4 },
    { name: "Apr", temp: 25, humidity: 58, lux: 1650, co2: 480, vpd: 1.5 },
    { name: "May", temp: 26, humidity: 55, lux: 1800, co2: 500, vpd: 1.6 },
    { name: "Jun", temp: 27, humidity: 53, lux: 1950, co2: 520, vpd: 1.7 },
    { name: "Jul", temp: 26, humidity: 56, lux: 1850, co2: 510, vpd: 1.6 },
    { name: "Aug", temp: 25, humidity: 58, lux: 1700, co2: 490, vpd: 1.5 },
    { name: "Sep", temp: 24, humidity: 60, lux: 1550, co2: 470, vpd: 1.4 },
    { name: "Oct", temp: 23, humidity: 62, lux: 1400, co2: 450, vpd: 1.3 },
    { name: "Nov", temp: 22, humidity: 64, lux: 1250, co2: 430, vpd: 1.2 },
    { name: "Dec", temp: 21, humidity: 66, lux: 1100, co2: 410, vpd: 1.1 },
];

const humidityData = [
    { name: "03:00", value: 32 },
    { name: "09:00", value: 34 },
    { name: "15:00", value: 30 },
    { name: "21:00", value: 32 },
];

const Dashboard = () => {
    const [activeTab, setActiveTab] = useState("Month");
    const [activeLineTab, setActiveLineTab] = useState("Day");
 // Add these lines to use WebSocket
    const { isConnected, addMessageListener, lastMessage, sendMessage } = useWebSocket();
    const [temperatureData, setTemperatureData] = useState(null);
    const [humidityData, setHumidityData] = useState(null);
    const [lightData, setLightData] = useState(null);

        // Listen for temperature data updates
    useEffect(() => {
        const unsubscribe = addMessageListener('temperature_data', (data) => {
            if (data && data.success) {
                console.log("Received temperature data:", data);
                setTemperatureData(data.data);
            }
        });        
        // Clean up listener when component unmounts
        return unsubscribe;
    }, [addMessageListener]);
    
    // Listen for humidity data updates
    useEffect(() => {
        const unsubscribe = addMessageListener('humidity_data', (data) => {
            if (data && data.success) {
                console.log("Received humidity data:", data);
                setHumidityData(data.data);
            }
        });
        
        return unsubscribe;
    }, [addMessageListener]);
    
    // Listen for light data updates
    useEffect(() => {
        const unsubscribe = addMessageListener('light_data', (data) => {
            if (data && data.success) {
                console.log("Received light data:", data);
                setLightData(data.data);
            }
        });
        
        return unsubscribe;
    }, [addMessageListener]);

    // Request sensor data when connected
    useEffect(() => {
        if (isConnected) {
            console.log("Requesting sensor data from server");
            try {
                sendMessage('get_temperature', {});
                sendMessage('get_humidity', {});
                sendMessage('get_light', {});
                console.log("Requests sent successfully");
            } catch (error) {
                console.error("Error sending data requests:", error);
            }
        }
    }, [isConnected, sendMessage]);
    
    useEffect(() => {
        console.log("Current WebSocket state:", { isConnected });
        console.log("Current sensor data:", { temperatureData, humidityData, lightData });
    }, [isConnected, temperatureData, humidityData, lightData]);

    // Handle all incoming messages
    useEffect(() => {
        if (lastMessage) {
            console.log("New WebSocket message:", lastMessage.event);
            
            switch(lastMessage.event) {
                case 'temperature_data':
                    if (lastMessage.data && lastMessage.data.success) {
                        setTemperatureData(lastMessage.data.data);
                    }
                    break;
                case 'humidity_data':
                    if (lastMessage.data && lastMessage.data.success) {
                        setHumidityData(lastMessage.data.data);
                    }
                    break;
                case 'light_data':
                    if (lastMessage.data && lastMessage.data.success) {
                        setLightData(lastMessage.data.data);
                    }
                    break;
                default:
                    break;
            }
        }
    }, [lastMessage]);

    // Format temperature for display (convert if needed)
    const getFormattedTemperature = () => {
        console.log("Formatting temperature data:", temperatureData);
        
        if (!temperatureData) return { value: '--', unit: '°C' };
        
        // Make sure value exists and is a number before using toFixed
        const value = temperatureData.value;
        if (value === undefined || value === null) return { value: '--', unit: '°C' };
        
        return { 
            value: typeof value === 'number' ? value.toFixed(1) : value.toString(), 
            unit: temperatureData.unit || '°C'
        };
    };

    // Format humidity for display
    const getFormattedHumidity = () => {
        if (!humidityData) return { value: '--', unit: '%' };
        
        const value = humidityData.value;
        if (value === undefined || value === null) return { value: '--', unit: '%' };
        
        return { 
            value: typeof value === 'number' ? value.toFixed(1) : value.toString(), 
            unit: humidityData.unit || '%'
        };
    };
    
    // Format light for display
    const getFormattedLight = () => {
        if (!lightData) return { value: '--', unit: 'lx' };
        
        const value = lightData.value;
        if (value === undefined || value === null) return { value: '--', unit: 'lx' };
        
        return { 
            value: typeof value === 'number' ? value.toFixed(0) : value.toString(), 
            unit: lightData.unit || 'lx'
        };
    };

    // Get the formatted temperature
    const tempDisplay = getFormattedTemperature();
    const humidityDisplay = getFormattedHumidity();
    const lightDisplay = getFormattedLight();

    return (
        <div className="dashboard">
            <Sidebar />
            <div className="dashboard-content">
                <Header />
                {!isConnected && (
                    <div className="connection-warning">
                        Attempting to connect to server...
                    </div>
                )}

                <div className="charts-container">
                    <div className="chart-card main-chart">
                        <div className="chart-header">
                            <h3>Graphical Synopsis</h3>
                            <div className="chart-tabs">
                                {["Hour", "Day", "Week", "Month", "Year", "Custom"].map((tab) => (
                                    <button
                                        key={tab}
                                        className={`tab-btn ${activeTab === tab ? "active" : ""}`}
                                        onClick={() => setActiveTab(tab)}
                                    >
                                        {tab}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={data}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a"/>
                                <XAxis dataKey="name" stroke="#a1a1b5"/>
                                <YAxis stroke="#a1a1b5"/>
                                <Tooltip
                                    contentStyle={{
                                        background: '#2a2a3a',
                                        border: 'none',
                                        borderRadius: '8px',
                                        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)'
                                    }}
                                />
                                <Legend/>
                                <Bar dataKey="temp" fill="#8884d8" name="Temperature" barSize={20}/>
                                <Bar dataKey="humidity" fill="#82ca9d" name="Humidity" barSize={20}/>
                                <Bar dataKey="lux" fill="#ffc658" name="Lux" barSize={20}/>
                                <Bar dataKey="co2" fill="#ff7300" name="CO2" barSize={20}/>
                                <Bar dataKey="vpd" fill="#ff69b4" name="VPD" barSize={20}/>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="chart-card humidity-chart">
                        <div className="chart-header">
                            <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                                <FaWater style={{color: '#a1a1b5', fontSize: '20px'}}/>
                                <h3>Humidity</h3>
                            </div>
                        </div>
                        <div className="chart-value">
                            <div className="change positive">
                                <FiArrowUp/> 4%
                            </div>
                        </div>
                        <div className="chart-tabs">
                            {["Hour", "Day", "Week", "Month", "Year", "Custom"].map((tab) => (
                                <button
                                    key={tab}
                                    className={`tab-btn ${activeLineTab === tab ? "active" : ""}`}
                                    onClick={() => setActiveLineTab(tab)}
                                >
                                    {tab}
                                </button>
                            ))}
                        </div>
                        <div className="chart-content">
                            <ResponsiveContainer width="100%" height={180}>
                                <LineChart data={humidityData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a"/>
                                    <XAxis dataKey="name" stroke="#a1a1b5"/>
                                    <YAxis stroke="#a1a1b5" domain={[0, 60]}/>
                                    <Tooltip
                                        contentStyle={{
                                            background: '#2a2a3a',
                                            border: 'none',
                                            borderRadius: '8px'
                                        }}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="value"
                                        stroke="#00c6ff"
                                        strokeWidth={2}
                                        dot={false}
                                        activeDot={{r: 6, stroke: '#00c6ff', strokeWidth: 2, fill: '#1e1e2f'}}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </div>

                <div className="sensor-cards">
                    {[
                        {
                            id: 'temp', 
                            name: 'Temperature', 
                            value: temperatureData ? tempDisplay.value : '--', 
                            change: temperatureData ? 2.5 : null, 
                            positive: true, 
                            unit: temperatureData ? tempDisplay.unit : '°C'
                        },                        
                        {
                            id: 'humidity', 
                            name: 'Humidity', 
                            value: humidityDisplay.value, 
                            change: humidityData ? 1.2 : null, 
                            positive: false, 
                            unit: humidityDisplay.unit
                        },                        
                        {id: 'co2', name: 'CO2', value: '420', change: 0.8, positive: true, unit: 'ppm'},
                        {
                            id: 'lux', 
                            name: 'Lux', 
                            value: lightDisplay.value, 
                            change: lightData ? 3.1 : null, 
                            positive: true, 
                            unit: lightDisplay.unit
                        },                        
                        {id: 'vpd', name: 'VPD', value: '1.2', change: 0.3, positive: false, unit: 'kPa'},
                        {
                            id: 'wifi', 
                            name: 'WiFi', 
                            value: isConnected ? 'Good' : 'Bad', 
                            change: null, 
                            positive: null, 
                            unit: ''
                        },
                        ].map((sensor) => (
                        <SensorCard key={sensor.id} sensor={sensor}/>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default Dashboard;