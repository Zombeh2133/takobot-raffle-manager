/**
 * Dark Mode Toggle System
 * Handles theme switching between light and dark modes
 * Persists user preference in localStorage
 */

(function() {
  'use strict';

  const THEME_KEY = 'takobot-theme';
  const THEME_LIGHT = 'light';
  const THEME_DARK = 'dark';

  /**
   * Get current theme from localStorage or default to light
   */
  function getCurrentTheme() {
    return localStorage.getItem(THEME_KEY) || THEME_LIGHT;
  }

  /**
   * Apply theme to document
   */
  function applyTheme(theme) {
    if (theme === THEME_DARK) {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    
    // Update toggle icon
    updateToggleIcon(theme);
    
    // Save to localStorage
    localStorage.setItem(THEME_KEY, theme);
    
    console.log('🎨 Theme applied:', theme);
  }

  /**
   * Update the toggle button icon
   */
  function updateToggleIcon(theme) {
    const toggleBtn = document.getElementById('themeToggle');
    if (!toggleBtn) return;

    const img = toggleBtn.querySelector('img');
    if (!img) return;

    if (theme === THEME_DARK) {
      img.src = '/static/assets/Icons/ON.png';
      img.alt = 'Dark mode enabled';
      toggleBtn.title = 'Switch to Light Mode';
    } else {
      img.src = '/static/assets/Icons/OFF.png';
      img.alt = 'Light mode enabled';
      toggleBtn.title = 'Switch to Dark Mode';
    }
    
    console.log('🔄 Toggle icon updated to:', theme, '| Icon:', img.src);
  }

  /**
   * Toggle between light and dark themes
   */
  function toggleTheme() {
    const currentTheme = getCurrentTheme();
    const newTheme = currentTheme === THEME_DARK ? THEME_LIGHT : THEME_DARK;
    applyTheme(newTheme);
    
    // Dispatch custom event for other scripts to react if needed
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: newTheme } }));
  }

  /**
   * Initialize dark mode on page load
   */
  function initDarkMode() {
    // Apply saved theme immediately to HTML element (before page renders)
    const savedTheme = getCurrentTheme();
    if (savedTheme === THEME_DARK) {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    
    console.log('🎨 Theme applied early:', savedTheme);

    // Wait for DOM to be ready before updating icon
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function() {
        updateToggleIcon(savedTheme);
        attachToggleListener();
      });
    } else {
      updateToggleIcon(savedTheme);
      attachToggleListener();
    }
  }

  /**
   * Attach click listener to toggle button
   */
  function attachToggleListener() {
    const toggleBtn = document.getElementById('themeToggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', toggleTheme);
      console.log('✅ Dark mode toggle initialized');
    }
    // Silently skip if no toggle button (e.g., on pages without dark mode toggle)
  }

  // Initialize immediately
  initDarkMode();

  // Expose global functions for debugging
  window.TakoBotTheme = {
    toggle: toggleTheme,
    getCurrent: getCurrentTheme,
    setTheme: applyTheme,
    setLight: () => applyTheme(THEME_LIGHT),
    setDark: () => applyTheme(THEME_DARK)
  };

})();
