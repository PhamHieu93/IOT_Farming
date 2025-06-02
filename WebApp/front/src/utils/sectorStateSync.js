/**
 * Utility to synchronize sector states between localStorage and server
 */

export const syncSectorWithServer = async (sector, sendDeviceCommand, changeControlType) => {
    try {
        // Get saved states from localStorage
        const sectorGroups = JSON.parse(localStorage.getItem('sectorGroups')) || {};
        const sectorGroupsThreshold = JSON.parse(localStorage.getItem('sectorGroupsThreshold')) || {};
        const timeSettings = JSON.parse(localStorage.getItem('timeSettings')) || {};
        
        if (!sectorGroups[sector] || !sectorGroupsThreshold[sector]) {
            console.warn(`No saved data found for sector ${sector}`);
            return false;
        }
        
        // Sync regular device states first
        for (let i = 0; i < sectorGroups[sector].length; i++) {
            const device = sectorGroups[sector][i];
            
            // Sync control type first
            if (device.type) {
                await changeControlType(
                    sector,
                    device.id,
                    device.type,
                    device.status,
                    device.type === "Schedule" ? timeSettings[sector][i] : undefined
                );
            }
            
            // Then sync on/off status if the device is on
            if (device.status) {
                const payload = device.type === "Schedule" 
                    ? { ...timeSettings[sector][i], command: "start" } 
                    : { command: "start" };
                
                await sendDeviceCommand(
                    sector,
                    device.id,
                    true,
                    device.type,
                    payload
                );
            }
        }
        
        // Sync threshold devices
        for (let i = 0; i < sectorGroupsThreshold[sector].length; i++) {
            const device = sectorGroupsThreshold[sector][i];
            
            if (device.status) {
                const errorPercentage = device.errorPercentage || 10;
                const thresholdValue = device.thresholdValue;
                const minThreshold = thresholdValue * (1 - errorPercentage / 100);
                const maxThreshold = thresholdValue * (1 + errorPercentage / 100);
                
                await sendDeviceCommand(
                    sector,
                    device.id,
                    true,
                    "Threshold",
                    {
                        command: "start",
                        thresholdValue: thresholdValue,
                        minThreshold: minThreshold,
                        maxThreshold: maxThreshold,
                        errorPercentage: errorPercentage,
                        unit: device.thresholdUnit
                    }
                );
            }
        }
        
        return true;
    } catch (error) {
        console.error("Error syncing sector state with server:", error);
        return false;
    }
};

// Function to load state from server if available, or use localStorage
export const loadSectorStateFromServer = (fetchDeviceStates) => {
    // This would be implemented if your backend has an API to get all device states
    // For now, we'll just use localStorage data
};
