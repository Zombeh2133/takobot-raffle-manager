/**
 * Background Polling Script
 * Runs on all pages and performs auto-scanning even when user is away from Active Raffle page
 */

(function() {
  let pollingInterval = null;
  const POLLING_INTERVAL_MS = 60000; // 1 minute

  // Check if polling should be active
  function shouldPoll() {
    const isActive = localStorage.getItem('autoPollingActive') === 'true';
    const raffleId = localStorage.getItem('autoPollingRaffleId');
    return isActive && raffleId;
  }

  // Perform the auto-scan
  async function performBackgroundScan() {
    const raffleId = localStorage.getItem('autoPollingRaffleId');
    
    if (!raffleId) {
      console.log('⏸️ Background polling: No raffle ID found');
      stopBackgroundPolling();
      return;
    }

    console.log('🔄 Background polling: Scanning Reddit for new participants...');

    try {
      // Call the scan Reddit endpoint
      const response = await fetch('/api/scan-reddit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raffle_id: raffleId })
      });

      if (!response.ok) {
        console.error('❌ Background scan failed:', response.status);
        return;
      }

      const data = await response.json();
      
      if (data.new_participants && data.new_participants.length > 0) {
        console.log(`✅ Background scan: ${data.new_participants.length} new participants found`);
        
        // Store last scan result in localStorage so Active Raffle page can pick it up
        localStorage.setItem('lastBackgroundScan', JSON.stringify({
          timestamp: new Date().toISOString(),
          newCount: data.new_participants.length,
          totalEntries: data.new_participants.reduce((sum, p) => sum + p.spots.length, 0)
        }));

        // Trigger a custom event that the Active Raffle page can listen for
        if (window.location.pathname.includes('active-raffle') || window.location.pathname === '/') {
          window.dispatchEvent(new CustomEvent('backgroundScanComplete', { 
            detail: { newCount: data.new_participants.length } 
          }));
        }
      } else {
        console.log('✓ Background scan: No new participants');
      }

      // Check if raffle is full (spots remaining = 0)
      if (data.spots_remaining === 0) {
        console.log('🎉 Background scan: Raffle is full! Stopping auto-scan.');
        stopBackgroundPolling();
      }

    } catch (error) {
      console.error('❌ Background scan error:', error);
    }
  }

  // Start background polling
  function startBackgroundPolling() {
    // Clear any existing interval
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }

    // Only start if polling should be active
    if (!shouldPoll()) {
      return;
    }

    console.log('🚀 Background polling started (runs on all pages)');
    
    // Start polling every minute
    pollingInterval = setInterval(performBackgroundScan, POLLING_INTERVAL_MS);
    
    // Perform initial scan
    performBackgroundScan();
  }

  // Stop background polling
  function stopBackgroundPolling() {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
      console.log('⏹️ Background polling stopped');
    }
  }

  // Initialize on page load
  window.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
      // Check if we're on the Active Raffle page
      const isActiveRafflePage = window.location.pathname.includes('active-raffle') || 
                                  window.location.pathname === '/active_raffle' ||
                                  document.getElementById('autoScanIndicator'); // Presence of this element indicates Active Raffle page
      
      // Only start background polling if NOT on Active Raffle page
      // (Active Raffle page has its own polling mechanism)
      if (!isActiveRafflePage && shouldPoll()) {
        console.log('📍 Background polling: Starting on non-Active-Raffle page');
        startBackgroundPolling();
      } else if (isActiveRafflePage) {
        console.log('📍 Background polling: Disabled (Active Raffle page handles its own polling)');
      }
    }, 2000); // Wait 2 seconds to ensure page is fully loaded
  });

  // Listen for localStorage changes (when polling is started/stopped from another page)
  window.addEventListener('storage', (e) => {
    if (e.key === 'autoPollingActive') {
      if (e.newValue === 'true') {
        startBackgroundPolling();
      } else {
        stopBackgroundPolling();
      }
    }
  });

  // Clean up on page unload
  window.addEventListener('beforeunload', () => {
    // Don't stop polling - it should continue even when navigating
    // Just clean up this page's interval (other pages will pick it up)
  });

  // Expose control functions globally (for debugging)
  window.backgroundPolling = {
    start: startBackgroundPolling,
    stop: stopBackgroundPolling,
    isActive: () => pollingInterval !== null
  };

})();
