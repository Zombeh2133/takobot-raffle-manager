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

      // Query ONLY the minimal columns that definitely exist
      const result = await pool.query(`
        SELECT
          id,
          username,
          is_admin,
          created_at
        FROM users
        ORDER BY created_at DESC
      `);

      // Map to expected frontend format
      const users = result.rows.map(user => ({
        id: user.id,
        username: user.username,
        email: null, // Column might not exist
        role: user.is_admin ? 'admin' : 'user',
        is_active: true,
        last_login: null,
        created_at: user.created_at,
        created_by: null
      }));

      res.json({ ok: true, data: users });
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
      // VALIDATION: Username and password are required (email optional)
      // ============================================
      if (!username || !password) {
        return res.status(400).json({
          ok: false,
          error: 'Username and password are required'
        });
      }

      // ============================================
      // VALIDATION: Email format (if provided)
      // ============================================
      if (email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
          return res.status(400).json({
            ok: false,
            error: 'Invalid email format'
          });
        }
      }

      // Validate role - determine is_admin from role
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
      // CHECK: Email uniqueness (case-insensitive, if provided)
      // ============================================
      if (email) {
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
      }

      // Hash password
      const bcrypt = require('bcrypt');
      const hashedPassword = await bcrypt.hash(password, 10);

      // Determine is_admin based on role
      const isAdminFlag = userRole === 'admin';

      // Insert new user (only use columns that exist in your schema)
      const result = await pool.query(`
        INSERT INTO users (username, email, password_hash, is_admin)
        VALUES ($1, $2, $3, $4)
        RETURNING id, username, email, is_admin, created_at
      `, [username, email || null, hashedPassword, isAdminFlag]);

      // Map response to expected format
      const newUser = result.rows[0];
      res.json({ 
        ok: true, 
        data: {
          id: newUser.id,
          username: newUser.username,
          email: newUser.email,
          role: newUser.is_admin ? 'admin' : 'user',
          is_active: true,
          created_at: newUser.created_at,
          created_by: null
        }
      });
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
      const { email, role, password } = req.body;

      // Check if user exists
      const userExists = await pool.query('SELECT id FROM users WHERE id = $1', [id]);
      if (userExists.rows.length === 0) {
        return res.status(404).json({ ok: false, error: 'User not found' });
      }

      // Build dynamic update query (only for columns that exist)
      const updates = [];
      const values = [];
      let paramCount = 1;

      if (email !== undefined) {
        updates.push(`email = $${paramCount}`);
        values.push(email);
        paramCount++;
      }

      if (role !== undefined) {
        // Map role to is_admin
        const isAdminFlag = role === 'admin';
        updates.push(`is_admin = $${paramCount}`);
        values.push(isAdminFlag);
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

      // Add updated_at
      updates.push(`updated_at = NOW()`);
      values.push(id);

      const result = await pool.query(`
        UPDATE users
        SET ${updates.join(', ')}
        WHERE id = $${paramCount}
        RETURNING id, username, email, is_admin, created_at, updated_at
      `, values);

      // Map response to expected format
      const updatedUser = result.rows[0];
      res.json({ 
        ok: true, 
        data: {
          id: updatedUser.id,
          username: updatedUser.username,
          email: updatedUser.email,
          role: updatedUser.is_admin ? 'admin' : 'user',
          is_active: true,
          last_login: null,
          created_at: updatedUser.created_at,
          created_by: null
        }
      });
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

      // Query only columns that exist in your schema
      const result = await pool.query(`
        SELECT
          id,
          username,
          email,
          is_admin,
          created_at,
          updated_at
        FROM users
        WHERE id = $1
      `, [id]);

      if (result.rows.length === 0) {
        return res.status(404).json({ ok: false, error: 'User not found' });
      }

      // Map to expected format
      const user = result.rows[0];
      res.json({ 
        ok: true, 
        data: {
          id: user.id,
          username: user.username,
          email: user.email,
          role: user.is_admin ? 'admin' : 'user',
          is_active: true,
          last_login: null,
          created_at: user.created_at,
          created_by: null
        }
      });
    } catch (error) {
      console.error('Error fetching user:', error);
      res.status(500).json({ ok: false, error: error.message });
    }
  });

};
