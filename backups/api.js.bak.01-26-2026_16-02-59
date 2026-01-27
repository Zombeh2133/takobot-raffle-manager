const API = {
  // Version check
  version: '2.0-with-username-tracking',
  
  saveRaffle: async (data) => {
    const response = await fetch('/api/raffle/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return response.json();
  },

  loadRaffle: async () => {
    const response = await fetch('/api/raffle/load');
    return response.json();
  },

  clearRaffle: async () => {
    const response = await fetch('/api/raffle/clear', { method: 'DELETE' });
    return response.json();
  },

  saveToHistory: async (data) => {
    const response = await fetch('/api/raffle/history', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return response.json();
  },

  getHistory: async () => {
    const response = await fetch('/api/raffle/history');
    return response.json();
  },

  clearHistory: async () => {
    const response = await fetch('/api/raffle/history', { method: 'DELETE' });
    return response.json();
  },

  deleteRaffle: async (id) => {
    const response = await fetch(`/api/raffle/history/${id}`, { method: 'DELETE' });
    return response.json();
  },

  logActivity: async (data) => {
    // Get current user info
    let username = null;
    let raffle_id = null;
    
    try {
      const userResponse = await fetch('/api/auth/current-user');
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
      const raffleResponse = await fetch('/api/raffle/load');
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
    
    const response = await fetch('/api/activity/log', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    
    const result = await response.json();
    console.log('📥 logActivity: Response:', result);
    
    return result;
  },

  getActivities: async () => {
    const response = await fetch('/api/activity/list');
    return response.json();
  },

  clearActivities: async () => {
    const response = await fetch('/api/activity/clear', { method: 'DELETE' });
    return response.json();
  },

  scanReddit: async (redditLink, costPerSpot, totalSpots = null, existingCommentIds = null) => {
    // OPTIMIZED: Pass existing comment IDs to skip AI parsing for already-processed comments
    let url = `/api/reddit/scan?url=${encodeURIComponent(redditLink)}&costPerSpot=${costPerSpot}`;
    if (totalSpots !== null && totalSpots > 0) {
      url += `&totalSpots=${totalSpots}`;
    }
    // Pass existing comment IDs to reduce OpenAI API calls
    if (existingCommentIds && existingCommentIds.length > 0) {
      url += `&existingCommentIds=${encodeURIComponent(JSON.stringify(existingCommentIds))}`;
    }
    const response = await fetch(url);
    return response.json();
  },

  // User authentication methods
  login: async (username) => {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    });
    return response.json();
  },

  checkAdminStatus: async () => {
    const response = await fetch('/api/auth/current-user');
    return response.json();
  },

  // Alias for compatibility with raffle history page
  checkAuth: async () => {
    const response = await fetch('/api/auth/current-user');
    return response.json();
  },

  // Admin analytics methods
  getAdminAnalytics: async (year) => {
    const response = await fetch(`/api/admin/analytics/${year}`);
    return response.json();
  }
};

