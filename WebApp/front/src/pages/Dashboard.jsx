import React, { useState, memo, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";
import { getToken, fetchTelemetryData, useTelemetryData, DEVICE_INFO, publishSensorData } from '../services/coreIOT';
import "./Dashboard.scss";

import {
    BarChart, Bar, LineChart, Line, AreaChart, Area,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";
import { FiArrowUp, FiArrowDown } from "react-icons/fi";
import { FaWater } from "react-icons/fa";

const SensorCard = memo(({ sensor }) => {
    const { data, loading, error } = useTelemetryData('DEVICE', sensor.deviceId, 10000);
    const [trend, setTrend] = useState({ value: 0, isPositive: true });

    // Monitor data changes and check thresholds
    useEffect(() => {
        if (!data || !data[sensor.dataKey]) return;

        const latestData = data[sensor.dataKey][data[sensor.dataKey].length - 1];
        if (!latestData) return;

        const value = parseFloat(latestData.value);
        if (isNaN(value)) return;

        // Get the sensor name based on data key
        const sensorNameMap = {
            'temperature': 'Temperature',
            'humidity': 'Humidity',
            'light': 'Light'
        };

        const sensorName = sensorNameMap[sensor.dataKey];
        if (!sensorName) return;

        console.log(`Checking sensor ${sensorName} with value:`, value);

        // Fetch current thresholds
        fetch('http://localhost:3000/api/threshold')
            .then(response => response.json())
            .then(thresholdData => {
                const thresholds = thresholdData.find(t => t.attribute === sensorName);
                if (!thresholds) {
                    console.log(`No thresholds found for ${sensorName}`);
                    return;
                }

                const thresholdValue = parseFloat(thresholds.value);
                const minValue = parseFloat(thresholds.minValue);

                console.log(`Threshold values for ${sensorName}:`, {
                    current: value,
                    min: minValue,
                    threshold: thresholdValue
                });

                // Check if we need to create an alert
                if (value >= thresholdValue || value <= minValue) {
                    // Create alert in the server
                    fetch('http://localhost:3000/api/alerts', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            sensor: sensorName,
                            value,
                            threshold: thresholdValue
                        })
                    })
                    .then(response => response.json())
                    .then(result => {
                        if (result.success) {
                            // Notify alarm component to refresh its data
                            publishSensorData({
                                sensor: sensorName,
                                value,
                                minValue,
                                thresholdValue,
                                timestamp: new Date().toLocaleString()
                            });
                        }
                    })
                    .catch(error => console.error('Error saving alert:', error));
                }
            })
            .catch(error => console.error('Error fetching thresholds:', error));
    }, [data, sensor.dataKey]);

    // Add debug logging
    useEffect(() => {
        console.log(`SensorCard ${sensor.id} data:`, { data, loading, error });
    }, [data, loading, error, sensor.id]);

    const formattedData = React.useMemo(() => {
        if (!data || !data[sensor.dataKey]) {
            console.log(`No data for sensor ${sensor.id}`, { data });
            return [];
        }
        
        const formattedData = data[sensor.dataKey].map(point => ({
            name: formatTime(point.ts),
            value: parseFloat(point.value)
        })).filter(point => !isNaN(point.value));

        console.log(`Formatted data for ${sensor.id}:`, formattedData);

        // Calculate trend
        if (formattedData.length >= 2) {
            const latest = formattedData[formattedData.length - 1].value;
            const first = formattedData[0].value;
            const change = ((latest - first) / first) * 100;
            setTrend({
                value: Math.abs(change),
                isPositive: change >= 0
            });
        }

        return formattedData;
    }, [data, sensor.dataKey, sensor.id]);

    // Get current value
    const currentValue = React.useMemo(() => {
        if (loading) return "...";
        if (error) return "Error";
        if (formattedData.length === 0) return "N/A";
        
        const value = formattedData[formattedData.length - 1].value;
        return typeof value === 'number' ? value.toFixed(1) : value;
    }, [loading, error, formattedData]);

    return (
        <div className={`sensor-card ${sensor.id}`}>
            <div className="sensor-info">
                <span className="sensor-name">{sensor.name}</span>
                <h4 className="sensor-value">
                    {currentValue}{sensor.unit}
                </h4>
                {!loading && formattedData.length >= 2 && (
                    <div className={`sensor-change ${trend.isPositive ? 'positive' : 'negative'}`}>
                        {trend.isPositive ? <FiArrowUp /> : <FiArrowDown />}
                        {trend.value.toFixed(1)}%
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
                        <AreaChart data={formattedData}>
                            <Area
                                type="monotone"
                                dataKey="value"
                                stroke={
                                    sensor.id === 'temp' ? '#8884d8' :
                                    sensor.id === 'humidity' ? '#82ca9d' :
                                    sensor.id === 'lux' ? '#ffc658' :
                                    sensor.id === 'temp_predict' ? '#ff7300' :
                                    sensor.id === 'humidity_predict' ? '#ff69b4' :
                                    sensor.id === 'light_predict' ? '#00c6ff' :
                                    '#82ca9d'
                                }
                            fill={
                                sensor.id === 'temp' ? 'rgba(136, 132, 216, 0.2)' :
                                sensor.id === 'humidity' ? 'rgba(130, 202, 157, 0.2)' :
                                sensor.id === 'lux' ? 'rgba(255, 198, 88, 0.2)' :
                                sensor.id === 'temp_predict' ? 'rgba(255, 115, 0, 0.2)' :
                                sensor.id === 'humidity_predict' ? 'rgba(255, 105, 180, 0.2)' :
                                sensor.id === 'light_predict' ? 'rgba(0, 198, 255, 0.2)' :
                                'rgba(130, 202, 157, 0.2)'
                            }
                                strokeWidth={2}
                            />
                        </AreaChart>
                    )}
                </ResponsiveContainer>
            </div>
            {error && <div className="error-message">{error}</div>}
        </div>
    );
});

// Helper function for formatting timestamps
function formatTime(ts) {
    const date = new Date(ts);
    return `${date.getHours()}:${date.getMinutes().toString().padStart(2, '0')}`;
}

const Dashboard = () => {
    const [activeTab, setActiveTab] = useState("Month");
    const [activeLineTab, setActiveLineTab] = useState("Day");

    const { data, loading } = useTelemetryData('DEVICE', DEVICE_INFO['1'].entityId, 10000);

    // Process the data for main chart
    const chartData = React.useMemo(() => {
        if (!data?.temperature) return [];
        return data.temperature.map((temp, idx) => ({
            name: formatTime(temp.ts),
            temp: parseFloat(temp.value),
            humidity: data.humidity?.[idx] ? parseFloat(data.humidity[idx].value) : undefined,
            light: data.light?.[idx] ? parseFloat(data.light[idx].value) : undefined,
            temp_predict: data.temperature_predict?.[idx] ? parseFloat(data.temperature_predict[idx].value) : undefined,
            humidity_predict: data.humidity_predict?.[idx] ? parseFloat(data.humidity_predict[idx].value) : undefined,
            light_predict: data.light_predict?.[idx] ? parseFloat(data.light_predict[idx].value) : undefined,
        })) || [];
    }, [data]);

    // Process humidity data for the humidity chart
    const humidityChartData = React.useMemo(() => {
        if (!data?.humidity) return [];
        return data.humidity.map(point => ({
            name: formatTime(point.ts),
            value: parseFloat(point.value)
        })) || [];
    }, [data]);

    const sensors = [
        {
            id: 'temp',
            name: 'Temperature',
            deviceId: DEVICE_INFO['1'].entityId,
            dataKey: 'temperature',
            unit: '°C'
        },
        {
            id: 'humidity',
            name: 'Humidity',
            deviceId: DEVICE_INFO['1'].entityId,
            dataKey: 'humidity',
            unit: '%'
        },
        {
            id: 'lux',
            name: 'Light',
            deviceId: DEVICE_INFO['1'].entityId,
            dataKey: 'light',
            unit: ' lux'
        },
        {
            id: 'temp_predict',
            name: 'Temperature Predict',
            deviceId: DEVICE_INFO['1'].entityId,
            dataKey: 'temperature_predict',
            unit: '°C'
        },
        {
            id: 'humidity_predict',
            name: 'Humidity Predict',
            deviceId: DEVICE_INFO['1'].entityId,
            dataKey: 'humidity_predict',
            unit: '%'
        },
        {
            id: 'light_predict',
            name: 'Light Predict',
            deviceId: DEVICE_INFO['1'].entityId,
            dataKey: 'light_predict',
            unit: ' lux'
        },
    ];

    return (
        <div className="dashboard">
            <Sidebar />
            <div className="dashboard-content">
                <Header />
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
                        <BarChart data={loading ? [] : chartData}>
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
                            <Bar dataKey="light" fill="#ffc658" name="Light" barSize={20}/>
                            <Bar dataKey="temp_predict" fill="#ff7300" name="Temperature Predict" barSize={20}/>
                            <Bar dataKey="humidity_predict" fill="#ff69b4" name="Humidity Predict" barSize={20}/>
                            <Bar dataKey="light_predict" fill="#00c6ff" name="Light Predict" barSize={20}/>
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
                            {!loading && humidityChartData.length >= 2 && (
                                <div className={`change ${humidityChartData[humidityChartData.length - 1].value > humidityChartData[0].value ? 'positive' : 'negative'}`}>
                                    <FiArrowUp/>
                                    {Math.abs(((humidityChartData[humidityChartData.length - 1].value - humidityChartData[0].value) / humidityChartData[0].value) * 100).toFixed(1)}%
                                </div>
                            )}
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
                                <LineChart data={loading ? [] : humidityChartData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a"/>
                                    <XAxis dataKey="name" stroke="#a1a1b5"/>
                                    <YAxis stroke="#a1a1b5" domain={[0, 100]}/>
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
                    {sensors.map((sensor) => (
                        <SensorCard key={sensor.id} sensor={sensor}/>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default Dashboard;