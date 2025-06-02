import React, { useState, useEffect } from "react";
import Sidebar from "../components/Sidebar";
import { FiCheck, FiX, FiClock, FiList, FiFlag, FiCheckCircle, FiPlus, FiTrash2, FiCalendar } from "react-icons/fi";
import "./Reminder.scss";

const Reminder = () => {
    const [requests, setRequests] = useState([]);
    const [activeStatus, setActiveStatus] = useState("All");
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [selectedNoteId, setSelectedNoteId] = useState(null);
    const statuses = ["All", "Planned", "Completed"];
    
    const [newNote, setNewNote] = useState({
        title: "",
        date: new Date().toISOString().split("T")[0],
        time: new Date().toTimeString().slice(0, 5),
        status: "Planned"
    });

    useEffect(() => {
        // Initial fetch
        fetchNotes();

        // Set up interval for periodic updates
        const interval = setInterval(fetchNotes, 5000); // Update every 5 seconds

        // Cleanup interval on component unmount
        return () => clearInterval(interval);
    }, []); // Empty dependency array means this runs once when component mounts

    const fetchNotes = async () => {
        try {
            console.log('Fetching notes...');
            const response = await fetch('http://localhost:3000/api/notes');
            if (!response.ok) {
                throw new Error(`Failed to fetch notes: ${response.status} ${response.statusText}`);
            }
            const data = await response.json();
            console.log('Raw data from server:', data);
            
            if (!Array.isArray(data)) {
                console.error('Received data is not an array:', data);
                return;
            }

            // Transform the data to match your component's structure
            const formattedNotes = data.map(note => {
                console.log('Processing note:', note);
                // Parse the datetime string
                let noteDate;
                try {
                    noteDate = new Date(note.datetime);
                    if (isNaN(noteDate.getTime())) {
                        console.warn('Invalid date for note:', note);
                        noteDate = new Date();
                    }
                } catch (e) {
                    console.error('Error parsing date:', e);
                    noteDate = new Date();
                }

                return {
                    id: parseInt(note.id), // Ensure ID is a number
                    title: note.content,
                    date: noteDate.toISOString().split('T')[0],
                    time: noteDate.toLocaleTimeString('en-US', { 
                        hour: '2-digit', 
                        minute: '2-digit',
                        hour12: false 
                    }),
                    status: note.status || 'Planned' // Default to Planned if status is missing
                };
            });
            
            // Sort notes by date and time, most recent first
            formattedNotes.sort((a, b) => {
                const dateA = new Date(a.date + 'T' + a.time);
                const dateB = new Date(b.date + 'T' + b.time);
                return dateB - dateA;
            });
            
            console.log('Formatted notes:', formattedNotes);
            setRequests(formattedNotes);
        } catch (error) {
            console.error('Error fetching notes:', error);
        }
    };

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

    // Modified handleAddNote to properly format data for CSV
    const handleAddNote = async () => {
        if (newNote.title.trim() === "") return;
        
        const newId = requests.length > 0 
            ? Math.max(...requests.map(req => req.id)) + 1 
            : 1;
        
        try {
            // Create datetime string with both date and time
            const datetime = `${newNote.date}T${newNote.time}:00.000Z`;
            
            // Make API call to save to CSV
            const response = await fetch('http://localhost:3000/api/notes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content: newNote.title.trim(),
                    status: newNote.status,
                    datetime: datetime
                })
            });

            if (!response.ok) {
                throw new Error('Failed to save note');
            }

            const noteToAdd = {
                id: newId,
                title: newNote.title.trim(),
                date: newNote.date,
                time: newNote.time,
                status: newNote.status
            };
            
            setRequests(prevRequests => [...prevRequests, noteToAdd]);
            setNewNote({
                title: "",
                date: new Date().toISOString().split("T")[0],
                time: new Date().toTimeString().slice(0, 5),
                status: "Planned"
            });
            setIsModalOpen(false);
        } catch (error) {
            console.error('Error saving note:', error);
            alert('Failed to save note. Please try again.');
        }
    };
    
    // Function to change note status
    const handleStatusChange = async (id) => {
        if (!selectedNoteId) return;
        
        const noteToUpdate = requests.find(req => req.id === id);
        if (!noteToUpdate) return;

        try {
            const response = await fetch(`http://localhost:3000/api/notes/${noteToUpdate.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    status: 'Completed'
                })
            });

            if (!response.ok) {
                throw new Error('Failed to update note status');
            }

            // Update local state
            setRequests(prevRequests => 
                prevRequests.map(req => 
                    req.id === id 
                        ? { ...req, status: 'Completed' }
                        : req
                )
            );
            setSelectedNoteId(null);

            // Refresh the notes list
            await fetchNotes();
        } catch (error) {
            console.error('Error updating note:', error);
            alert('Failed to update note status. Please try again.');
        }
    };

    // Function to delete a note
    const handleDeleteSelected = async () => {
        if (selectedNoteId === null) return;

        const noteToDelete = requests.find(req => req.id === selectedNoteId);
        if (!noteToDelete) return;

        try {
            const response = await fetch(`http://localhost:3000/api/notes/${noteToDelete.id}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error('Failed to delete note');
            }

            // Update local state
            setRequests(requests.filter(req => req.id !== selectedNoteId));
            setSelectedNoteId(null);

            // Refresh the notes list
            await fetchNotes();
        } catch (error) {
            console.error('Error deleting note:', error);
            alert('Failed to delete note. Please try again.');
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
                                className="complete-btn" 
                                onClick={() => handleStatusChange(selectedNoteId)}
                                disabled={!selectedNoteId || requests.find(req => req.id === selectedNoteId)?.status === 'Completed'}
                            >
                                <FiCheckCircle />
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
                                                    {request.time || '00:00'}
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