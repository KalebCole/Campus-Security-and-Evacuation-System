// Base URL for the API, fetched from environment variables
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'; // Fallback if not set

console.log(`API Base URL: ${API_BASE_URL}`); // Log for debugging

// Helper function for making API requests (optional, but good practice)
const makeRequest = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const response = await fetch(url, options);
    if (!response.ok) {
      // Attempt to read error details from response body
      let errorBody = null;
      try {
        errorBody = await response.json();
      } catch (_) { /* Ignore if body isn't JSON */ }
      const errorMessage = errorBody?.error || response.statusText || 'Unknown API error';
      console.error(`API Error ${response.status} at ${url}:`, errorMessage, errorBody);
      throw new Error(`API Error: ${errorMessage}`);
    }
    // Handle cases where response might be empty (e.g., 204 No Content)
    if (response.status === 204) {
        return null; 
    }
    return await response.json(); // Assuming most responses are JSON
  } catch (error) {
    console.error(`Network or fetch error for ${url}:`, error);
    // Re-throw or handle as appropriate for the specific call site
    throw error; 
  }
};

// Example: Fetch pending count (implementation later)
export const fetchPendingReviewCount = async () => {
  // TODO: Replace with actual fetch call to backend
  console.warn("API call 'fetchPendingReviewCount' is not implemented yet.");
  // Use the helper
  // return await makeRequest('/admin/reviews/pending/count'); 
  
  // Simulate fetching count for now (REMOVE THIS MOCK LATER)
  await new Promise(resolve => setTimeout(resolve, 300));
  return Math.floor(Math.random() * 10);
};

// --- MOCKED LOG DATA --- 
let mockLogCounter = 0;
const createMockLog = () => {
  mockLogCounter++;
  const methods = ['RFID_ONLY_PENDING_REVIEW', 'FACE_ONLY_PENDING_REVIEW', 'FACE_VERIFICATION_FAILED'];
  const employees = [null, 'Alice', 'Bob', 'Charlie', null, 'David'];
  const now = new Date();
  const pastTimestamp = new Date(now.getTime() - mockLogCounter * 60000 * Math.random() * 5);

  return {
    log_id: crypto.randomUUID(), // Use built-in crypto for UUIDs
    session_id: crypto.randomUUID(),
    timestamp: pastTimestamp.toISOString(),
    verification_method: methods[mockLogCounter % methods.length],
    employee_name: employees[mockLogCounter % employees.length],
    status: 'pending' // Assuming these are pending
    // Add other fields if needed by LogCard
  };
};

// Example: Fetch pending logs (implementation later)
export const fetchPendingLogs = async (page = 1, limit = 6) => {
  // TODO: Replace with actual fetch call to backend with pagination
  console.warn(`API call 'fetchPendingLogs' (page: ${page}) is not implemented yet.`);
  // Use the helper 
  // return await makeRequest(`/admin/reviews?status=pending&page=${page}&limit=${limit}`);
  
  // Simulate fetching paginated data (REMOVE THIS MOCK LATER)
  await new Promise(resolve => setTimeout(resolve, 500));
  const logs = Array.from({ length: limit }, createMockLog);
  const hasMore = page < 3;
  return { logs, hasMore };
};

// Add other API functions here as needed... 