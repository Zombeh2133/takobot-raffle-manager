/**
 * Sidebar Admin Control Script
 * Hides admin-only navigation items for non-admin users
 */

(async function initSidebarAdminControl() {
  try {
    // Check if user is admin
    const response = await fetch('/api/auth/current-user');
    
    if (!response.ok) {
      console.warn('Failed to check user status');
      return;
    }
    
    const data = await response.json();
    const isAdmin = data.data?.isAdmin === true;
    
    // If not admin, hide admin-only menu items
    if (!isAdmin) {
      const sidebarNav = document.getElementById('sidebarNav');
      if (!sidebarNav) return;
      
      // Hide Admin link
      const adminLink = Array.from(sidebarNav.querySelectorAll('.nav-item')).find(link => 
        link.textContent.includes('Admin') && link.getAttribute('href') === '/admin'
      );
      if (adminLink) {
        adminLink.style.display = 'none';
      }
      
      // Hide User Management link
      const userManagementLink = Array.from(sidebarNav.querySelectorAll('.nav-item')).find(link => 
        link.textContent.includes('User Management')
      );
      if (userManagementLink) {
        userManagementLink.style.display = 'none';
      }
      
      console.log('✅ Admin menu items hidden for non-admin user');
    } else {
      console.log('✅ Admin user - all menu items visible');
    }
  } catch (error) {
    console.error('Error checking admin status:', error);
  }
})();
