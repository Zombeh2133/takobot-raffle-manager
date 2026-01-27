/**
 * User Management Routes
 * Handles CRUD operations for user accounts
 */

module.exports = function(app, pool) {

  // GET all users
  app.get('/api/users/all', async (req, res) => {
    try {
      const isAdmin = req.headers['x-user-admin'] === 'true';
      if (!isAdmin) {
        return res.status(403).json({ ok: false, error: 'Admin access required' });
      }

      const result = await pool.query(`
        SELECT 
          id, 
          username, 
          email, 
          role, 
          is_active, 
          last_login, 
          created_at, 
          created_by 
        FROM users 
        ORDER BY created_at DESC
      `);

      res.json({ ok: true, data: result.rows });
    } catch (error) {
      console.error('Error fetching users:', error);
      res.status(500).json({ ok: false, error: error.message });
    }
  });

// CREATE new user
app.post('/api/users', async (req, res) => {
  try {
    const isAdmin = req.headers['x-user-admin'] === 'true';
    if (!isAdmin) {
      return res.status(403).json({ ok: false, error: 'Admin access required' });
    }

    const { username, email, password, role } = req.body;

    // ============================================
    // VALIDATION: Username, email, and password are required
    // ============================================
    if (!username || !password || !email) {
      return res.status(400).json({
        ok: false,
        error: 'Username, email, and password are required'
      });
    }

    // ============================================
    // VALIDATION: Email format
    // ============================================
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return res.status(400).json({
        ok: false,
        error: 'Invalid email format'
      });
    }

    // Validate role
    const validRoles = ['user', 'moderator', 'admin'];
    const userRole = role || 'user'; // Default to 'user' role
    if (!validRoles.includes(userRole)) {
      return res.status(400).json({
        ok: false,
        error: 'Invalid role. Must be user, moderator, or admin'
      });
    }

    // ============================================
    // CHECK: Username uniqueness (case-insensitive)
    // ============================================
    const existingUser = await pool.query(
      'SELECT id FROM users WHERE LOWER(username) = LOWER($1)',
      [username]
    );

    if (existingUser.rows.length > 0) {
      return res.status(409).json({
        ok: false,
        error: 'Username already exists'
      });
    }

    // ============================================
    // CHECK: Email uniqueness (case-insensitive)
    // ============================================
    const existingEmail = await pool.query(
      'SELECT id FROM users WHERE LOWER(email) = LOWER($1)',
      [email]
    );

    if (existingEmail.rows.length > 0) {
      return res.status(409).json({
        ok: false,
        error: 'Email already exists'
      });
    }

    // Hash password
    const bcrypt = require('bcrypt');
    const hashedPassword = await bcrypt.hash(password, 10);

    // Get current user's username for created_by
    const createdBy = req.headers['x-user-name'] || 'admin';

    // Insert new user
    const result = await pool.query(`
      INSERT INTO users (username, email, password_hash, role, is_active, created_by)
      VALUES ($1, $2, $3, $4, true, $5)
      RETURNING id, username, email, role, is_active, created_at, created_by
    `, [username, email, hashedPassword, userRole, createdBy]);

    res.json({ ok: true, data: result.rows[0] });
  } catch (error) {
    console.error('Error creating user:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

  // UPDATE user
  app.put('/api/users/:id', async (req, res) => {
    try {
      const isAdmin = req.headers['x-user-admin'] === 'true';
      if (!isAdmin) {
        return res.status(403).json({ ok: false, error: 'Admin access required' });
      }

      const { id } = req.params;
      const { email, role, is_active, password } = req.body;

      // Check if user exists
      const userExists = await pool.query('SELECT id FROM users WHERE id = $1', [id]);
      if (userExists.rows.length === 0) {
        return res.status(404).json({ ok: false, error: 'User not found' });
      }

      // Build dynamic update query
      const updates = [];
      const values = [];
      let paramCount = 1;

      if (email !== undefined) {
        updates.push(`email = $${paramCount}`);
        values.push(email);
        paramCount++;
      }

      if (role !== undefined) {
        updates.push(`role = $${paramCount}`);
        values.push(role);
        paramCount++;
      }

      if (is_active !== undefined) {
        updates.push(`is_active = $${paramCount}`);
        values.push(is_active);
        paramCount++;
      }

      if (password) {
        const bcrypt = require('bcrypt');
        const hashedPassword = await bcrypt.hash(password, 10);
        updates.push(`password_hash = $${paramCount}`);
        values.push(hashedPassword);
        paramCount++;
      }

      if (updates.length === 0) {
        return res.status(400).json({ ok: false, error: 'No fields to update' });
      }

      values.push(id);

      const result = await pool.query(`
        UPDATE users 
        SET ${updates.join(', ')}
        WHERE id = $${paramCount}
        RETURNING id, username, email, role, is_active, last_login, created_at, created_by
      `, values);

      res.json({ ok: true, data: result.rows[0] });
    } catch (error) {
      console.error('Error updating user:', error);
      res.status(500).json({ ok: false, error: error.message });
    }
  });

  // DELETE user
  app.delete('/api/users/:id', async (req, res) => {
    try {
      const isAdmin = req.headers['x-user-admin'] === 'true';
      if (!isAdmin) {
        return res.status(403).json({ ok: false, error: 'Admin access required' });
      }

      const { id } = req.params;

      // Prevent deleting your own account
      const currentUserId = req.headers['x-user-id'];
      if (currentUserId === id) {
        return res.status(400).json({ 
          ok: false, 
          error: 'Cannot delete your own account' 
        });
      }

      // Check if user exists
      const userExists = await pool.query('SELECT id FROM users WHERE id = $1', [id]);
      if (userExists.rows.length === 0) {
        return res.status(404).json({ ok: false, error: 'User not found' });
      }

      // Delete user
      await pool.query('DELETE FROM users WHERE id = $1', [id]);

      res.json({ ok: true, message: 'User deleted successfully' });
    } catch (error) {
      console.error('Error deleting user:', error);
      res.status(500).json({ ok: false, error: error.message });
    }
  });

  // GET single user by ID
  app.get('/api/users/:id', async (req, res) => {
    try {
      const isAdmin = req.headers['x-user-admin'] === 'true';
      if (!isAdmin) {
        return res.status(403).json({ ok: false, error: 'Admin access required' });
      }

      const { id } = req.params;

      const result = await pool.query(`
        SELECT 
          id, 
          username, 
          email, 
          role, 
          is_active, 
          last_login, 
          created_at, 
          created_by 
        FROM users 
        WHERE id = $1
      `, [id]);

      if (result.rows.length === 0) {
        return res.status(404).json({ ok: false, error: 'User not found' });
      }

      res.json({ ok: true, data: result.rows[0] });
    } catch (error) {
      console.error('Error fetching user:', error);
      res.status(500).json({ ok: false, error: error.message });
    }
  });

};
