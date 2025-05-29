import React, { useState, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import { FiCheck, FiX, FiClock, FiList, FiFlag, FiCheckCircle, FiPlus, FiTrash2, FiCalendar } from "react-icons/fi";
import { useWebSocket } from "../contexts/WebSocket";
import "./Reminder.scss";

const Reminder = () => {
    // Get WebSocket context - add lastMessage to the destructuring
    const { sendMessage, isConnected, lastMessage } = useWebSocket();
    
    // Initialize with empty array instead of hardcoded data
    const [requests, setRequests] = useState([]);
    const [hasLoadedData, setHasLoadedData] = useState(false);
    // Fetch notes when component mounts
    useEffect(() => {
        if (isConnected && !hasLoadedData) {
            console.log("Requesting notes from server");
            sendMessage('get_csv_note', {});
            setHasLoadedData(true);
        }
    }, [isConnected, hasLoadedData]);
    
    // Handle incoming WebSocket messages
    useEffect(() => {
        if (lastMessage) {
            console.log("Received message:", lastMessage);
            
            if (lastMessage.type === 'csv_note_response') {
                console.log("Received notes from server:", lastMessage.data);
                
                // Check if data is an array before mapping
                if (Array.isArray(lastMessage.data)) {
                    setRequests(lastMessage.data.map(note => ({
                        id: note.id,
                        title: note.title,
                        date: note.date,
                        timeToDo: note.timeToDo,
                        status: note.status
                    })));
                } else {
                    console.error("Server did not return an array of notes:", lastMessage.data);
                }
            }
        }
    }, [lastMessage]);
        
    const [activeStatus, setActiveStatus] = useState("All");
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [selectedNoteId, setSelectedNoteId] = useState(null);
    const statuses = ["All", "Planned", "Completed"];
    
    const [newNote, setNewNote] = useState({
        title: "",
        date: new Date().toISOString().split("T")[0], // YYYY-MM-DD format
        time: new Date().toTimeString().slice(0, 5),  // HH:MM format
        status: "Planned"
    });

    // Function to filter requests based on active status
    const filteredRequests = activeStatus === "All" 
        ? requests 
        : requests.filter(request => request.status === activeStatus);

    const handleNoteSelect = (id) => {
        setSelectedNoteId(id === selectedNoteId ? null : id);
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case "Completed":
                return <FiCheckCircle className="status-icon completed" />;
            case "Planned":
                return <FiClock className="status-icon planned" />;
            default:
                return <FiList className="status-icon pending" />;
        }
    };

    // Function to add a new note
    const handleAddNote = () => {
        if (newNote.title.trim() === "") return;
        
        // Generate new ID (replace with proper UUID in production)
        const newId = requests.length > 0 
            ? Math.max(...requests.map(req => req.id)) + 1 
            : 1;
        
        // Format the selected date
        const formattedDate = new Date(newNote.date).toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric' 
        });
        
        // Combine date and time for the WebSocket
        const timeToDoFormatted = `${newNote.date} ${newNote.time}`;
        
        const noteToAdd = {
            id: newId,
            title: newNote.title.trim(),
            date: formattedDate,
            timeToDo: timeToDoFormatted,
            status: newNote.status
        };
        
        // Update local state
        setRequests(prevRequests => [...prevRequests, noteToAdd]);
        
        // Send to WebSocket
        if (isConnected) {
            console.log("Sending new note to server:", noteToAdd);
            sendMessage('add_note', {
                id: newId,
                title: noteToAdd.title,
                status: noteToAdd.status,
                // Send structured date and time information
                date: newNote.date,       // YYYY-MM-DD format
                time: newNote.time,       // HH:MM format
                timeToDo: timeToDoFormatted  // Combined format
            });
        }
        
        // Reset form and close modal
        setNewNote({
            title: "",
            date: new Date().toISOString().split("T")[0],
            time: new Date().toTimeString().slice(0, 5),
            status: "Planned"
        });
        setIsModalOpen(false);
    };
    
    // Function to delete a note
    const handleDeleteSelected = () => {
        if (selectedNoteId !== null) {
            // Find the note to get its content for deletion matching on server
            const noteToDelete = requests.find(req => req.id === selectedNoteId);
            
            if (noteToDelete) {
                // Update local state
                setRequests(requests.filter(req => req.id !== selectedNoteId));
                
                // Send to WebSocket - the server expects the content
                if (isConnected) {
                    console.log("Sending delete note to server:", selectedNoteId);
                    sendMessage('delete_note', {
                        noteId: selectedNoteId
                    });
                }
                
                setSelectedNoteId(null);
            }
        }
    };

    return (
        <div className="history">
            <Sidebar />
            <div className="history-content">
                <div className="history-container">
                    <div className="history-header">
                        <h2>Notes</h2>
                        <p>View, create, and manage your notes.</p>
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
                        <div className="action-buttons">
                            <button className="add-note-btn" onClick={() => setIsModalOpen(true)}>
                                <FiPlus />
                            </button>
                            <button 
                                className="delete-all-btn" 
                                onClick={handleDeleteSelected}
                                disabled={selectedNoteId === null}
                            >
                                <FiTrash2 />
                            </button>
                        </div>
                    </div>

                    <div className="requests-list">
                        {filteredRequests.map((request) => (
                            <div 
                                key={request.id} 
                                className={`request-card ${selectedNoteId === request.id ? 'selected' : ''}`}
                                onClick={() => handleNoteSelect(request.id)}
                            >
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
                                                <span className="note-time">
                                                    <FiClock className="time-icon" />
                                                    {request.timeToDo ? request.timeToDo.split(' ')[1] || '00:00' : '00:00'}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

            {isModalOpen && (
                <div className="modal-overlay">
                    <div className="add-note-modal">
                        <h3>Add New Note</h3>
                        
                        <div className="form-group">
                            <label htmlFor="note-title"></label>
                            <input
                                id="note-title"
                                type="text"
                                placeholder="Note title"
                                value={newNote.title}
                                onChange={(e) => setNewNote({...newNote, title: e.target.value})}
                            />
                        </div>
                        
                        <div className="form-group">
                            <label htmlFor="note-date">Date</label>
                            <div className="date-input-wrapper">
                                <FiCalendar className="input-icon" />
                                <input
                                    id="note-date"
                                    type="date"
                                    value={newNote.date}
                                    onChange={(e) => setNewNote({...newNote, date: e.target.value})}
                                />
                            </div>
                        </div>
                        
                        <div className="form-group">
                            <label htmlFor="note-time">Time</label>
                            <div className="time-input-wrapper">
                                <FiClock className="input-icon" />
                                <input
                                    id="note-time"
                                    type="time"
                                    value={newNote.time}
                                    onChange={(e) => setNewNote({...newNote, time: e.target.value})}
                                />
                            </div>
                        </div>
                        
                        <div className="form-group">
                            <label htmlFor="note-status">Status</label>
                            <select 
                                id="note-status"
                                value={newNote.status}
                                onChange={(e) => setNewNote({...newNote, status: e.target.value})}
                            >
                                <option value="Planned">Planned</option>
                                <option value="Completed">Completed</option>
                            </select>
                        </div>
                        
                        <div className="modal-buttons">
                            <button className="cancel-button" onClick={() => setIsModalOpen(false)}>Cancel</button>
                            <button className="add-button" onClick={handleAddNote}>Add Note</button>
                        </div>
                    </div>
                </div>
            )}
            </div>
        </div>
    );
};

export default Reminder;