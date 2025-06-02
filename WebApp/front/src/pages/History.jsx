import React, { useState, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";
import "./History.scss";
import { FiCheck, FiX, FiClock, FiList, FiFlag, FiCheckCircle } from "react-icons/fi";

const History = () => {
    const [requests, setRequests] = useState([]);
    const [activeStatus, setActiveStatus] = useState("All");

    const statuses = ["All", "Pending", "Reviewing", "Planned", "In Progress", "Completed", "Closed"];

    useEffect(() => {
        // Function to fetch notifications from the server
        const fetchNotifications = async () => {
            try {
                const response = await fetch('http://localhost:3000/api/notifications');
                if (!response.ok) {
                    throw new Error('Failed to fetch notifications');
                }
                const data = await response.json();
                
                // Transform the data to match our component's structure
                const transformedData = data.map(note => ({
                    id: note.id,
                    title: note.content,
                    date: note.datetime,
                    status: note.status,
                    upvotes: 0,
                    comments: 0
                }));
                
                setRequests(transformedData);
            } catch (error) {
                console.error('Error fetching notifications:', error);
            }
        };

        // Fetch notifications immediately and then every 5 seconds
        fetchNotifications();
        const interval = setInterval(fetchNotifications, 5000);

        // Cleanup interval on component unmount
        return () => clearInterval(interval);
    }, []);

    const getStatusIcon = (status) => {
        switch (status) {
            case "Completed":
                return <FiCheckCircle className="status-icon completed" />;
            case "In Progress":
                return <FiCheck className="status-icon in-progress" />;
            case "Planned":
                return <FiList className="status-icon planned" />;
            case "Reviewing":
                return <FiFlag className="status-icon reviewing" />;
            case "Pending":
                return <FiClock className="status-icon pending" />;
            case "Closed":
                return <FiX className="status-icon closed" />;
            default:
                return <FiClock className="status-icon" />;
        }
    };

    const filteredRequests = activeStatus === "All"
        ? requests
        : requests.filter(request => request.status === activeStatus);

    return (
        <div className="history">
            <Sidebar />
            <div className="history-content">
                <div className="history-container">
                    <div className="history-header">
                        <h2>Notification</h2>
                        <p>View all your notifications.</p>
                    </div>

                    <div className="boards">
                        <div className="board-options">
                            <span>Status</span>
                            <span>Tags</span>
                            <span>Order</span>
                        </div>
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
                    </div>

                    <div className="requests-list">
                        {filteredRequests.map((request) => (
                            <div key={request.id} className="request-card">
                                <div className="request-content">
                                    <div className="request-status">
                                        {getStatusIcon(request.status)}
                                        <span className={`status-badge ${request.status.toLowerCase().replace(" ", "-")}`}>
                                            {request.status}
                                        </span>
                                    </div>
                                    <div className="request-details">
                                        <h3 className="request-title">{request.title}</h3>
                                        <div className="request-meta">
                                            <span className="request-date">{request.date}</span>
                                            <div className="request-stats">
                                                <span className="upvotes">{request.upvotes} upvotes</span>
                                                <span className="comments">{request.comments} comments</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default History;