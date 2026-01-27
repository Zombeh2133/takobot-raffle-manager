/* ==============================
   LOADING STATES HELPER v1.0.0
   ============================== */

const LoadingStates = {
  // Show full page loader
  showPageLoader(text = 'Loading...') {
    const existingLoader = document.getElementById('pageLoader');
    if (existingLoader) {
      existingLoader.querySelector('.loader-text').textContent = text;
      existingLoader.classList.remove('hidden');
      return;
    }

    const loader = document.createElement('div');
    loader.id = 'pageLoader';
    loader.className = 'page-loader';
    loader.innerHTML = `
      <div class="loader-spinner"></div>
      <div class="loader-text">${text}</div>
    `;
    document.body.appendChild(loader);
  },

  // Hide full page loader
  hidePageLoader() {
    const loader = document.getElementById('pageLoader');
    if (loader) {
      loader.classList.add('hidden');
      setTimeout(() => loader.remove(), 300);
    }
  },

  // Add loading state to a button
  setButtonLoading(button, loading = true) {
    if (loading) {
      button.dataset.originalText = button.textContent;
      button.classList.add('btn-loading');
      button.disabled = true;
      button.textContent = '';
    } else {
      button.classList.remove('btn-loading');
      button.disabled = false;
      button.textContent = button.dataset.originalText || 'Submit';
    }
  },

  // Show section loader overlay
  showSectionLoader(element) {
    if (!element) return;
    
    const existing = element.querySelector('.section-loader-overlay');
    if (existing) {
      existing.classList.remove('hidden');
      return;
    }

    const overlay = document.createElement('div');
    overlay.className = 'section-loader-overlay';
    overlay.innerHTML = '<div class="loader-spinner"></div>';
    element.style.position = 'relative';
    element.appendChild(overlay);
  },

  // Hide section loader overlay
  hideSectionLoader(element) {
    if (!element) return;
    const overlay = element.querySelector('.section-loader-overlay');
    if (overlay) {
      overlay.classList.add('hidden');
      setTimeout(() => overlay.remove(), 300);
    }
  },

  // Create skeleton loader for table
  createTableSkeleton(rowCount = 5, columnCount = 4) {
    const skeleton = document.createElement('div');
    for (let i = 0; i < rowCount; i++) {
      const row = document.createElement('div');
      row.className = 'skeleton-table-row';
      for (let j = 0; j < columnCount; j++) {
        const cell = document.createElement('div');
        cell.className = 'skeleton skeleton-table-cell';
        row.appendChild(cell);
      }
      skeleton.appendChild(row);
    }
    return skeleton;
  },

  // Create skeleton loader for cards
  createCardsSkeleton(count = 3) {
    const skeleton = document.createElement('div');
    for (let i = 0; i < count; i++) {
      const card = document.createElement('div');
      card.className = 'skeleton skeleton-card';
      skeleton.appendChild(card);
    }
    return skeleton;
  },

  // Show loading dots
  createLoadingDots() {
    const dots = document.createElement('div');
    dots.className = 'loading-dots';
    dots.innerHTML = '<span></span><span></span><span></span>';
    return dots;
  },

  // Show empty state
  showEmptyState(container, options = {}) {
    const {
      icon = '📭',
      title = 'No data found',
      description = 'There are no items to display.',
      actionText = null,
      onAction = null
    } = options;

    const emptyState = document.createElement('div');
    emptyState.className = 'empty-state';
    
    let html = `
      <div class="empty-state-icon">${icon}</div>
      <h3 class="empty-state-title">${title}</h3>
      <p class="empty-state-description">${description}</p>
    `;

    if (actionText && onAction) {
      html += `<button class="empty-state-action">${actionText}</button>`;
    }

    emptyState.innerHTML = html;

    if (actionText && onAction) {
      emptyState.querySelector('.empty-state-action').addEventListener('click', onAction);
    }

    container.innerHTML = '';
    container.appendChild(emptyState);
  },

  // Async data fetch with loading state
  async fetchWithLoading(fetchFn, options = {}) {
    const {
      showPageLoader = false,
      loaderText = 'Loading...',
      showSectionLoader = null,
      onSuccess = null,
      onError = null
    } = options;

    try {
      if (showPageLoader) {
        this.showPageLoader(loaderText);
      }
      if (showSectionLoader) {
        this.showSectionLoader(showSectionLoader);
      }

      const result = await fetchFn();

      if (onSuccess) {
        onSuccess(result);
      }

      return result;
    } catch (error) {
      console.error('Fetch error:', error);
      if (onError) {
        onError(error);
      }
      throw error;
    } finally {
      if (showPageLoader) {
        this.hidePageLoader();
      }
      if (showSectionLoader) {
        this.hideSectionLoader(showSectionLoader);
      }
    }
  },

  // Add progress bar
  showProgressBar(container, progress = null) {
    const existing = container.querySelector('.progress-bar-container');
    if (existing) {
      const bar = existing.querySelector('.progress-bar');
      if (progress !== null) {
        bar.classList.remove('indeterminate');
        bar.style.width = `${progress}%`;
      } else {
        bar.classList.add('indeterminate');
      }
      return;
    }

    const progressBarContainer = document.createElement('div');
    progressBarContainer.className = 'progress-bar-container';
    
    const progressBar = document.createElement('div');
    progressBar.className = 'progress-bar';
    
    if (progress !== null) {
      progressBar.style.width = `${progress}%`;
    } else {
      progressBar.classList.add('indeterminate');
    }

    progressBarContainer.appendChild(progressBar);
    container.insertBefore(progressBarContainer, container.firstChild);
  },

  hideProgressBar(container) {
    const progressBar = container.querySelector('.progress-bar-container');
    if (progressBar) {
      progressBar.remove();
    }
  }
};

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = LoadingStates;
}
