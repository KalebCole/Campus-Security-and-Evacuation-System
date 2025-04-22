import React, { createContext, useState, useEffect, useContext } from 'react';
import { fetchPendingReviewCount } from '@/services/api'; // Use alias

const AppContext = createContext();

export function AppProvider({ children }) {
  const [pendingCount, setPendingCount] = useState(0);

  useEffect(() => {
    // Initial fetch
    fetchPendingReviewCount().then(setPendingCount);

    // Set up polling (e.g., every 30 seconds)
    const intervalId = setInterval(async () => {
      try {
        const count = await fetchPendingReviewCount();
        setPendingCount(count);
      } catch (error) {
        console.error("Failed to fetch pending review count:", error);
        // Optionally handle error in UI (e.g., set count to null or show error state)
      }
    }, 30000); // 30 seconds interval

    // Cleanup function to clear interval on unmount
    return () => clearInterval(intervalId);
  }, []); // Empty dependency array ensures this runs only once on mount

  return (
    <AppContext.Provider value={{ pendingCount }}>
      {children}
    </AppContext.Provider>
  );
}

// Custom hook to use the AppContext
export function useAppContext() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
} 