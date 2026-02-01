/* ==========================================
   BEAUTIFUL UPDATE NOTIFICATION SYSTEM
   ========================================== */

// Show toast notification
function showUpdateToast(message, duration = 3000) {
  // Remove existing toast
  const existingToast = document.querySelector('.update-toast');
  if (existingToast) {
    existingToast.remove();
  }

  // Create toast
  const toast = document.createElement('div');
  toast.className = 'update-toast';
  toast.innerHTML = `
    <span class="update-toast-icon">🔄</span>
    <span>${message}</span>
  `;
  document.body.appendChild(toast);

  // Animate in
  setTimeout(() => toast.classList.add('show'), 10);

  // Auto-hide
  if (duration > 0) {
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 400);
    }, duration);
  }

  return toast;
}

// Show beautiful update modal
function showUpdateModal(version, onConfirm, onCancel) {
  // Remove existing modal
  const existingModal = document.querySelector('.update-modal-overlay');
  if (existingModal) {
    existingModal.remove();
  }

  // Create modal
  const modal = document.createElement('div');
  modal.className = 'update-modal-overlay';
  modal.innerHTML = `
    <div class="update-modal" onclick="event.stopPropagation()">
      <div class="update-modal-header">
        <div class="update-modal-icon">🚀</div>
        <h2 class="update-modal-title">Update Available!</h2>
        <div class="update-modal-version">Version ${version}</div>
      </div>
      <div class="update-modal-body">
        <p class="update-modal-message">
          A new version of TakoBot is ready to download. <strong>Stay up to date</strong> with the latest features and improvements!
        </p>
        <div class="update-modal-actions">
          <button class="update-modal-btn update-modal-btn-secondary" onclick="updateModalCancel()">
            Later
          </button>
          <button class="update-modal-btn update-modal-btn-primary" onclick="updateModalConfirm()">
            Download Now
          </button>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // Store callbacks
  window.updateModalConfirmCallback = onConfirm;
  window.updateModalCancelCallback = onCancel;

  // Show modal
  setTimeout(() => modal.classList.add('show'), 10);

  // Prevent body scroll
  document.body.style.overflow = 'hidden';
}

// Confirm download
function updateModalConfirm() {
  const modal = document.querySelector('.update-modal-overlay');
  if (!modal) return;

  // Show downloading state
  const modalBody = modal.querySelector('.update-modal-body');
  modalBody.innerHTML = `
    <div class="update-downloading">
      <div class="update-downloading-title">Downloading Update...</div>
      <div class="update-progress-bar">
        <div class="update-progress-fill" id="updateProgressFill"></div>
      </div>
      <div class="update-progress-text" id="updateProgressText">Preparing download...</div>
    </div>
  `;

  // Call confirm callback
  if (window.updateModalConfirmCallback) {
    window.updateModalConfirmCallback();
  }
}

// Cancel update
function updateModalCancel() {
  const modal = document.querySelector('.update-modal-overlay');
  if (!modal) return;

  // Hide modal
  modal.classList.remove('show');
  document.body.style.overflow = '';

  setTimeout(() => {
    modal.remove();
  }, 300);

  // Call cancel callback
  if (window.updateModalCancelCallback) {
    window.updateModalCancelCallback();
  }
}

// Update download progress
function updateDownloadProgress(percent) {
  const fill = document.getElementById('updateProgressFill');
  const text = document.getElementById('updateProgressText');

  if (fill) {
    fill.style.width = percent + '%';
  }

  if (text) {
    if (percent < 100) {
      text.textContent = `${Math.round(percent)}% complete`;
    } else {
      text.textContent = 'Download complete!';
    }
  }
}

// Show install ready modal with custom UI (no native dialog)
function showInstallReadyModal() {
  const modal = document.querySelector('.update-modal-overlay');
  if (!modal) return;

  const modalBody = modal.querySelector('.update-modal-body');
  modalBody.innerHTML = `
    <div class="update-install-ready">
      <div class="update-install-icon">✅</div>
      <div class="update-install-title">Update Downloaded Successfully!</div>
      <p class="update-install-message">
        Restart TakoBot now to install the update and enjoy the latest features.
      </p>
      <div class="update-modal-actions">
        <button class="update-modal-btn update-modal-btn-secondary" onclick="updateModalCancel()">
          Restart Later
        </button>
        <button class="update-modal-btn update-modal-btn-primary" onclick="restartAndInstall()">
          Restart Now
        </button>
      </div>
    </div>
  `;
}

// Restart and install
function restartAndInstall() {
  if (window.electronAPI && window.electronAPI.quitAndInstall) {
    window.electronAPI.quitAndInstall();
  }
}

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const modal = document.querySelector('.update-modal-overlay');
    if (modal && modal.classList.contains('show')) {
      updateModalCancel();
    }
  }
});

// Close modal on overlay click
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('update-modal-overlay')) {
    updateModalCancel();
  }
});
