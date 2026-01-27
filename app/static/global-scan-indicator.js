/**
 * Global Auto-Scan Indicator
 * Shows a small indicator on all pages when auto-scanning is active
 */

(function() {
  let indicatorElement = null;

  function createIndicator() {
    if (indicatorElement) return;

    // Find the white-square container
    const whiteSquare = document.querySelector('.white-square');
    if (!whiteSquare) return;

    // Create indicator element
    indicatorElement = document.createElement('div');
    indicatorElement.id = 'globalAutoScanIndicator';
    indicatorElement.style.cssText = `
      position: absolute;
      bottom: 20px;
      right: 20px;
      background: linear-gradient(135deg, rgba(147, 51, 234, 0.85) 0%, rgba(121, 40, 202, 0.85) 100%);
      color: white;
      padding: 12px 20px;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(147, 51, 234, 0.3);
      display: none;
      align-items: center;
      gap: 10px;
      font-family: 'Inter', sans-serif;
      font-size: 13px;
      font-weight: 500;
      z-index: 9999;
      backdrop-filter: blur(10px);
      animation: fadeIn 0.3s ease;
    `;

    indicatorElement.innerHTML = `
      <span style="font-size: 16px; animation: pulse 2s ease-in-out infinite;">🔄</span>
      <span>Auto-Scan Active</span>
    `;

    // Add CSS animation
    const style = document.createElement('style');
    style.textContent = `
      @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
      }
      @keyframes pulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.2); opacity: 0.8; }
      }
    `;
    document.head.appendChild(style);

    // Append to white-square instead of body
    whiteSquare.appendChild(indicatorElement);
  }

  function showIndicator() {
    if (!indicatorElement) {
      createIndicator();
    }
    indicatorElement.style.display = 'flex';
  }

  function hideIndicator() {
    if (indicatorElement) {
      indicatorElement.style.display = 'none';
    }
  }

  function updateIndicatorVisibility() {
    const isActive = localStorage.getItem('autoPollingActive') === 'true';
    
    // Don't show on Active Raffle page (it has its own indicator)
    const isActiveRafflePage = window.location.pathname.includes('active-raffle') || 
                                window.location.pathname === '/active_raffle';
    
    if (isActive && !isActiveRafflePage) {
      showIndicator();
    } else {
      hideIndicator();
    }
  }

  // Initialize on page load
  window.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
      createIndicator();
      updateIndicatorVisibility();
    }, 1000);
  });

  // Listen for localStorage changes
  window.addEventListener('storage', (e) => {
    if (e.key === 'autoPollingActive') {
      updateIndicatorVisibility();
    }
  });

  // Periodically check status (in case localStorage changes from same window)
  setInterval(updateIndicatorVisibility, 2000);

})();

