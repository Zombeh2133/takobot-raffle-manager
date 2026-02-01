/* =========================================
   VIEW TRANSITIONS API - NAVIGATION HANDLER
   ========================================= */

/**
 * Intercepts all internal link clicks and applies smooth cross-fade transitions
 * Works in Chrome 111+, Edge 111+, Safari 18+
 * Gracefully falls back to normal navigation in unsupported browsers
 */

(function() {
  'use strict';

  // Check if View Transitions API is supported
  const supportsViewTransitions = 'startViewTransition' in document;

  if (supportsViewTransitions) {
    console.log('✅ View Transitions API supported - smooth page transitions enabled');
  } else {
    console.log('ℹ️ View Transitions API not supported - using standard navigation');
    return; // Exit early if not supported
  }

  /**
   * Handle click events on links
   */
  function handleLinkClick(event) {
    const link = event.target.closest('a');
    
    // Ignore if not a link
    if (!link) return;
    
    // Ignore if link has target="_blank" or similar
    if (link.target && link.target !== '_self') return;
    
    // Ignore external links
    if (link.hostname && link.hostname !== window.location.hostname) return;
    
    // Ignore if link has download attribute
    if (link.hasAttribute('download')) return;
    
    // Ignore if Ctrl/Cmd/Shift key is pressed (user wants new tab)
    if (event.ctrlKey || event.metaKey || event.shiftKey) return;
    
    // Ignore if right-click
    if (event.button !== 0) return;
    
    // Get the URL
    const url = link.href;
    
    // Ignore if no URL
    if (!url) return;
    
    // Ignore if same page (hash links)
    if (url.split('#')[0] === window.location.href.split('#')[0]) return;
    
    // Prevent default navigation
    event.preventDefault();
    
    // Apply View Transition
    document.startViewTransition(() => {
      window.location.href = url;
    });
  }

  /**
   * Handle browser back/forward buttons
   */
  function handlePopState(event) {
    if (document.startViewTransition) {
      document.startViewTransition(() => {
        // Browser will handle the navigation
      });
    }
  }

  // Attach event listeners
  document.addEventListener('click', handleLinkClick);
  window.addEventListener('popstate', handlePopState);

  // Log initialization
  console.log('🎬 View Transitions initialized - cross-fade on navigation');

})();
