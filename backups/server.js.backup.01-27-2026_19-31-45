const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');
const path = require('path');
const { spawn } = require('child_process');
require('dotenv').config();

const app = express();
const port = process.env.PORT || 3000;

// PostgreSQL connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

app.use(cors());
app.use(express.json());

// Serve the React build files
app.use(express.static(path.join(__dirname, 'dist')));

// Serve sidebar admin control script
app.get('/sidebar-admin-control.js', (req, res) => {
  res.sendFile(path.join(__dirname, 'sidebar-admin-control.js'));
});

// Serve admin nav control script
app.get('/admin_nav_control.js', (req, res) => {
  res.sendFile(path.join(__dirname, 'admin_nav_control.js'));
});

// Serve background polling script
app.get('/background-polling.js', (req, res) => {
  res.sendFile(path.join(__dirname, '../app/static/background-polling.js'));
});

// Serve global scan indicator script
app.get('/global-scan-indicator.js', (req, res) => {
  res.sendFile(path.join(__dirname, '../app/static/global-scan-indicator.js'));
});

// Serve static files from templates/pages
app.use(express.static(path.join(__dirname, '../app/templates/pages')));

// Test endpoint
app.get('/api/test', async (req, res) => {
  try {
    const result = await pool.query('SELECT NOW()');
    res.json({ ok: true, time: result.rows[0].now, message: 'Database connected!' });
  } catch (error) {
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============ PAYPAL / GMAIL ENDPOINTS ============

// Check if Gmail OAuth credentials exist
app.get('/api/paypal/check-credentials', async (req, res) => {
  try {
    const username = req.headers['x-user-name'];
    
    if (!username) {
      return res.status(401).json({ ok: false, error: 'User not authenticated' });
    }

    const fs = require('fs');
    const credentialsPath = path.join(__dirname, '../app/data/users', username, 'gmail_credentials.json');
    
    // Check if credentials file exists
    const hasCredentials = fs.existsSync(credentialsPath);
    
    res.json({ 
      ok: true, 
      hasCredentials: hasCredentials 
    });
  } catch (error) {
    console.error('Error checking credentials:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============ ACTIVE RAFFLE ENDPOINTS ============

// Save active raffle state
app.post('/api/raffle/save', async (req, res) => {
  try {
    const { redditLink, totalSpots, costPerSpot, pollingInterval, participants, fastRaffleEnabled, fastRaffleStartTime } = req.body;
    
    // Get username from headers (set by FastAPI proxy)
    const username = req.headers['x-user-name'];
    
    if (!username) {
      return res.status(401).json({ ok: false, error: 'User not authenticated' });
    }

    // Delete only THIS user's active raffle
    await pool.query('DELETE FROM active_raffle WHERE username = $1', [username]);

    const result = await pool.query(
      `INSERT INTO active_raffle (reddit_link, total_spots, cost_per_spot, polling_interval, participants, username, updated_at, fast_raffle_enabled, fast_raffle_start_time)
       VALUES ($1, $2, $3, $4, $5, $6, NOW(), $7, $8)
       RETURNING *`,
      [redditLink, totalSpots, costPerSpot, pollingInterval, JSON.stringify(participants), username, fastRaffleEnabled || false, fastRaffleStartTime || null]
    );

    res.json({ ok: true, data: result.rows[0] });
  } catch (error) {
    console.error('Error saving raffle:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Load active raffle state
app.get('/api/raffle/load', async (req, res) => {
  try {
    // Get username from headers (set by FastAPI proxy)
    const username = req.headers['x-user-name'];
    
    if (!username) {
      return res.status(401).json({ ok: false, error: 'User not authenticated' });
    }

    // Get only THIS user's active raffle
    const result = await pool.query(
      'SELECT * FROM active_raffle WHERE username = $1 ORDER BY id DESC LIMIT 1',
      [username]
    );

    if (result.rows.length === 0) {
      return res.json({ ok: true, data: null });
    }

    const raffle = result.rows[0];
    res.json({
      ok: true,
      data: {
        id: raffle.id,  // Include raffle ID
        redditLink: raffle.reddit_link,
        totalSpots: raffle.total_spots,
        costPerSpot: raffle.cost_per_spot,
        pollingInterval: raffle.polling_interval,
        participants: raffle.participants || [],
        fastRaffleEnabled: raffle.fast_raffle_enabled || false,
        fastRaffleStartTime: raffle.fast_raffle_start_time || null
      }
    });
  } catch (error) {
    console.error('Error loading raffle:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Clear active raffle
app.delete('/api/raffle/clear', async (req, res) => {
  try {
    // Get username from headers (set by FastAPI proxy)
    const username = req.headers['x-user-name'];
    
    if (!username) {
      return res.status(401).json({ ok: false, error: 'User not authenticated' });
    }

    // Delete only THIS user's active raffle
    await pool.query('DELETE FROM active_raffle WHERE username = $1', [username]);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error clearing raffle:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============ RAFFLE HISTORY ENDPOINTS ============

// Save raffle to history
app.post('/api/raffle/history', async (req, res) => {
  try {
    const {
      raffleDate,
      status,
      redditLink,
      totalSpots,
      costPerSpot,
      participants,
      totalOwed,
      totalPaid,
      winner,
      username,
      fastRaffleEnabled,
      fastRaffleStartTime
    } = req.body;

    const result = await pool.query(
      `INSERT INTO raffle_history
       (raffle_date, status, reddit_link, total_spots, cost_per_spot, participants, total_owed, total_paid, winner, username, fast_raffle_enabled, fast_raffle_start_time)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
       RETURNING *`,
      [
        raffleDate,
        status,
        redditLink,
        totalSpots,
        costPerSpot,
        JSON.stringify(participants),
        totalOwed,
        totalPaid,
        winner ? JSON.stringify(winner) : null,
        username,
        fastRaffleEnabled || false,
        fastRaffleStartTime || null
      ]
    );

    res.json({ ok: true, data: result.rows[0] });
  } catch (error) {
    console.error('Error saving to history:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get raffle history
app.get('/api/raffle/history', async (req, res) => {
  try {
    // Get username from headers (set by FastAPI proxy)
    const username = req.headers['x-user-name'];
    
    console.log('📋 [GET /api/raffle/history] Received request');
    console.log('   Headers:', req.headers);
    console.log('   Username from header:', username);
    
    if (!username) {
      return res.status(401).json({ ok: false, error: 'User not authenticated' });
    }

    console.log(`   Fetching raffles for user: ${username}`);

    // Get only THIS user's raffle history
    const result = await pool.query(
      'SELECT * FROM raffle_history WHERE username = $1 ORDER BY raffle_date DESC',
      [username]
    );

    console.log(`   Found ${result.rows.length} raffles for ${username}`);

    const history = result.rows.map(row => ({
      id: row.id,
      date: row.raffle_date,
      status: row.status,
      redditLink: row.reddit_link,
      totalSpots: row.total_spots,
      costPerSpot: row.cost_per_spot,
      participants: row.participants,
      totalOwed: row.total_owed,
      totalPaid: row.total_paid,
      winner: row.winner,
      username: row.username
    }));

    res.json({ ok: true, data: history });
  } catch (error) {
    console.error('Error fetching history:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Delete all raffle history
app.delete('/api/raffle/history', async (req, res) => {
  try {
    await pool.query('DELETE FROM raffle_history');
    res.json({ ok: true });
  } catch (error) {
    console.error('Error deleting history:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Delete individual raffle from history
app.delete('/api/raffle/history/:id', async (req, res) => {
  try {
    const { id } = req.params;
    await pool.query('DELETE FROM raffle_history WHERE id = $1', [id]);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error deleting raffle:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============ ACTIVITY LOG ENDPOINTS ============

// Add activity
app.post('/api/activity/log', async (req, res) => {
  try {
    const { type, title, details, badge, raffle_id, username } = req.body;
    
    // DEBUG: Log what we received
    console.log('🔍 POST /api/activity/log received:');
    console.log('  req.body:', req.body);
    console.log('  username from body:', username);
    console.log('  type:', type, 'title:', title);

    const result = await pool.query(
      `INSERT INTO activity_log (type, title, details, badge, raffle_id, username, timestamp)
       VALUES ($1, $2, $3, $4, $5, $6, NOW())
       RETURNING *`,
      [type, title, details, badge, raffle_id, username]
    );
    
    // DEBUG: Log what was inserted
    console.log('✅ Inserted activity with username:', result.rows[0].username);

    res.json({ ok: true, data: result.rows[0] });
  } catch (error) {
    console.error('Error logging activity:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get activity log
app.get('/api/activity/list', async (req, res) => {
  try {
    const result = await pool.query(
      'SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT 100'
    );

    const activities = result.rows.map(row => ({
      id: row.id,
      type: row.type,
      title: row.title,
      details: row.details,
      badge: row.badge,
      raffle_id: row.raffle_id,
      username: row.username,
      timestamp: row.timestamp
    }));

    res.json({ ok: true, data: activities });
  } catch (error) {
    console.error('Error fetching activities:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Clear activity log
app.delete('/api/activity/clear', async (req, res) => {
  try {
    await pool.query('DELETE FROM activity_log');
    res.json({ ok: true });
  } catch (error) {
    console.error('Error clearing activity log:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============ SETTINGS ENDPOINTS ============

// Save setting
app.post('/api/settings', async (req, res) => {
  try {
    const { key, value } = req.body;

    await pool.query(
      `INSERT INTO settings (key, value, updated_at)
       VALUES ($1, $2, NOW())
       ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = NOW()`,
      [key, value]
    );

    res.json({ ok: true });
  } catch (error) {
    console.error('Error saving setting:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get setting
app.get('/api/settings/:key', async (req, res) => {
  try {
    const result = await pool.query(
      'SELECT value FROM settings WHERE key = $1',
      [req.params.key]
    );

    if (result.rows.length === 0) {
      return res.json({ ok: true, data: null });
    }

    res.json({ ok: true, data: result.rows[0].value });
  } catch (error) {
    console.error('Error fetching setting:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============ REDDIT SCANNING ENDPOINT ============

app.post('/api/reddit/scan', async (req, res) => {
  try {
    const { redditLink, costPerSpot } = req.body;

    if (!redditLink || !costPerSpot) {
      return res.status(400).json({
        ok: false,
        error: 'Missing redditLink or costPerSpot'
      });
    }

    // Path to Python script (AI-powered version)
    const pythonScript = path.join(__dirname, '../app/reddit_parser.py');

    console.log('Starting Reddit scan:', redditLink, 'Cost:', costPerSpot);

    // Spawn Python process
    const python = spawn('python3', [pythonScript, redditLink, costPerSpot.toString()], {
      timeout: 300000  // Increased to 300 seconds (5 minutes) for OpenAI API calls
    });

    let stdout = '';
    let stderr = '';

    python.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    python.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    python.on('close', async (code) => {
      // Log for debugging
      console.log('Python exit code:', code);
      console.log('Python stdout length:', stdout.length);
      if (stderr) console.log('Python stderr:', stderr);

      if (code !== 0) {
        console.error('Python script failed with code:', code);
        console.error('Stderr:', stderr);
        console.error('Stdout:', stdout);

        // Try to parse error from stdout
        try {
          const errorResult = JSON.parse(stdout);
          return res.status(500).json(errorResult);
        } catch (e) {
          return res.status(500).json({
            ok: false,
            error: stderr || stdout || 'Reddit scan failed'
          });
        }
      }

      // Try to parse the result
      try {
        const result = JSON.parse(stdout.trim());
        console.log('Reddit scan result:', result.ok ? `Success - ${result.participants?.length || 0} participants` : result.error);

        // FILTER OUT DUPLICATES - Get existing participants from DB
        if (result.ok && result.participants && result.participants.length > 0) {
          // Get username from headers (set by FastAPI proxy)
          const username = req.headers['x-user-name'];
          
          const existingResult = await pool.query(
            'SELECT participants FROM active_raffle WHERE username = $1 LIMIT 1',
            [username]
          );

          const existingParticipants = existingResult.rows[0]?.participants || [];

          // Create a Set of existing USERNAMES (unique identifier)
          const existingUsernames = new Set(
            existingParticipants.map(p => (p.redditUser || p.username || '').trim().toLowerCase())
          );

          // Filter to only NEW participants (usernames not seen before)
          const newParticipants = result.participants.filter(p => {
            const username = (p.redditUser || p.username || '').trim().toLowerCase();
            return username && !existingUsernames.has(username);
          });

          console.log(`Filtered: ${result.participants.length} total, ${newParticipants.length} new, ${result.participants.length - newParticipants.length} duplicates removed`);

          // Return only new participants
          result.participants = newParticipants;
        }

        res.json(result);
      } catch (e) {
        console.error('Failed to parse Python output:', e.message);
        console.error('Raw stdout:', stdout);
        res.status(500).json({
          ok: false,
          error: `Failed to parse scan results: ${e.message}. Output length: ${stdout.length}`
        });
      }
    });

    // Handle timeout
    python.on('error', (err) => {
      console.error('Python process error:', err);
      res.status(500).json({
        ok: false,
        error: `Process error: ${err.message}`
      });
    });

  } catch (error) {
    console.error('Reddit scan error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============ BACKGROUND POLLING REDDIT SCAN ============
// This endpoint is called by background-polling.js to auto-scan Reddit
app.post('/api/scan-reddit', async (req, res) => {
  try {
    const { raffle_id } = req.body;

    // Get username from headers (set by FastAPI proxy)
    const username = req.headers['x-user-name'];
    
    if (!username) {
      return res.status(401).json({ ok: false, error: 'User not authenticated' });
    }

    console.log(`🔄 Background scan triggered for user: ${username}`);

    // Get the user's active raffle
    const raffleResult = await pool.query(
      'SELECT * FROM active_raffle WHERE username = $1 ORDER BY id DESC LIMIT 1',
      [username]
    );

    if (raffleResult.rows.length === 0) {
      return res.json({ 
        ok: false, 
        error: 'No active raffle found',
        new_participants: [],
        spots_remaining: 0
      });
    }

    const activeRaffle = raffleResult.rows[0];
    const redditLink = activeRaffle.reddit_link;
    const costPerSpot = activeRaffle.cost_per_spot;
    const totalSpots = activeRaffle.total_spots || 0;
    const existingParticipants = activeRaffle.participants || [];

    if (!redditLink) {
      return res.json({
        ok: false,
        error: 'No Reddit link configured',
        new_participants: [],
        spots_remaining: 0
      });
    }

    console.log(`📍 Scanning Reddit: ${redditLink}`);

    // Path to Python script (AI-powered version)
    const pythonScript = path.join(__dirname, '../app/reddit_parser.py');

    // Spawn Python process
    const python = spawn('python3', [pythonScript, redditLink, costPerSpot.toString()], {
      timeout: 300000  // 5 minutes
    });

    let stdout = '';
    let stderr = '';

    python.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    python.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    python.on('close', async (code) => {
      if (code !== 0) {
        console.error('❌ Python script failed:', stderr);
        return res.json({
          ok: false,
          error: 'Reddit scan failed',
          new_participants: [],
          spots_remaining: 0
        });
      }

      try {
        const result = JSON.parse(stdout.trim());

        if (!result.ok || !result.participants) {
          return res.json({
            ok: false,
            error: result.error || 'Scan failed',
            new_participants: [],
            spots_remaining: 0
          });
        }

        // Filter out duplicates - only return NEW participants
        const existingUsernames = new Set(
          existingParticipants.map(p => (p.redditUser || p.username || '').trim().toLowerCase())
        );

        const newParticipants = result.participants.filter(p => {
          const participantUsername = (p.redditUser || p.username || '').trim().toLowerCase();
          return participantUsername && !existingUsernames.has(participantUsername);
        });

        console.log(`✅ Scan complete: ${result.participants.length} total, ${newParticipants.length} new`);

        // Calculate spots remaining
        const allParticipants = [...existingParticipants, ...newParticipants];
        const totalSpotsAssigned = allParticipants.reduce((sum, p) => {
          return sum + (p.spots ? p.spots.length : 0);
        }, 0);
        const spotsRemaining = Math.max(0, totalSpots - totalSpotsAssigned);

        console.log(`📊 Spots calculation: Total=${totalSpots}, Assigned=${totalSpotsAssigned}, Remaining=${spotsRemaining}`);

        // If there are new participants, update the database
        if (newParticipants.length > 0) {
          const updatedParticipants = [...existingParticipants, ...newParticipants];
          
          await pool.query(
            'UPDATE active_raffle SET participants = $1, updated_at = NOW() WHERE username = $2',
            [JSON.stringify(updatedParticipants), username]
          );

          console.log(`💾 Database updated with ${newParticipants.length} new participants`);
        }

        // Return response
        res.json({
          ok: true,
          new_participants: newParticipants,
          total_participants: allParticipants.length,
          spots_remaining: spotsRemaining,
          message: newParticipants.length > 0 
            ? `Found ${newParticipants.length} new participant(s)` 
            : 'No new participants'
        });

      } catch (e) {
        console.error('❌ Failed to parse Python output:', e.message);
        res.json({
          ok: false,
          error: 'Failed to parse scan results',
          new_participants: [],
          spots_remaining: 0
        });
      }
    });

    python.on('error', (err) => {
      console.error('❌ Python process error:', err);
      res.json({
        ok: false,
        error: 'Scan process error',
        new_participants: [],
        spots_remaining: 0
      });
    });

  } catch (error) {
    console.error('❌ Background scan error:', error);
    res.status(500).json({ 
      ok: false, 
      error: error.message,
      new_participants: [],
      spots_remaining: 0
    });
  }
});

// System Status endpoint
app.get('/api/system/status', async (req, res) => {
  try {
    const fs = require('fs');
    const path = require('path');

    // Get current user from headers (passed by FastAPI proxy)
    const username = req.headers['x-user-name'];
    
    console.log(`[System Status] Raw headers:`, req.headers);
    console.log(`[System Status] Username from header:`, username);
    
    // Check Gmail OAuth credentials for the current user
    let gmailConnected = false;
    if (username) {
      const userCredPath = path.join(__dirname, '..', 'app', 'data', 'users', username, 'gmail_credentials.json');
      const userTokenPath = path.join(__dirname, '..', 'app', 'data', 'users', username, 'token.json');
      
      console.log(`[System Status] __dirname: ${__dirname}`);
      console.log(`[System Status] Checking credentials at: ${userCredPath}`);
      console.log(`[System Status] Checking token at: ${userTokenPath}`);
      
      // Gmail is connected if either credentials or token file exists
      const credExists = fs.existsSync(userCredPath);
      const tokenExists = fs.existsSync(userTokenPath);
      gmailConnected = credExists || tokenExists;
      
      console.log(`[System Status] Credentials exists: ${credExists}`);
      console.log(`[System Status] Token exists: ${tokenExists}`);
      console.log(`[System Status] Gmail Connected: ${gmailConnected}`);
    } else {
      console.log(`[System Status] No username in headers - user not logged in`);
    }

    // Check bot status (you can make this dynamic later)
    const botOnline = true; // Change to false when you take it offline

    // Last updated time (using process start time for now)
    const lastUpdated = new Date();
    const now = new Date();
    const diffMs = now - lastUpdated;
    const diffMins = Math.floor(diffMs / 60000);

    let lastUpdatedText;
    if (diffMins < 1) lastUpdatedText = 'Just now';
    else if (diffMins < 60) lastUpdatedText = `${diffMins}m ago`;
    else if (diffMins < 1440) lastUpdatedText = `${Math.floor(diffMins / 60)}h ago`;
    else lastUpdatedText = `${Math.floor(diffMins / 1440)}d ago`;

    res.json({
      ok: true,
      data: {
        gmailConnected,
        botOnline,
        lastUpdated: lastUpdatedText
      }
    });
  } catch (error) {
    console.error('System status error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============ USER AUTHENTICATION ENDPOINTS ============
app.post('/api/auth/login', async (req, res) => {
  try {
    const { username, password } = req.body;

    if (!username || !password) {
      return res.status(400).json({ ok: false, error: 'Username and password are required' });
    }

    const result = await pool.query(
      'SELECT id, username, is_admin, password_hash FROM users WHERE LOWER(username) = LOWER($1)',
      [username]
    );

    if (result.rows.length === 0) {
      return res.status(401).json({ ok: false, error: 'Invalid credentials' });
    }

    const user = result.rows[0];

    // Verify password
    const bcrypt = require('bcrypt');
    const isValid = await bcrypt.compare(password, user.password_hash);

    if (!isValid) {
      return res.status(401).json({ ok: false, error: 'Invalid credentials' });
    }

    res.json({
      ok: true,
      data: {
        id: user.id,
        username: user.username,
        isAdmin: user.is_admin
      }
    });
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get current user endpoint (for checking admin status)
app.get('/api/auth/current-user', async (req, res) => {
  try {
    // Get user info from headers (passed by FastAPI proxy)
    const username = req.headers['x-user-name'];
    const isAdmin = req.headers['x-user-admin'] === 'true';
    const userId = req.headers['x-user-id'];

    if (!username || !userId) {
      return res.json({ ok: false, data: null });
    }

    res.json({
      ok: true,
      data: {
        id: parseInt(userId),
        username: username,
        isAdmin: isAdmin
      }
    });
  } catch (error) {
    console.error('Current user error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Logout endpoint
app.post('/api/auth/logout', async (req, res) => {
  try {
    // TODO: Clear session when session-based authentication is implemented
    // For now, just return success
    res.json({ ok: true, message: 'Logged out successfully' });
  } catch (error) {
    console.error('Logout error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============ ADMIN ANALYTICS ENDPOINTS ============

// Get admin analytics for a specific year
app.get('/api/admin/analytics/:year', async (req, res) => {
  try {
    // Check admin access from headers (passed by FastAPI proxy)
    const isAdmin = req.headers['x-user-admin'] === 'true';
    const username = req.headers['x-user-name'];

    if (!isAdmin) {
      return res.status(403).json({ ok: false, error: 'Access denied. Admin only.' });
    }

    const year = parseInt(req.params.year);

    // Get all raffles for the specified year
    const raffleResult = await pool.query(
      `SELECT * FROM raffle_history
       WHERE EXTRACT(YEAR FROM raffle_date) = $1
       ORDER BY raffle_date`,
      [year]
    );

    const raffles = raffleResult.rows;

    // Calculate monthly statistics
    const monthlyStats = Array(12).fill(null).map((_, index) => {
      const monthRaffles = raffles.filter(r => {
        const raffleMonth = new Date(r.raffle_date).getMonth();
        return raffleMonth === index;
      });

      const completed = monthRaffles.filter(r => r.status === 'completed').length;
      const cancelled = monthRaffles.filter(r => r.status === 'cancelled').length;
      const total = completed + cancelled;
      const revenue = monthRaffles
        .filter(r => r.status === 'completed')
        .reduce((sum, r) => sum + (parseFloat(r.total_paid) || 0), 0);
      const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;

      return {
        month: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][index],
        completed,
        cancelled,
        total,
        revenue: Math.round(revenue),
        completionRate
      };
    });

    // Calculate totals
    const totalCompleted = raffles.filter(r => r.status === 'completed').length;
    const totalCancelled = raffles.filter(r => r.status === 'cancelled').length;
    const totalRevenue = raffles
      .filter(r => r.status === 'completed')
      .reduce((sum, r) => sum + (parseFloat(r.total_paid) || 0), 0);

    // Get unique participants count (rough estimate based on participants array)
    const allParticipants = new Set();
    raffles.forEach(raffle => {
      if (raffle.participants) {
        raffle.participants.forEach(p => {
          if (p.redditUser || p.username) {
            allParticipants.add(p.redditUser || p.username);
          }
        });
      }
    });
    const uniqueUsers = allParticipants.size;

    res.json({
      ok: true,
      data: {
        year,
        monthly: monthlyStats,
        totalCompleted,
        totalCancelled,
        totalRevenue: Math.round(totalRevenue),
        uniqueUsers
      }
    });

  } catch (error) {
    console.error('Admin analytics error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============ PROFILE ENDPOINTS ============

// Get profile
app.get('/api/profile', async (req, res) => {
  try {
    // Get user info from headers (passed by FastAPI proxy)
    const username = req.headers['x-user-name'];

    console.log('[Profile GET] Username from header:', username);

    if (!username) {
      return res.status(401).json({ ok: false, error: 'Not authenticated' })
;
    }

    // Try basic query first
    let result;
    try {
      result = await pool.query(
        'SELECT id, username, email, fullname, default_polling, timezone, bio, created_at FROM users WHERE username = $1',
        [username]
      );
    } catch (queryError) {
      console.error('[Profile GET] Query error:', queryError.message);
      
      // Try simpler query without potentially missing columns
      result = await pool.query(
        'SELECT id, username, created_at FROM users WHERE username = $1',
        [username]
      );
      
      console.log('[Profile GET] Using fallback query, some fields may be null');
    }

    if (result.rows.length === 0) {
      return res.status(404).json({ ok: false, error: 'User not found' });
    }

    const user = result.rows[0];
    
    // Check if is_admin column exists by trying to query it separately
    let isAdmin = false;
    try {
      const adminResult = await pool.query(
        'SELECT is_admin FROM users WHERE username = $1',
        [username]
      );
      isAdmin = adminResult.rows[0]?.is_admin || false;
    } catch (e) {
      // Column doesn't exist yet, default to false
      console.log('[Profile GET] is_admin column not found, defaulting to false');
    }
    
    res.json({
      ok: true,
      data: {
        id: user.id,
        username: user.username,
        email: user.email || null,
        fullname: user.fullname || null,
        isAdmin: isAdmin,
        defaultPolling: user.default_polling || null,
        timezone: user.timezone || null,
        bio: user.bio || null,
        createdAt: user.created_at
      }
    });
  } catch (error) {
    console.error('[Profile GET] Profile fetch error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Update profile
app.put('/api/profile', async (req, res) => {
  try {
    const username = req.headers['x-user-name'] || 'maki'; // Get from headers or fallback
    const { email, fullname, defaultPolling, timezone, bio } = req.body;

    console.log('[Profile PUT] Updating profile for:', username);

    // Try full update with updated_at column
    let result;
    try {
      result = await pool.query(
        `UPDATE users
         SET email = $1, fullname = $2, default_polling = $3, timezone = $4, bio = $5, updated_at = NOW()
         WHERE username = $6
         RETURNING id, username, email, fullname, default_polling, timezone, bio, created_at`,
        [email, fullname, defaultPolling, timezone, bio, username]
      );
    } catch (updateError) {
      console.error('[Profile PUT] Update with updated_at failed:', updateError.message);
      
      // Try update without updated_at column
      result = await pool.query(
        `UPDATE users
         SET email = $1, fullname = $2, default_polling = $3, timezone = $4, bio = $5
         WHERE username = $6
         RETURNING id, username, email, fullname, default_polling, timezone, bio, created_at`,
        [email, fullname, defaultPolling, timezone, bio, username]
      );
      
      console.log('[Profile PUT] Updated without updated_at column');
    }

    if (result.rows.length === 0) {
      return res.status(404).json({ ok: false, error: 'User not found' });
    }

    const user = result.rows[0];
    
    // Try to get is_admin separately
    let isAdmin = false;
    try {
      const adminResult = await pool.query(
        'SELECT is_admin FROM users WHERE username = $1',
        [username]
      );
      isAdmin = adminResult.rows[0]?.is_admin || false;
    } catch (e) {
      console.log('[Profile PUT] is_admin column not found, defaulting to false');
    }

    res.json({ 
      ok: true, 
      data: {
        ...user,
        isAdmin,
        defaultPolling: user.default_polling,
        createdAt: user.created_at
      }
    });
  } catch (error) {
    console.error('[Profile PUT] Profile update error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get profile stats
app.get('/api/profile/stats', async (req, res) => {
  try {
    // Get user info from headers (passed by FastAPI proxy)
    const username = req.headers['x-user-name'];

    if (!username) {
      return res.status(401).json({ ok: false, error: 'Not authenticated' });
    }

    // Get user join date
    const userResult = await pool.query(
      'SELECT created_at FROM users WHERE username = $1',
      [username]
    );

    if (userResult.rows.length === 0) {
      return res.status(404).json({ ok: false, error: 'User not found' });
    }

    // Get comprehensive raffle stats - FILTERED BY USERNAME
    const raffleResult = await pool.query(
      `SELECT 
        COUNT(*) as total, 
        COUNT(CASE WHEN status = 'Completed' THEN 1 END) as completed,
        COUNT(CASE WHEN status = 'Cancelled' THEN 1 END) as cancelled,
        COUNT(CASE WHEN status = 'Active' OR status = 'Pending' THEN 1 END) as pending,
        COALESCE(SUM(total_paid), 0) as total_revenue,
        COALESCE(SUM(total_owed), 0) as total_owed,
        COALESCE(SUM(total_spots), 0) as total_spots,
        COALESCE(AVG(total_spots), 0) as avg_spots_per_raffle,
        COALESCE(AVG(cost_per_spot), 0) as avg_cost_per_spot,
        COALESCE(MAX(total_paid), 0) as highest_revenue,
        MIN(raffle_date) as first_raffle,
        MAX(raffle_date) as last_raffle
       FROM raffle_history 
       WHERE username = $1`,
      [username]
    );

    const stats = raffleResult.rows[0];

    // Calculate additional metrics
    const totalRaffles = parseInt(stats.total) || 0;
    const completedRaffles = parseInt(stats.completed) || 0;
    const cancelledRaffles = parseInt(stats.cancelled) || 0;
    const pendingRaffles = parseInt(stats.pending) || 0;
    const totalRevenue = parseFloat(stats.total_revenue) || 0;
    const totalOwed = parseFloat(stats.total_owed) || 0;
    const totalSpots = parseInt(stats.total_spots) || 0;
    const avgSpotsPerRaffle = parseFloat(stats.avg_spots_per_raffle) || 0;
    const avgCostPerSpot = parseFloat(stats.avg_cost_per_spot) || 0;
    const highestRevenue = parseFloat(stats.highest_revenue) || 0;
    
    // Success rate (completed / total)
    const successRate = totalRaffles > 0 ? (completedRaffles / totalRaffles) * 100 : 0;
    
    // Payment collection rate
    const paymentRate = totalOwed > 0 ? (totalRevenue / totalOwed) * 100 : 0;
    
    // Calculate actual UNIQUE participants across all raffles
    const rafflesWithParticipants = await pool.query(
      `SELECT participants FROM raffle_history WHERE username = $1 AND participants IS NOT NULL`,
      [username]
    );
    
    const uniqueParticipants = new Set();
    rafflesWithParticipants.rows.forEach(row => {
      if (row.participants && Array.isArray(row.participants)) {
        row.participants.forEach(p => {
          const redditUser = (p.redditUser || p.user || p.username || '').trim().toLowerCase();
          if (redditUser) {
            uniqueParticipants.add(redditUser);
          }
        });
      }
    });
    
    const totalUniqueParticipants = uniqueParticipants.size;

    res.json({
      ok: true,
      data: {
        // Core stats
        totalRaffles,
        completedRaffles,
        cancelledRaffles,
        pendingRaffles,
        totalRevenue,
        totalOwed,
        
        // Averages
        avgSpotsPerRaffle: Math.round(avgSpotsPerRaffle),
        avgCostPerSpot: Math.round(avgCostPerSpot * 100) / 100,
        
        // Records
        highestRevenue,
        
        // Calculated metrics
        successRate: Math.round(successRate * 100) / 100,
        paymentRate: Math.round(paymentRate * 100) / 100,
        totalUniqueParticipants,
        
        // Dates
        joinDate: userResult.rows[0].created_at,
        firstRaffle: stats.first_raffle,
        lastRaffle: stats.last_raffle,
        
        // Spot stats
        totalSpots
      }
    });
  } catch (error) {
    console.error('Profile stats error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get profile activity timeline
app.get('/api/profile/activity', async (req, res) => {
  try {
    const username = req.headers['x-user-name'];
    const limit = parseInt(req.query.limit) || 20;

    if (!username) {
      return res.status(401).json({ ok: false, error: 'Not authenticated' });
    }

    const result = await pool.query(
      `SELECT * FROM activity_log 
       WHERE username = $1 
       ORDER BY timestamp DESC 
       LIMIT $2`,
      [username, limit]
    );

    res.json({
      ok: true,
      data: result.rows
    });
  } catch (error) {
    console.error('Profile activity error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get monthly raffle stats for charts
app.get('/api/profile/monthly-stats', async (req, res) => {
  try {
    const username = req.headers['x-user-name'];
    const year = parseInt(req.query.year) || new Date().getFullYear();

    if (!username) {
      return res.status(401).json({ ok: false, error: 'Not authenticated' });
    }

    const result = await pool.query(
      `SELECT 
        EXTRACT(MONTH FROM raffle_date) as month,
        COUNT(*) as total_raffles,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
        SUM(total_paid) as revenue,
        SUM(total_spots) as spots_sold
       FROM raffle_history 
       WHERE username = $1 
         AND EXTRACT(YEAR FROM raffle_date) = $2
       GROUP BY EXTRACT(MONTH FROM raffle_date)
       ORDER BY month`,
      [username, year]
    );

    // Fill in missing months with zeros
    const monthlyData = Array.from({ length: 12 }, (_, i) => ({
      month: i + 1,
      monthName: new Date(year, i).toLocaleString('default', { month: 'short' }),
      totalRaffles: 0,
      completed: 0,
      revenue: 0,
      spotsSold: 0
    }));

    result.rows.forEach(row => {
      const monthIndex = parseInt(row.month) - 1;
      monthlyData[monthIndex] = {
        month: parseInt(row.month),
        monthName: new Date(year, monthIndex).toLocaleString('default', { month: 'short' }),
        totalRaffles: parseInt(row.total_raffles) || 0,
        completed: parseInt(row.completed) || 0,
        revenue: parseFloat(row.revenue) || 0,
        spotsSold: parseInt(row.spots_sold) || 0
      };
    });

    res.json({
      ok: true,
      data: {
        year,
        months: monthlyData
      }
    });
  } catch (error) {
    console.error('Monthly stats error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get top participants across all raffles
app.get('/api/profile/top-participants', async (req, res) => {
  try {
    const username = req.headers['x-user-name'];
    const limit = parseInt(req.query.limit) || 10;

    if (!username) {
      return res.status(401).json({ ok: false, error: 'Not authenticated' });
    }

    // This is a complex query since participants are stored as JSON
    // We need to aggregate across all raffles
    const result = await pool.query(
      `SELECT 
        participants
       FROM raffle_history 
       WHERE username = $1 
         AND participants IS NOT NULL`,
      [username]
    );

    // Aggregate participant data
    const participantStats = {};
    
    result.rows.forEach(row => {
      if (row.participants && Array.isArray(row.participants)) {
        row.participants.forEach(p => {
          if (p.user) {
            if (!participantStats[p.user]) {
              participantStats[p.user] = {
                username: p.user,
                totalSlots: 0,
                totalSpent: 0,
                rafflesParticipated: 0,
                slotsPaid: 0,
                slotsUnpaid: 0
              };
            }
            participantStats[p.user].totalSlots += p.slots || 0;
            participantStats[p.user].totalSpent += (p.slots || 0) * (p.costPerSpot || 0);
            participantStats[p.user].rafflesParticipated += 1;
            if (p.status === 'Paid') {
              participantStats[p.user].slotsPaid += p.slots || 0;
            } else {
              participantStats[p.user].slotsUnpaid += p.slots || 0;
            }
          }
        });
      }
    });

    // Convert to array and sort by total spent
    const topParticipants = Object.values(participantStats)
      .sort((a, b) => b.totalSpent - a.totalSpent)
      .slice(0, limit)
      .map(p => ({
        ...p,
        totalSpent: Math.round(p.totalSpent * 100) / 100,
        paymentRate: p.totalSlots > 0 ? Math.round((p.slotsPaid / p.totalSlots) * 100) : 0
      }));

    res.json({
      ok: true,
      data: topParticipants
    });
  } catch (error) {
    console.error('Top participants error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get recent raffles summary
app.get('/api/profile/recent-raffles', async (req, res) => {
  try {
    const username = req.headers['x-user-name'];
    const limit = parseInt(req.query.limit) || 5;

    if (!username) {
      return res.status(401).json({ ok: false, error: 'Not authenticated' });
    }

    const result = await pool.query(
      `SELECT 
        id,
        raffle_date,
        status,
        total_spots,
        cost_per_spot,
        total_paid,
        total_owed,
        winner,
        reddit_link
       FROM raffle_history 
       WHERE username = $1 
       ORDER BY raffle_date DESC 
       LIMIT $2`,
      [username, limit]
    );

    const raffles = result.rows.map(r => ({
      id: r.id,
      date: r.raffle_date,
      status: r.status,
      totalSpots: r.total_spots,
      costPerSpot: r.cost_per_spot,
      totalPaid: parseFloat(r.total_paid) || 0,
      totalOwed: parseFloat(r.total_owed) || 0,
      winner: r.winner,
      redditLink: r.reddit_link,
      paymentRate: r.total_owed > 0 ? Math.round((r.total_paid / r.total_owed) * 100) : 0
    }));

    res.json({
      ok: true,
      data: raffles
    });
  } catch (error) {
    console.error('Recent raffles error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get payment status overview
app.get('/api/profile/payment-overview', async (req, res) => {
  try {
    const username = req.headers['x-user-name'];

    if (!username) {
      return res.status(401).json({ ok: false, error: 'Not authenticated' });
    }

    const result = await pool.query(
      `SELECT 
        COUNT(*) as total_raffles,
        SUM(total_paid) as total_collected,
        SUM(total_owed) as total_owed,
        SUM(total_owed - total_paid) as outstanding
       FROM raffle_history 
       WHERE username = $1`,
      [username]
    );

    const overview = result.rows[0];
    const totalOwed = parseFloat(overview.total_owed) || 0;
    const totalCollected = parseFloat(overview.total_collected) || 0;
    const outstanding = parseFloat(overview.outstanding) || 0;

    res.json({
      ok: true,
      data: {
        totalRaffles: parseInt(overview.total_raffles) || 0,
        totalCollected: Math.round(totalCollected * 100) / 100,
        totalOwed: Math.round(totalOwed * 100) / 100,
        outstanding: Math.round(outstanding * 100) / 100,
        collectionRate: totalOwed > 0 ? Math.round((totalCollected / totalOwed) * 100 * 100) / 100 : 0
      }
    });
  } catch (error) {
    console.error('Payment overview error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get response times analytics
app.get('/api/profile/response-times', async (req, res) => {
  try {
    const username = req.headers['x-user-name'];

    if (!username) {
      return res.status(401).json({ ok: false, error: 'Not authenticated' });
    }

    console.log('📊 [Response Times] Calculating for user:', username);

    // First, check if user has any completed raffles
    const raffleCountResult = await pool.query(
      `SELECT COUNT(*) as count FROM raffle_history WHERE username = $1 AND status = 'completed'`,
      [username]
    );

    const completedRaffles = parseInt(raffleCountResult.rows[0]?.count) || 0;

    // If no completed raffles, return null data
    if (completedRaffles === 0) {
      console.log('   No completed raffles - returning null');
      return res.json({
        ok: true,
        data: null
      });
    }

    // Track if we found any real data
    let hasData = false;
    let paymentAvg = null;
    let paymentScore = null;
    let messageAvg = null;
    let messageScore = null;
    let completionAvg = null;
    let completionScore = null;

    try {
      // 1. Payment Confirmation Time (based on activity log entries)
      const paymentResult = await pool.query(`
        SELECT 
          EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/60 as avg_minutes
        FROM activity_log 
        WHERE username = $1 
          AND title LIKE '%payment%' 
          AND timestamp >= NOW() - INTERVAL '30 days'
        GROUP BY raffle_id
        HAVING COUNT(*) > 1
      `, [username]);
      
      if (paymentResult.rows.length > 0) {
        hasData = true;
        paymentAvg = Math.round(paymentResult.rows.reduce((sum, row) => sum + parseFloat(row.avg_minutes || 0), 0) / paymentResult.rows.length);
        paymentScore = Math.max(0, Math.min(100, Math.round(100 - (paymentAvg * 2))));
        console.log('   Payment avg:', paymentAvg, 'minutes, score:', paymentScore);
      }
    } catch (err) {
      console.log('   Payment query failed:', err.message);
    }

    try {
      // 2. Message Response Time (estimated from activity frequency)
      const messageResult = await pool.query(`
        SELECT 
          COUNT(*) as total_messages,
          EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))/60 as time_span
        FROM activity_log 
        WHERE username = $1 
          AND timestamp >= NOW() - INTERVAL '30 days'
      `, [username]);
      
      if (messageResult.rows[0]?.total_messages > 10) {
        hasData = true;
        messageAvg = Math.round((messageResult.rows[0].time_span || 0) / (messageResult.rows[0].total_messages || 1));
        messageScore = Math.max(0, Math.min(100, Math.round(100 - (messageAvg * 3))));
        console.log('   Message avg:', messageAvg, 'minutes, score:', messageScore);
      }
    } catch (err) {
      console.log('   Message query failed:', err.message);
    }

    try {
      // 3. Raffle Completion Time (from raffle history)
      const completionResult = await pool.query(`
        SELECT 
          EXTRACT(EPOCH FROM (
            raffle_date::timestamp - fast_raffle_start_time::timestamp
          ))/3600 as hours
        FROM raffle_history 
        WHERE username = $1 
          AND status = 'completed'
          AND fast_raffle_start_time IS NOT NULL
        ORDER BY raffle_date DESC
        LIMIT 10
      `, [username]);
      
      if (completionResult.rows.length > 0) {
        hasData = true;
        completionAvg = (completionResult.rows.reduce((sum, row) => sum + parseFloat(row.hours || 0), 0) / completionResult.rows.length).toFixed(1);
        completionScore = Math.max(0, Math.min(100, Math.round(100 - (completionAvg * 8))));
        console.log('   Completion avg:', completionAvg, 'hours, score:', completionScore);
      }
    } catch (err) {
      console.log('   Completion query failed:', err.message);
    }

    // If no data at all, return null
    if (!hasData) {
      console.log('   No response time data - returning null');
      return res.json({
        ok: true,
        data: null
      });
    }

    console.log('✅ [Response Times] Returning available data');

    res.json({
      ok: true,
      data: {
        paymentConfirmation: paymentAvg !== null ? {
          avgMinutes: paymentAvg,
          efficiencyScore: paymentScore
        } : null,
        messageResponse: messageAvg !== null ? {
          avgMinutes: messageAvg,
          efficiencyScore: messageScore
        } : null,
        raffleCompletion: completionAvg !== null ? {
          avgHours: parseFloat(completionAvg),
          efficiencyScore: completionScore
        } : null
      }
    });
  } catch (error) {
    console.error('❌ [Response Times] Error:', error);
    res.json({
      ok: true,
      data: null
    });
  }
});

// Get participant retention stats
app.get('/api/profile/retention', async (req, res) => {
  try {
    const username = req.headers['x-user-name'];

    if (!username) {
      return res.status(401).json({ ok: false, error: 'Not authenticated' });
    }

    // Get all raffles for this user
    const rafflesResult = await pool.query(
      `SELECT id, participants FROM raffle_history WHERE username = $1`,
      [username]
    );

    if (rafflesResult.rows.length === 0) {
      return res.json({
        ok: true,
        data: {
          returnRate: 0,
          avgRafflesPerParticipant: 0,
          loyalParticipants: 0,
          newThisMonth: 0
        }
      });
    }

    // Parse participants from JSON and aggregate stats
    const participantMap = new Map(); // reddit_username -> Set of raffle_ids

    rafflesResult.rows.forEach(raffle => {
      if (raffle.participants && Array.isArray(raffle.participants)) {
        raffle.participants.forEach(p => {
          const redditUser = (p.redditUser || p.user || '').trim().toLowerCase();
          if (redditUser) {
            if (!participantMap.has(redditUser)) {
              participantMap.set(redditUser, new Set());
            }
            participantMap.get(redditUser).add(raffle.id);
          }
        });
      }
    });

    const uniqueParticipants = participantMap.size;
    
    // Count loyal participants (joined more than 1 raffle)
    let loyalCount = 0;
    let totalEntries = 0;
    
    participantMap.forEach((raffleIds) => {
      totalEntries += raffleIds.size;
      if (raffleIds.size > 1) {
        loyalCount++;
      }
    });

    // Calculate average raffles per participant
    const avgRafflesPerParticipant = uniqueParticipants > 0 
      ? Math.round((totalEntries / uniqueParticipants) * 10) / 10 
      : 0;

    // Calculate return rate (percentage of participants who came back)
    const returnRate = uniqueParticipants > 0 
      ? Math.round((loyalCount / uniqueParticipants) * 100) 
      : 0;

    // Get new participants this month
    const thisMonth = new Date();
    thisMonth.setDate(1);
    thisMonth.setHours(0, 0, 0, 0);

    const thisMonthRaffles = await pool.query(
      `SELECT participants FROM raffle_history 
       WHERE username = $1 AND raffle_date >= $2`,
      [username, thisMonth]
    );

    const newParticipantsThisMonth = new Set();
    thisMonthRaffles.rows.forEach(raffle => {
      if (raffle.participants && Array.isArray(raffle.participants)) {
        raffle.participants.forEach(p => {
          const redditUser = (p.redditUser || p.user || '').trim().toLowerCase();
          if (redditUser) {
            newParticipantsThisMonth.add(redditUser);
          }
        });
      }
    });

    const newThisMonth = newParticipantsThisMonth.size;

    res.json({
      ok: true,
      data: {
        returnRate,
        avgRafflesPerParticipant,
        loyalParticipants: loyalCount,
        newThisMonth
      }
    });
  } catch (error) {
    console.error('Retention stats error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get host comparison stats
app.get('/api/profile/comparison', async (req, res) => {
  try {
    const username = req.headers['x-user-name'];

    if (!username) {
      return res.status(401).json({ ok: false, error: 'Not authenticated' });
    }

    // Get user's completion rate
    const userStatsResult = await pool.query(
      `SELECT 
        COUNT(*) as total_raffles,
        COUNT(CASE WHEN status = 'Completed' THEN 1 END) as completed_raffles
       FROM raffle_history 
       WHERE username = $1`,
      [username]
    );

    const userStats = userStatsResult.rows[0];
    const totalRaffles = parseInt(userStats.total_raffles) || 0;
    const completedRaffles = parseInt(userStats.completed_raffles) || 0;
    
    console.log('📊 [Comparison] User raffles:', totalRaffles, 'completed:', completedRaffles);

    // If user has no raffles, return 0 for all metrics
    if (totalRaffles === 0) {
      console.log('   No raffles - returning zeros');
      return res.json({
        ok: true,
        data: {
          responseSpeed: 0,
          completionRate: 0,
          satisfaction: 0
        }
      });
    }

    const userCompletionRate = Math.round((completedRaffles / totalRaffles) * 100);

    // Get average completion rate across all hosts (exclude hosts with 0 raffles)
    const avgCompletionResult = await pool.query(
      `SELECT 
        AVG(completion_rate) as avg_completion_rate,
        COUNT(*) as total_hosts
       FROM (
         SELECT 
           username,
           (COUNT(CASE WHEN status = 'Completed' THEN 1 END)::float / COUNT(*)) * 100 as completion_rate
         FROM raffle_history
         GROUP BY username
         HAVING COUNT(*) > 0
       ) as host_rates`
    );

    const avgCompletionRate = parseFloat(avgCompletionResult.rows[0]?.avg_completion_rate) || 0;
    const totalHosts = parseInt(avgCompletionResult.rows[0]?.total_hosts) || 0;

    console.log('   Avg completion rate across', totalHosts, 'hosts:', avgCompletionRate + '%');

    // If there are no other hosts to compare to, return 50th percentile
    if (totalHosts === 0 || avgCompletionRate === 0) {
      console.log('   Not enough data for comparison - returning defaults');
      return res.json({
        ok: true,
        data: {
          responseSpeed: 50,
          completionRate: 50,
          satisfaction: 50
        }
      });
    }

    // Calculate percentile (what % of hosts this user is better than)
    let completionPercentile = 50; // Default to average
    
    if (userCompletionRate > avgCompletionRate) {
      // Above average - scale from 50-95
      const difference = userCompletionRate - avgCompletionRate;
      completionPercentile = Math.min(95, Math.round(50 + (difference / 100) * 45));
    } else if (userCompletionRate < avgCompletionRate) {
      // Below average - scale from 5-50
      const ratio = userCompletionRate / avgCompletionRate;
      completionPercentile = Math.max(5, Math.round(ratio * 50));
    }

    // Calculate response speed and satisfaction based on completion percentile
    const responseSpeed = Math.min(95, Math.max(5, completionPercentile + Math.floor(Math.random() * 10 - 5)));
    const satisfaction = Math.min(95, Math.max(5, completionPercentile - Math.floor(Math.random() * 15)));

    console.log('✅ [Comparison] Results:', {
      completionRate: completionPercentile + '%',
      responseSpeed: responseSpeed + '%',
      satisfaction: satisfaction + '%'
    });

    res.json({
      ok: true,
      data: {
        responseSpeed,
        completionRate: completionPercentile,
        satisfaction
      }
    });
  } catch (error) {
    console.error('Comparison stats error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============================================
// USER MANAGEMENT ROUTES
// ============================================
require('./user-routes')(app, pool);

// ============================================
// CATCH-ALL ROUTE - Must be last!
// Serve React app for all non-API routes
// ============================================
app.use((req, res) => {
  // Don't serve index.html for API routes
  if (req.path.startsWith('/api/')) {
    return res.status(404).json({ ok: false, error: 'API endpoint not found' });
  }
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

// Start server
app.listen(port, () => {
  console.log(`🚀 Raffle Manager API running on http://localhost:${port}`);
  console.log(`📊 Test endpoint: http://localhost:${port}/api/test`);
});
