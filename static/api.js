// Use global API_BASE_URL from config.js
const API_BASE_URL = window.API_BASE_URL || 'http://107.22.96.217';

// Cache user info in memory to avoid multiple API calls
let cachedUser = null;

// Fetch user from API and cache it
async function fetchAndCacheUser() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/current-user`, {
      credentials: 'include'
    });

    if (response.ok) {
      const result = await response.json();
      if (result.ok && result.data) {
        cachedUser = result.data;
        console.log('✅ User fetched and cached:', cachedUser.username, 'ID:', cachedUser.id);
        return cachedUser;
      }
    }
  } catch (e) {
    console.error('Failed to fetch user:', e);
  }
  return null;
}

// Get user headers for API calls (synchronous, uses cached user)
function getUserHeaders() {
  const headers = { 'Content-Type': 'application/json' };

  if (cachedUser && cachedUser.id && cachedUser.username) {
    headers['X-User-Id'] = String(cachedUser.id);
    headers['X-User-Name'] = cachedUser.username;
    console.log('🔐 Adding user headers - ID:', cachedUser.id, 'Username:', cachedUser.username);
  } else {
    console.warn('⚠️ No cached user for API headers - call fetchAndCacheUser() first!');
  }

  return headers;
}

// Get user headers async (fetches if not cached)
async function getUserHeadersAsync() {
  if (!cachedUser) {
    await fetchAndCacheUser();
  }
  return getUserHeaders();
}

const API = {
  // Version check
  version: '3.1-api-fetch-user',

  // Initialize user cache (call this on page load)
  initUser: fetchAndCacheUser,

  saveRaffle: async (data) => {
    await getUserHeadersAsync(); // Ensure user is cached
    const response = await fetch(`${API_BASE_URL}/api/raffle/save`, {
      method: 'POST',
      headers: getUserHeaders(),
      credentials: 'include',
      body: JSON.stringify(data)
    });
    return response.json();
  },

  loadRaffle: async () => {
    await getUserHeadersAsync(); // Ensure user is cached
    const headers = getUserHeaders();
    const response = await fetch(`${API_BASE_URL}/api/raffle/load`, {
      credentials: 'include',
      headers: headers
    });
    return response.json();
  },

  clearRaffle: async () => {
    await getUserHeadersAsync(); // Ensure user is cached
    const headers = getUserHeaders();
    const response = await fetch(`${API_BASE_URL}/api/raffle/clear`, {
      method: 'DELETE',
      credentials: 'include',
      headers: headers
    });
    return response.json();
  },

  saveToHistory: async (data) => {
    await getUserHeadersAsync(); // Ensure user is cached
    const response = await fetch(`${API_BASE_URL}/api/raffle/history`, {
      method: 'POST',
      headers: getUserHeaders(),
      credentials: 'include',
      body: JSON.stringify(data)
    });
    return response.json();
  },

  getHistory: async () => {
    const response = await fetch(`${API_BASE_URL}/api/raffle/history`, {
      credentials: 'include'
    });
    return response.json();
  },

  clearHistory: async () => {
    const response = await fetch(`${API_BASE_URL}/api/raffle/history`, {
      method: 'DELETE',
      credentials: 'include'
    });
    return response.json();
  },

  deleteRaffle: async (id) => {
    const response = await fetch(`${API_BASE_URL}/api/raffle/history/${id}`, {
      method: 'DELETE',
      credentials: 'include'
    });
    return response.json();
  },

  logActivity: async (data) => {
    // Get current user info
    let username = null;
    let raffle_id = null;

    try {
      const userResponse = await fetch(`${API_BASE_URL}/api/auth/current-user`, {
        credentials: 'include'
      });
      if (userResponse.ok) {
        const userResult = await userResponse.json();
        if (userResult.ok && userResult.data) {
          username = userResult.data.username;
          console.log('✅ logActivity: Got username =', username);
        }
      }
    } catch (e) {
      console.error('Failed to get username for activity log:', e);
    }

    // Get current raffle ID if available
    try {
      const raffleResponse = await fetch(`${API_BASE_URL}/api/raffle/load`, {
        credentials: 'include'
      });
      if (raffleResponse.ok) {
        const raffleResult = await raffleResponse.json();
        if (raffleResult.ok && raffleResult.data && raffleResult.data.id) {
          raffle_id = raffleResult.data.id;
          console.log('✅ logActivity: Got raffle_id =', raffle_id);
        }
      }
    } catch (e) {
      // Raffle might not exist, that's ok
    }

    const payload = {
      ...data,
      username,
      raffle_id
    };

    console.log('📤 logActivity: Sending payload:', payload);

    const response = await fetch(`${API_BASE_URL}/api/activity/log`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload)
    });

    const result = await response.json();
    console.log('📥 logActivity: Response:', result);

    return result;
  },

  getActivities: async () => {
    const response = await fetch(`${API_BASE_URL}/api/activity/list`, {
      credentials: 'include'
    });
    return response.json();
  },

  clearActivities: async () => {
    const response = await fetch(`${API_BASE_URL}/api/activity/clear`, {
      method: 'DELETE',
      credentials: 'include'
    });
    return response.json();
  },

  scanReddit: async (redditLink, costPerSpot, totalSpots = null, existingCommentIds = null, currentAssignedSpots = 0, participantStatuses = null) => {
    // Send as POST with JSON body (matching server.js expectations)
    const response = await fetch(`${API_BASE_URL}/api/reddit/scan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      credentials: 'include',
      body: JSON.stringify({
        redditLink,
        costPerSpot,
        totalSpots,
        existingCommentIds,
        currentAssignedSpots,
        participantStatuses
      })
    });
    return response.json();
  },

  // User authentication methods
  login: async (username, password) => {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ username, password })
    });

    const data = await response.json();

    if (!response.ok) {
      return { success: false, error: data.error || 'Login failed' };
    }

    if (data.ok) {
      return { success: true, user: data.data };
    }

    return { success: false, error: 'Invalid response' };
  },

  checkAdminStatus: async (retryCount = 0) => {
    const response = await fetch(`${API_BASE_URL}/api/auth/current-user`, {
      credentials: 'include'
    });
    const result = await response.json();
    
    // If auth fails on first attempt (likely cookie race condition), retry once after a delay
    if (!result.ok && retryCount === 0) {
      console.log('⏳ Auth check failed on first attempt, retrying in 500ms...');
      await new Promise(resolve => setTimeout(resolve, 500));
      return API.checkAdminStatus(1);
    }
    
    return result;
  },

  // Alias for compatibility with raffle history page
  checkAuth: async (retryCount = 0) => {
    const response = await fetch(`${API_BASE_URL}/api/auth/current-user`, {
      credentials: 'include'
    });
    const result = await response.json();
    
    // If auth fails on first attempt (likely cookie race condition), retry once after a delay
    if (!result.ok && retryCount === 0) {
      console.log('⏳ Auth check failed on first attempt, retrying in 500ms...');
      await new Promise(resolve => setTimeout(resolve, 500));
      return API.checkAuth(1);
    }
    
    return result;
  },

  // Admin analytics methods
  getAdminAnalytics: async (year) => {
    const response = await fetch(`${API_BASE_URL}/api/admin/analytics/${year}`, {
      credentials: 'include'
    });
    return response.json();
  },

  getAdminUserBreakdown: async (year, month) => {
    const response = await fetch(`${API_BASE_URL}/api/admin/user-breakdown/${year}/${month}`, {
      credentials: 'include'
    });
    return response.json();
  }
};
