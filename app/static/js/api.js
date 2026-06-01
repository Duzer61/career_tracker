// API layer

// Helper function to make authenticated requests with auto-refresh via cookies
async function authenticatedFetch(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        credentials: 'include'
    });

    // If token expired, try to refresh
    if (response.status === 401) {
        console.log('Token expired, attempting refresh...');
        
        // If refresh already in progress, wait for it
        if (refreshInProgress) {
            console.log('Waiting for refresh to complete...');
            await new Promise(resolve => {
                const checkInterval = setInterval(() => {
                    if (!refreshInProgress) {
                        clearInterval(checkInterval);
                        resolve();
                    }
                }, 100);
            });
            // Retry the original request with new token
            return fetch(url, {
                ...options,
                credentials: 'include'
            });
        }

        // Try to refresh token
        refreshInProgress = true;
        try {
            const refreshResponse = await fetch(`${API_BASE}/auth/refresh`, {
                method: 'POST',
                credentials: 'include'
            });

            if (refreshResponse.ok) {
                console.log('Token refreshed successfully');
                // Retry the original request
                return fetch(url, {
                    ...options,
                    credentials: 'include'
                });
            } else {
                console.log('Refresh failed, logging out');
                // Refresh failed - logout
                refreshInProgress = false;
                currentUser = null;
                showAuth();
                throw new Error('Session expired. Please login again.');
            }
        } catch (error) {
            refreshInProgress = false;
            currentUser = null;
            showAuth();
            throw error;
        } finally {
            refreshInProgress = false;
        }
    }

    return response;
}
