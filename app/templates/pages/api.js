// API Helper for Raffle Manager
const API_BASE = window.location.origin + '/api';

const API = {
  // ============ ACTIVE RAFFLE ============
  
  async saveRaffle(data) {
    try {
      const res = await fetch(`${API_BASE}/raffle/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      return await res.json();
    } catch (error) {
      console.error('API Error - saveRaffle:', error);
      return { ok: false, error: error.message };
    }
  },

  async loadRaffle() {
    try {
      const res = await fetch(`${API_BASE}/raffle/load`);
      return await res.json();
    } catch (error) {
      console.error('API Error - loadRaffle:', error);
      return { ok: false, error: error.message };
    }
  },

  async clearRaffle() {
    try {
      const res = await fetch(`${API_BASE}/raffle/clear`, { method: 'DELETE' });
      return await res.json();
    } catch (error) {
      console.error('API Error - clearRaffle:', error);
      return { ok: false, error: error.message };
    }
  },

  // ============ RAFFLE HISTORY ============

  async saveToHistory(data) {
    try {
      const res = await fetch(`${API_BASE}/raffle/history`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      return await res.json();
    } catch (error) {
      console.error('API Error - saveToHistory:', error);
      return { ok: false, error: error.message };
    }
  },

  async getHistory() {
    try {
      const res = await fetch(`${API_BASE}/raffle/history`);
      return await res.json();
    } catch (error) {
      console.error('API Error - getHistory:', error);
      return { ok: false, error: error.message };
    }
  },

  async clearHistory() {
    try {
      const res = await fetch(`${API_BASE}/raffle/history`, { method: 'DELETE' });
      return await res.json();
    } catch (error) {
      console.error('API Error - clearHistory:', error);
      return { ok: false, error: error.message };
    }
  },

  // ============ ACTIVITY LOG ============

  async logActivity(data) {
    try {
      const res = await fetch(`${API_BASE}/activity/log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      return await res.json();
    } catch (error) {
      console.error('API Error - logActivity:', error);
      return { ok: false, error: error.message };
    }
  },

  async getActivities() {
    try {
      const res = await fetch(`${API_BASE}/activity/list`);
      return await res.json();
    } catch (error) {
      console.error('API Error - getActivities:', error);
      return { ok: false, error: error.message };
    }
  },

  async clearActivities() {
    try {
      const res = await fetch(`${API_BASE}/activity/clear`, { method: 'DELETE' });
      return await res.json();
    } catch (error) {
      console.error('API Error - clearActivities:', error);
      return { ok: false, error: error.message };
    }
  },

  // ============ SETTINGS ============

  async saveSetting(key, value) {
    try {
      const res = await fetch(`${API_BASE}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value })
      });
      return await res.json();
    } catch (error) {
      console.error('API Error - saveSetting:', error);
      return { ok: false, error: error.message };
    }
  },

  async getSetting(key) {
    try {
      const res = await fetch(`${API_BASE}/settings/${key}`);
      return await res.json();
    } catch (error) {
      console.error('API Error - getSetting:', error);
      return { ok: false, error: error.message };
    }
  }
};

// Make it available globally
window.API = API;
