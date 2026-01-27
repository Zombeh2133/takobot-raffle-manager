const bcrypt = require('bcrypt');
const crypto = require('crypto');

// Helper function to generate UUID
function uuidv4() {
  return crypto.randomUUID();
}

const emailService = require('./email-service');

module.exports = function(app, pool) {

  // Request password reset
  app.post('/api/auth/forgot-password', async (req, res) => {
    const { email } = req.body;

    try {
      // Find user by email
      const userResult = await pool.query(
        'SELECT id, username, email FROM users WHERE LOWER(email) = LOWER($1)',
        [email]
      );

      if (userResult.rows.length === 0) {
        // Don't reveal if email exists or not (security best practice)
        return res.json({ 
          success: true, 
          message: 'If that email exists, a reset link has been sent.' 
        });
      }

      const user = userResult.rows[0];

      // Generate reset token
      const resetToken = uuidv4();
      const expiresAt = new Date(Date.now() + 3600000); // 1 hour from now

      // Save token to database
      await pool.query(
        'INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES ($1, $2, $3)',
        [user.id, resetToken, expiresAt]
      );

      // Send email
      await emailService.sendPasswordResetEmail(user.email, user.username, resetToken);

      res.json({ 
        success: true, 
        message: 'If that email exists, a reset link has been sent.' 
      });

    } catch (error) {
      console.error('Error requesting password reset:', error);
      res.status(500).json({ error: 'Failed to process password reset request' });
    }
  });

  // Validate reset token
  app.get('/api/auth/validate-reset-token/:token', async (req, res) => {
    const { token } = req.params;

    try {
      const result = await pool.query(
        `SELECT prt.*, u.username, u.email 
         FROM password_reset_tokens prt
         JOIN users u ON prt.user_id = u.id
         WHERE prt.token = $1 AND prt.used = FALSE AND prt.expires_at > NOW()`,
        [token]
      );

      if (result.rows.length === 0) {
        return res.status(400).json({ valid: false, error: 'Invalid or expired token' });
      }

      res.json({ valid: true, username: result.rows[0].username });

    } catch (error) {
      console.error('Error validating token:', error);
      res.status(500).json({ error: 'Failed to validate token' });
    }
  });

  // Reset password
  app.post('/api/auth/reset-password', async (req, res) => {
    const { token, newPassword } = req.body;

    if (!newPassword || newPassword.length < 6) {
      return res.status(400).json({ error: 'Password must be at least 6 characters' });
    }

    try {
      // Validate token
      const tokenResult = await pool.query(
        `SELECT prt.*, u.id as user_id 
         FROM password_reset_tokens prt
         JOIN users u ON prt.user_id = u.id
         WHERE prt.token = $1 AND prt.used = FALSE AND prt.expires_at > NOW()`,
        [token]
      );

      if (tokenResult.rows.length === 0) {
        return res.status(400).json({ error: 'Invalid or expired token' });
      }

      const tokenData = tokenResult.rows[0];

      // Hash new password
      const hashedPassword = await bcrypt.hash(newPassword, 10);

      // Update user's password
      await pool.query(
        'UPDATE users SET password_hash = $1, updated_at = NOW() WHERE id = $2',
        [hashedPassword, tokenData.user_id]
      );

      // Mark token as used
      await pool.query(
        'UPDATE password_reset_tokens SET used = TRUE WHERE token = $1',
        [token]
      );

      res.json({ success: true, message: 'Password reset successfully' });

    } catch (error) {
      console.error('Error resetting password:', error);
      res.status(500).json({ error: 'Failed to reset password' });
    }
  });

};

