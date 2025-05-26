import React, { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { useWebSocket } from '../contexts/WebSocket';
import { syncSectorWithServer } from '../utils/sectorStateSync';

const Layout = () => {
    const { isConnected, sendDeviceCommand, changeControlType } = useWebSocket();
    const [initialized, setInitialized] = useState(false);
    const location = useLocation();
    
    // When WebSocket is first connected, sync state
    useEffect(() => {
        if (isConnected && !initialized) {
            const syncState = async () => {
                try {
                    const lastActiveSector = localStorage.getItem('lastActiveSector') || 'A';
                    await syncSectorWithServer(lastActiveSector, sendDeviceCommand, changeControlType);
                    setInitialized(true);
                } catch (error) {
                    console.error('Error initializing sector state:', error);
                }
            };
            
            syncState();
        }
    }, [isConnected, initialized, sendDeviceCommand, changeControlType]);
    
    // When navigating between pages, make sure we maintain state
    useEffect(() => {
        // When location changes, we can trigger any necessary refresh or sync
        console.log('Navigation occurred, path:', location.pathname);
        
        // We don't need to sync on every navigation since localStorage persists
        // But we could add specific sync logic here if needed for certain routes
    }, [location.pathname]);
    
    // Track page changes to preserve state
    useEffect(() => {
        // Log for debugging
        console.log("Layout mounted, preserving sector states across navigation");
        
        // You could add any state synchronization here if needed
    }, []);
    
    return <Outlet />;
};

export default Layout;
