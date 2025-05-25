import React, { useState } from "react";
import Sidebar from "../components/Sidebar";
import Header from "../components/Header";
import "./History.scss";
import { FiCheck, FiX, FiClock, FiList, FiFlag, FiCheckCircle } from "react-icons/fi";

const History = () => {
    const [requests, setRequests] = useState([
        {
            id: 1,
            title: "Allow feedbacks without signing up",
            date: "Nov 21",
            upvotes: 2,
            comments: 7,
            status: "Completed",
        },
        {
            id: 2,
            title: "In-app widgets for collecting feedback",
            date: "Nov 21",
            upvotes: 0,
            comments: 4,
            status: "In Progress",
        },
        {
            id: 3,
            title: "Being able to change status directly from the list",
            date: "Nov 21",
            upvotes: 0,
            comments: 3,
            status: "Planned",
        },
        {
            id: 4,
            title: "Contrast issue when writing changelog in light mode",
            date: "Nov 21",
            upvotes: 1,
            comments: 2,
            status: "Reviewing",
        },
        {
            id: 5,
            title: "Add a custom 404 page",
            date: "Nov 21",
            upvotes: 1,
            comments: 2,
            status: "Pending",
        },
        {
            id: 6,
            title: "Stop suggesting dashes for workspace name",
            date: "Nov 22",
            upvotes: 0,
            comments: 1,
            status: "Closed",
        },
        {
            id: 7,
            title: "Changable usernames",
            date: "Nov 21",
            upvotes: 0,
            comments: 1,
            status: "Pending",
        },
    ]);

    const [activeStatus, setActiveStatus] = useState("All");

    const statuses = ["All", "Pending", "Reviewing", "Planned", "In Progress", "Completed", "Closed"];

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
                        <h2>Requests</h2>
                        <p>View, create, and manage your requests.</p>
                    </div>

                    <div className="boards">
                        <div className="board-options">
                            <span>Status</span>
                            <span>Tags</span>
                            <span>Order</span>
                        </div>
                    </div>

                    <div className="status-tabs">
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