document.addEventListener('DOMContentLoaded', function() {
    const emergencyBanner = document.getElementById('emergency-banner');
    // NOTE: The URL is no longer dynamic here. Needs to be hardcoded or passed via data attribute if base.js is generic.
    // For simplicity now, hardcoding the likely path. Adjust if needed.
    const emergencyApiUrl = "/admin/api/status/emergency"; 
    let pollingInterval = null;
    let consecutiveErrors = 0;
    const MAX_ERRORS = 3; // Stop polling after 3 consecutive errors

    async function checkEmergencyStatus() {
        if (!emergencyApiUrl) {
            console.error("Emergency API URL is not defined in base.js.");
            stopPolling();
            return;
        }

        if (!emergencyBanner) {
            // console.log("Emergency banner element not found on this page.");
            // Optionally stop polling if the banner isn't expected on every page
             stopPolling(); 
            return;
        }

        try {
            const response = await fetch(emergencyApiUrl, {
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache' // Ensure fresh data
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // Update banner visibility based on API response
            if (data.emergency_active) {
                emergencyBanner.classList.remove('d-none');
            } else {
                emergencyBanner.classList.add('d-none');
            }
            
            consecutiveErrors = 0; // Reset error count on success

        } catch (error) {
            console.error('Error fetching emergency status:', error);
            consecutiveErrors++;
            if (consecutiveErrors >= MAX_ERRORS) {
                console.warn(`Stopping emergency status polling after ${MAX_ERRORS} consecutive errors.`);
                stopPolling();
                // Optionally display a static error message or hide the banner
                 emergencyBanner.classList.add('d-none'); // Hide banner on error stop
            }
        }
    }

    function startPolling(interval = 5000) { // Poll every 5 seconds
        if (pollingInterval) return; // Already polling
        console.log("Starting emergency status polling...");
        checkEmergencyStatus(); // Check immediately
        pollingInterval = setInterval(checkEmergencyStatus, interval);
    }

    function stopPolling() {
        if (pollingInterval) {
            console.log("Stopping emergency status polling.");
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    }

    // Start polling when the page loads
    startPolling();

    // Optional: Stop polling if the page visibility changes (to save resources)
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            stopPolling();
        } else {
            startPolling();
        }
    });
});
