import React, { useState, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import { FiAlertTriangle, FiAlertCircle, FiTrash2 } from "react-icons/fi";
import "./Alarm.scss";

const Alert = () => {
    const [alerts, setAlerts] = useState([]);
    const [activeStatus, setActiveStatus] = useState("All");
    const [selectedAlertId, setSelectedAlertId] = useState(null);
    const statuses = ["All", "Warning", "Critical"];

    useEffect(() => {
        // Initial fetch
        fetchAlerts();

        // Set up interval for periodic updates
        const interval = setInterval(fetchAlerts, 5000); // Update every 5 seconds

        // Cleanup interval on component unmount
        return () => clearInterval(interval);
    }, []); 

    const fetchAlerts = async () => {
        try {
            const response = await fetch('http://localhost:3000/api/alerts');
            if (!response.ok) {
                throw new Error('Failed to fetch alerts');
            }
            const data = await response.json();
            setAlerts(data);
        } catch (error) {
            console.error('Error fetching alerts:', error);
        }
    };

    // Function to filter alerts based on active status
    const filteredAlerts = activeStatus === "All" 
        ? alerts 
        : alerts.filter(alert => alert.status.toLowerCase() === activeStatus.toLowerCase());

    const handleAlertSelect = (datetime) => {
        setSelectedAlertId(datetime === selectedAlertId ? null : datetime);
    };

    const getStatusIcon = (status) => {
        switch (status.toLowerCase()) {
            case "critical":
                return <FiAlertCircle className="status-icon critical" />;
            case "warning":
                return <FiAlertTriangle className="status-icon warning" />;
            default:
                return <FiAlertTriangle className="status-icon warning" />;
        }
    };

    // Function to delete an alert
    const handleDeleteSelected = async () => {
        if (selectedAlertId === null) return;

        try {
            const response = await fetch(`http://localhost:3000/api/alerts/${selectedAlertId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error('Failed to delete alert');
            }

            setAlerts(alerts.filter(alert => alert.datetime !== selectedAlertId));
            setSelectedAlertId(null);
            await fetchAlerts();
        } catch (error) {
            console.error('Error deleting alert:', error);
            alert('Failed to delete alert. Please try again.');
        }
    };

    return (
        <div className="history">
            <Sidebar />
            <div className="history-content">
                <div className="history-container">
                    <div className="history-header">
                        <h2>Alerts</h2>
                        <p>Monitor system alerts and thresholds.</p>
                    </div>

                    <div className="status-tabs">
                        <div className="filter-buttons">
                            {statuses.map((status) => (
                                <button
                                    key={status}
                                    className={`status-tab ${activeStatus === status ? "active" : ""}`}
                                    onClick={() => setActiveStatus(status)}
                                >
                                    {status}
                                </button>
                            ))}
                        </div>
                        <div className="action-buttons">
                            <button 
                                className="delete-btn" 
                                onClick={handleDeleteSelected}
                                disabled={selectedAlertId === null}
                            >
                                <FiTrash2 />
                            </button>
                        </div>
                    </div>

                    <div className="requests-list">
                        {filteredAlerts.map((alert) => (
                            <div 
                                key={alert.datetime} 
                                className={`request-card ${selectedAlertId === alert.datetime ? 'selected' : ''} ${alert.status.toLowerCase()}`}
                                onClick={() => handleAlertSelect(alert.datetime)}
                            >
                                <div className="request-content">
                                    <div className="request-status">
                                        {getStatusIcon(alert.status)}
                                        <span className={`status-badge ${alert.status.toLowerCase()}`}>
                                            {alert.status}
                                        </span>
                                    </div>
                                    <div className="request-details">
                                        <h3 className="request-title">{alert.content}</h3>
                                        <div className="request-meta">
                                            <span className="request-date">
                                                {new Date(alert.datetime).toLocaleString()}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                        {filteredAlerts.length === 0 && (
                            <p className="no-alerts">No alerts found</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Alert;