const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');
const path = require('path');
const { spawn } = require('child_process');
require('dotenv').config();
const session = require('express-session');

const app = express();
const port = process.env.PORT || 3001;

// PostgreSQL connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

// Initialize database tables
async function initializeDatabase() {
  try {
    // Ensure settings table exists
    await pool.query(`
      CREATE TABLE IF NOT EXISTS settings (
        key VARCHAR(255) PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT NOW()
      )
    `);
    console.log('✅ Database initialized: settings table ready');
  } catch (error) {
    console.error('❌ Error initializing database:', error);
  }
}

// Call initialization on startup
initializeDatabase();

app.use(cors());
app.use(express.json());

// Session middleware (must match FastAPI's session config)
app.use(session({
  secret: process.env.SESSION_SECRET || 'CHANGE_ME_SESSION_SECRET',
  resave: false,
  saveUninitialized: false,
  cookie: {
    httpOnly: true,
    secure: false, // Set to true if using HTTPS
    sameSite: 'lax',
    maxAge: 30 * 24 * 60 * 60 * 1000 // 30 days (matches FastAPI)
  }
}));

// Serve the React build files
app.use(express.static(path.join(__dirname, 'dist')));

// Serve sidebar admin control script
app.get('/sidebar-admin-control.js', (req, res) => {
  res.sendFile(path.join(__dirname, 'app/static/sidebar-admin-control.js'));
});

// Serve global scan indicator script
app.get('/global-scan-indicator.js', (req, res) => {
  res.sendFile(path.join(__dirname, 'app/static/global-scan-indicator.js'));
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

// ============ ACTIVE RAFFLE ENDPOINTS ============

// Save active raffle state
app.post('/api/raffle/save', async (req, res) => {
  try {
    console.log('🔵 POST /api/raffle/save - REQUEST RECEIVED');
    console.log('🔵 Body keys:', Object.keys(req.body));
    console.log('🔵 Participants count:', req.body.participants?.length);
    
    const { redditLink, totalSpots, costPerSpot, pollingInterval, participants, fastRaffleEnabled, fastRaffleStartTime } = req.body;

    // Get username and user_id from headers (set by FastAPI proxy)
    const username = req.headers['x-user-name'];
    const userId = req.headers['x-user-id'];

    // DEBUG: Log headers
    console.log('🔍 POST /api/raffle/save - Headers:');
    console.log('  X-User-Name:', username);
    console.log('  X-User-Id:', userId);

    if (!username || !userId) {
      console.error('❌ Missing authentication headers!');
      return res.status(401).json({ ok: false, error: 'User not authenticated' });
    }

    // Delete only THIS user's active raffle
    await pool.query('DELETE FROM active_raffle WHERE user_id = $1', [userId]);

    console.log('🗑️  Deleted any existing raffle for user_id:', userId);

    const result = await pool.query(
      `INSERT INTO active_raffle (reddit_link, total_spots, cost_per_spot, polling_interval, participants, fast_raffle_enabled, fast_raffle_start_time, username, user_id, updated_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
       RETURNING *`,
      [redditLink, totalSpots, costPerSpot, pollingInterval, JSON.stringify(participants), fastRaffleEnabled || false, fastRaffleStartTime, username, userId]
    );

    console.log('✅ Raffle saved with user_id:', userId, '- New raffle ID:', result.rows[0].id);

    // DEBUG: Check what's in the database now
    const checkResult = await pool.query('SELECT id, username, user_id FROM active_raffle');
    console.log('📊 All active raffles in DB:', checkResult.rows);

    const raffle = result.rows[0];

    // ✅ FIX: Map database columns to camelCase (same as /load endpoint)
    res.json({
      ok: true,
      data: {
        id: raffle.id,  // ← This is the critical raffle ID!
        redditLink: raffle.reddit_link,
        totalSpots: raffle.total_spots,
        costPerSpot: raffle.cost_per_spot,
        pollingInterval: raffle.polling_interval,
        participants: raffle.participants || [],
        fastRaffleEnabled: raffle.fast_raffle_enabled,
        fastRaffleStartTime: raffle.fast_raffle_start_time
      }
    });
  } catch (error) {
    console.error('Error saving raffle:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Load active raffle state
app.get('/api/raffle/load', async (req, res) => {
  try {
    // Get user_id from headers (set by FastAPI proxy)
    const userId = req.headers['x-user-id'];
    const username = req.headers['x-user-name'];

    // DEBUG: Log headers
    console.log('🔍 GET /api/raffle/load - Headers:');
    console.log('  X-User-Name:', username);
    console.log('  X-User-Id:', userId);

    if (!userId) {
      console.error('❌ Missing user_id header!');
      return res.status(401).json({ ok: false, error: 'User not authenticated' });
    }

    // Get only THIS user's active raffle (filter by user_id)
    const result = await pool.query(
      'SELECT * FROM active_raffle WHERE user_id = $1 ORDER BY id DESC LIMIT 1',
      [userId]
    );

    console.log('✅ Found', result.rows.length, 'raffle(s) for user_id:', userId);

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
        fastRaffleEnabled: raffle.fast_raffle_enabled,
        fastRaffleStartTime: raffle.fast_raffle_start_time
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
    // Get user_id from headers (set by FastAPI proxy)
    const userId = req.headers['x-user-id'];

    if (!userId) {
      return res.status(401).json({ ok: false, error: 'User not authenticated' });
    }

    // Delete only THIS user's active raffle
    await pool.query('DELETE FROM active_raffle WHERE user_id = $1', [userId]);
    res.json({ ok: true });
  } catch (error) {
    console.error('Error clearing raffle:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ✅ NEW: Admin delete any raffle by ID (for fixing bugged raffles)
app.delete('/api/admin/raffle/:id', async (req, res) => {
  try {
    const raffleId = req.params.id;
    const isAdmin = req.headers['x-user-is-admin'] === 'true';

    if (!isAdmin) {
      return res.status(403).json({ ok: false, error: 'Admin access required' });
    }

    console.log('🗑️  Admin deleting raffle ID:', raffleId);
    
    const result = await pool.query('DELETE FROM active_raffle WHERE id = $1 RETURNING *', [raffleId]);
    
    if (result.rows.length === 0) {
      return res.status(404).json({ ok: false, error: 'Raffle not found' });
    }

    console.log('✅ Successfully deleted raffle ID:', raffleId);
    res.json({ ok: true, message: 'Raffle deleted successfully' });
  } catch (error) {
    console.error('Error deleting raffle:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get ALL active raffles (Admin only - for Live Raffle Monitor)
app.get('/api/raffles/active', async (req, res) => {
  try {
    // Get all active raffles with their current state (NO CACHING)
    // ✅ FIX: JOIN with users table to get the correct username
    const result = await pool.query(`
      SELECT 
        ar.*,
        u.username as actual_username
      FROM active_raffle ar
      LEFT JOIN users u ON ar.user_id = u.id
      ORDER BY ar.updated_at DESC
    `);

    console.log('📊 Fetched', result.rows.length, 'active raffle(s)');

    // Helper function to convert title to Title Case
    function toTitleCase(str) {
      return str.replace(/\w\S*/g, function(txt) {
        return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
      });
    }

    // Transform the data for the frontend
    const raffles = result.rows.map(raffle => {
      // Parse participants - handle both JSON string and array
      let participants = [];
      try {
        if (Array.isArray(raffle.participants)) {
          participants = raffle.participants;
        } else if (typeof raffle.participants === 'string') {
          participants = JSON.parse(raffle.participants);
        } else if (raffle.participants && typeof raffle.participants === 'object') {
          participants = raffle.participants;
        }
      } catch (e) {
        console.error('Error parsing participants:', e);
        participants = [];
      }

      // DEBUG: Log first participant to see structure
      if (participants.length > 0) {
        console.log('  📋 Sample participant:', JSON.stringify(participants[0]));
      }

      // Calculate filled spots by summing up ALL spots from all participants
      // Support BOTH old format (spotsRequested) and new format (spots)
      const filledSpots = participants.reduce((sum, p) => {
        const spotCount = p.spots || p.spotsRequested || 0;
        return sum + spotCount;
      }, 0);
      const remainingSpots = raffle.total_spots - filledSpots;
      const progress = raffle.total_spots > 0 ? Math.round((filledSpots / raffle.total_spots) * 100) : 0;

      console.log(`  Raffle ${raffle.id}: ${filledSpots}/${raffle.total_spots} spots filled (${participants.length} participants)`);

      // Parse title from reddit_link - improved parsing
      let raffleTitle = raffle.reddit_link || 'Unknown Raffle';
      let itemName = 'Unknown Item';
      let isFast = false;

      if (raffle.reddit_link) {
        // Try to extract title from Reddit URL
        // Format: https://reddit.com/r/PokemonRaffles/comments/ID/title_slug/
        // or just the path: /r/pokemonraffles/comments/.../nm_fast_charizard_vmax_rainbow_rare_psa_10_37/
        
        let titleSlug = '';
        
        // Extract the title slug from URL
        const urlParts = raffle.reddit_link.split('/');
        // Find the part after 'comments' and skip the ID
        const commentsIndex = urlParts.findIndex(part => part === 'comments');
        if (commentsIndex >= 0 && urlParts.length > commentsIndex + 2) {
          titleSlug = urlParts[commentsIndex + 2];
        }
        
        if (titleSlug) {
          // Convert slug to readable title (replace underscores/dashes with spaces)
          raffleTitle = titleSlug
            .replace(/_/g, ' ')
            .replace(/-/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
          
          // Apply Title Case
          raffleTitle = toTitleCase(raffleTitle);
          
          // ✅ FIX: Force condition codes to UPPERCASE with brackets
          raffleTitle = raffleTitle.replace(/\b(nm|bnib|nib|lnib|mint|used)\b/gi, (match) => {
            return '[' + match.toUpperCase() + ']';
          });
          
          // Detect FAST raffle
          isFast = /\bfast\b/i.test(raffleTitle);
          
          // ✅ FIX: Extract FULL item name (don't truncate, just remove spot count)
          let cleanedTitle = raffleTitle;
          
          // Remove the spot count portion (e.g., "37 spots at $10ea" or "- X spots @ $Y/ea")
          cleanedTitle = cleanedTitle.replace(/\s*-?\s*\d+\s*spots?\s*(at|@).*$/i, '');
          
          // Also remove trailing numbers (like "37" at the end)
          cleanedTitle = cleanedTitle.replace(/\s+\d+$/, '');
          
          // Remove FAST keyword (it's shown as a badge instead)
          cleanedTitle = cleanedTitle.replace(/\s*-?\s*Fast\s*/gi, '');
          
          itemName = cleanedTitle.trim() || 'Unknown Item';
        }
      }

      // Determine status based on progress
      let status = 'starting';
      if (progress >= 90) {
        status = 'almost-full';
      } else if (progress >= 30) {
        status = 'filling';
      }

      return {
        id: raffle.id,
        title: raffleTitle,
        itemName: itemName,
        host: raffle.actual_username || raffle.username || 'Unknown User',  // ✅ Use actual_username from JOIN
        totalSpots: parseInt(raffle.total_spots) || 0,
        filledSpots: filledSpots,
        remainingSpots: remainingSpots,
        costPerSpot: parseFloat(raffle.cost_per_spot) || 0,
        progress: progress,
        status: status,
        isFast: isFast || raffle.fast_raffle_enabled,
        redditLink: raffle.reddit_link,
        updatedAt: raffle.updated_at,
        participants: participants
      };
    });

    res.json({
      ok: true,
      raffles: raffles,
      totalActive: raffles.length
    });
  } catch (error) {
    console.error('Error fetching active raffles:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============ ADMIN: GET ALL RAFFLES (ACTIVE + HISTORY) ============
app.get('/api/admin/all-raffles', async (req, res) => {
  try {
    const isAdmin = req.headers['x-user-is-admin'] === 'true';

    if (!isAdmin) {
      return res.status(403).json({ ok: false, error: 'Admin access required' });
    }

    // Fetch all active raffles
    const activeResult = await pool.query(`
      SELECT 
        ar.id,
        ar.user_id,
        ar.reddit_link,
        ar.total_spots,
        ar.cost_per_spot,
        ar.participants,
        ar.created_at,
        ar.updated_at,
        u.username,
        'Active' as status
      FROM active_raffle ar
      LEFT JOIN users u ON ar.user_id = u.id
      ORDER BY ar.created_at DESC
    `);

    // Fetch all raffle history
    const historyResult = await pool.query(`
      SELECT 
        id,
        NULL as user_id,
        reddit_link,
        total_spots,
        cost_per_spot,
        participants,
        raffle_date as created_at,
        raffle_date as updated_at,
        username,
        status
      FROM raffle_history
      ORDER BY raffle_date DESC
    `);

    // Combine and format the results
    const allRaffles = [];

    // Process active raffles
    activeResult.rows.forEach(raffle => {
      let participants = [];
      try {
        if (Array.isArray(raffle.participants)) {
          participants = raffle.participants;
        } else if (typeof raffle.participants === 'string') {
          participants = JSON.parse(raffle.participants);
        } else if (raffle.participants && typeof raffle.participants === 'object') {
          participants = raffle.participants;
        }
      } catch (e) {
        participants = [];
      }

      const filledSpots = participants.reduce((sum, p) => sum + (p.spots || 0), 0);
      const totalRevenue = filledSpots * parseFloat(raffle.cost_per_spot || 0);

      allRaffles.push({
        id: raffle.id,
        type: 'active',
        username: raffle.username || 'Unknown',
        redditLink: raffle.reddit_link || '',
        status: 'Active',
        date: raffle.created_at,
        totalSpots: parseInt(raffle.total_spots) || 0,
        filledSpots: filledSpots,
        costPerSpot: parseFloat(raffle.cost_per_spot) || 0,
        totalRevenue: totalRevenue.toFixed(2),
        participants: participants
      });
    });

    // Process history raffles
    historyResult.rows.forEach(raffle => {
      let participants = [];
      try {
        if (Array.isArray(raffle.participants)) {
          participants = raffle.participants;
        } else if (typeof raffle.participants === 'string') {
          participants = JSON.parse(raffle.participants);
        } else if (raffle.participants && typeof raffle.participants === 'object') {
          participants = raffle.participants;
        }
      } catch (e) {
        participants = [];
      }

      const filledSpots = participants.reduce((sum, p) => sum + (p.spots || 0), 0);
      const totalRevenue = filledSpots * parseFloat(raffle.cost_per_spot || 0);

      allRaffles.push({
        id: raffle.id,
        type: 'history',
        username: raffle.username || 'Unknown',
        redditLink: raffle.reddit_link || '',
        status: raffle.status || 'Unknown',
        date: raffle.created_at,
        totalSpots: parseInt(raffle.total_spots) || 0,
        filledSpots: filledSpots,
        costPerSpot: parseFloat(raffle.cost_per_spot) || 0,
        totalRevenue: totalRevenue.toFixed(2),
        participants: participants
      });
    });

    // Sort by date (most recent first)
    allRaffles.sort((a, b) => new Date(b.date) - new Date(a.date));

    // Calculate stats with defensive null checks
    const totalCompleted = allRaffles.filter(r => r.status && r.status.toLowerCase() === 'completed').length;
    const totalCancelled = allRaffles.filter(r => r.status && r.status.toLowerCase() === 'cancelled').length;

    console.log('📊 Admin fetched', allRaffles.length, 'total raffles (' + activeResult.rows.length + ' active, ' + historyResult.rows.length + ' history)');

    res.json({
      ok: true,
      raffles: allRaffles,
      stats: {
        totalActive: activeResult.rows.length,
        totalHistory: historyResult.rows.length,
        total: allRaffles.length,
        totalCompleted: totalCompleted,
        totalCancelled: totalCancelled
      }
    });
  } catch (error) {
    console.error('Error fetching all raffles:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============ ADMIN: DELETE ANY RAFFLE (ACTIVE OR HISTORY) ============
app.delete('/api/admin/delete-raffle', async (req, res) => {
  try {
    const isAdmin = req.headers['x-user-is-admin'] === 'true';

    if (!isAdmin) {
      return res.status(403).json({ ok: false, error: 'Admin access required' });
    }

    const { id, type } = req.body;

    if (!id || !type) {
      return res.status(400).json({ ok: false, error: 'ID and type are required' });
    }

    console.log('🗑️  Admin deleting raffle - ID:', id, 'Type:', type);

    let result;
    if (type === 'active') {
      result = await pool.query('DELETE FROM active_raffle WHERE id = $1 RETURNING *', [id]);
    } else if (type === 'history') {
      result = await pool.query('DELETE FROM raffle_history WHERE id = $1 RETURNING *', [id]);
    } else {
      return res.status(400).json({ ok: false, error: 'Invalid type. Must be "active" or "history"' });
    }

    if (result.rows.length === 0) {
      return res.status(404).json({ ok: false, error: 'Raffle not found' });
    }

    console.log('✅ Successfully deleted raffle ID:', id, 'from', type);
    res.json({ ok: true, message: 'Raffle deleted successfully' });
  } catch (error) {
    console.error('Error deleting raffle:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============ ADMIN: FINISH ACTIVE RAFFLE (MOVE TO COMPLETED) ============
app.post('/api/admin/finish-raffle', async (req, res) => {
  try {
    const isAdmin = req.headers['x-user-is-admin'] === 'true';

    if (!isAdmin) {
      return res.status(403).json({ ok: false, error: 'Admin access required' });
    }

    const { id, type, winner } = req.body;

    if (!id || !type) {
      return res.status(400).json({ ok: false, error: 'ID and type are required' });
    }

    // Only allow finishing active raffles
    if (type !== 'active') {
      return res.status(400).json({ ok: false, error: 'Can only finish active raffles' });
    }

    console.log('✅ Admin finishing active raffle - ID:', id);
    if (winner) {
      console.log('   Winner:', winner.username, '(' + winner.spots + ' spots)');
    }

    // Get the active raffle data with username from users table
    const raffleResult = await pool.query(
      `SELECT ar.*, u.username 
       FROM active_raffle ar
       LEFT JOIN users u ON ar.user_id = u.id
       WHERE ar.id = $1`, 
      [id]
    );

    if (raffleResult.rows.length === 0) {
      return res.status(404).json({ ok: false, error: 'Active raffle not found' });
    }

    const raffle = raffleResult.rows[0];

    // Format winner data for storage
    const winnerData = winner ? {
      username: winner.username,
      spots: winner.spots
    } : null;

    // Ensure participants is properly stringified (it might already be a JSON object from DB)
    let participantsJson;
    if (typeof raffle.participants === 'string') {
      participantsJson = raffle.participants;
    } else if (raffle.participants) {
      participantsJson = JSON.stringify(raffle.participants);
    } else {
      participantsJson = '[]';
    }

    // Move to raffle_history as "completed"
    await pool.query(
      `INSERT INTO raffle_history
       (raffle_date, status, reddit_link, total_spots, cost_per_spot, participants, total_owed, total_paid, winner, username)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
      [
        raffle.raffle_date || new Date(),
        'completed',
        raffle.reddit_link,
        raffle.total_spots,
        raffle.cost_per_spot,
        participantsJson,
        raffle.total_owed || 0,
        raffle.total_paid || 0,
        winnerData ? JSON.stringify(winnerData) : null,
        raffle.username
      ]
    );

    // Delete from active_raffle
    await pool.query('DELETE FROM active_raffle WHERE id = $1', [id]);

    console.log('✅ Successfully finished raffle ID:', id, '- moved to completed in history');
    res.json({ ok: true, message: 'Raffle finished successfully and moved to completed' });
  } catch (error) {
    console.error('Error finishing raffle:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============ ADMIN: CANCEL ACTIVE RAFFLE (MOVE TO CANCELLED) ============
app.post('/api/admin/cancel-raffle', async (req, res) => {
  try {
    const isAdmin = req.headers['x-user-is-admin'] === 'true';

    if (!isAdmin) {
      return res.status(403).json({ ok: false, error: 'Admin access required' });
    }

    const { id, type } = req.body;

    if (!id || !type) {
      return res.status(400).json({ ok: false, error: 'ID and type are required' });
    }

    // Only allow cancelling active raffles
    if (type !== 'active') {
      return res.status(400).json({ ok: false, error: 'Can only cancel active raffles' });
    }

    console.log('⚠️ Admin cancelling active raffle - ID:', id);

    // Get the active raffle data with username from users table
    const raffleResult = await pool.query(
      `SELECT ar.*, u.username 
       FROM active_raffle ar
       LEFT JOIN users u ON ar.user_id = u.id
       WHERE ar.id = $1`, 
      [id]
    );

    if (raffleResult.rows.length === 0) {
      return res.status(404).json({ ok: false, error: 'Active raffle not found' });
    }

    const raffle = raffleResult.rows[0];

    // Ensure participants is properly stringified
    let participantsJson;
    if (typeof raffle.participants === 'string') {
      participantsJson = raffle.participants;
    } else if (raffle.participants) {
      participantsJson = JSON.stringify(raffle.participants);
    } else {
      participantsJson = '[]';
    }

    // Move to raffle_history as "cancelled"
    await pool.query(
      `INSERT INTO raffle_history
       (raffle_date, status, reddit_link, total_spots, cost_per_spot, participants, total_owed, total_paid, winner, username)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
      [
        raffle.raffle_date || new Date(),
        'cancelled',
        raffle.reddit_link,
        raffle.total_spots,
        raffle.cost_per_spot,
        participantsJson,
        raffle.total_owed || 0,
        raffle.total_paid || 0,
        null, // No winner for cancelled raffles
        raffle.username
      ]
    );

    // Delete from active_raffle
    await pool.query('DELETE FROM active_raffle WHERE id = $1', [id]);

    console.log('✅ Successfully cancelled raffle ID:', id, '- moved to cancelled in history');
    res.json({ ok: true, message: 'Raffle cancelled successfully and moved to history' });
  } catch (error) {
    console.error('Error cancelling raffle:', error);
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
      username
    } = req.body;

    const result = await pool.query(
      `INSERT INTO raffle_history
       (raffle_date, status, reddit_link, total_spots, cost_per_spot, participants, total_owed, total_paid, winner, username)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
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
        username
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
    const result = await pool.query(
      'SELECT * FROM raffle_history ORDER BY raffle_date DESC'
    );

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
    // Get username from headers (set by FastAPI proxy)
    const username = req.headers['x-user-name'];

    // DEBUG: Log what we received
    console.log('🔍 GET /api/activity/list - Headers:');
    console.log('  X-User-Name:', username);
    console.log('  All headers:', JSON.stringify(req.headers, null, 2));

    if (!username) {
      console.warn('⚠️ No username header found, returning empty activity log');
      // Return empty array instead of 401 - this is more graceful
      return res.json({ ok: true, data: [] });
    }

    // ✅ FIX: Filter activities by username
    const result = await pool.query(
      'SELECT * FROM activity_log WHERE username = $1 ORDER BY timestamp DESC LIMIT 100',
      [username]
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

    console.log(`✅ Returning ${activities.length} activities for user: ${username}`);
    res.json({ ok: true, data: activities });
  } catch (error) {
    console.error('Error fetching activities:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Clear activity log
app.delete('/api/activity/clear', async (req, res) => {
  try {
    // Get username from headers (set by FastAPI proxy)
    const username = req.headers['x-user-name'];

    // DEBUG: Log what we received
    console.log('🔍 DELETE /api/activity/clear - Headers:');
    console.log('  X-User-Name:', username);

    if (!username) {
      console.warn('⚠️ No username header found, cannot clear activities');
      return res.status(401).json({ ok: false, error: 'User not authenticated' });
    }

    // ✅ FIX: Only clear THIS user's activities
    const result = await pool.query('DELETE FROM activity_log WHERE username = $1', [username]);
    console.log(`✅ Cleared ${result.rowCount} activities for user: ${username}`);
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
    
    console.log(`💾 Saving setting: key="${key}", value="${value}"`);

    await pool.query(
      `INSERT INTO settings (key, value, updated_at)
       VALUES ($1, $2, NOW())
       ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()`,
      [key, value]
    );
    
    // Verify the save by reading it back
    const verifyResult = await pool.query(
      'SELECT value FROM settings WHERE key = $1',
      [key]
    );
    
    console.log(`✅ Setting saved successfully`);
    console.log(`🔍 Verification: DB now contains value="${verifyResult.rows[0]?.value}"`);

    res.json({ ok: true });
  } catch (error) {
    console.error('Error saving setting:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get all name mappings (for Active Raffle display)
app.get('/api/settings/get-all-name-mappings', async (req, res) => {
  try {
    // Get username from headers (set by FastAPI proxy)
    const username = req.headers['x-user-name'];
    const userId = req.headers['x-user-id'];
    
    console.log('🔍 GET /api/settings/get-all-name-mappings - Headers:');
    console.log('  X-User-Name:', username);
    console.log('  X-User-Id:', userId);
    
    if (!username || !userId) {
      return res.status(401).json({ ok: false, error: 'Not authenticated' });
    }

    // Fetch all name mappings (using the current schema with first_initial and last_initial)
    const result = await pool.query(
      'SELECT reddit_username, first_initial, last_initial FROM shared_name_mappings'
    );

    // Convert to object format { "reddit_user": "F L" }
    const mappings = {};
    for (const row of result.rows) {
      mappings[row.reddit_username] = `${row.first_initial} ${row.last_initial}`;
    }

    console.log(`✅ Returning ${Object.keys(mappings).length} name mappings for user: ${username}`);
    res.json({ ok: true, mappings });
  } catch (error) {
    console.error('Error fetching name mappings:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Cleanup duplicate name mappings in database (case-insensitive)
app.post('/api/settings/cleanup-duplicate-mappings', async (req, res) => {
  try {
    const username = req.headers['x-user-name'];
    const userId = req.headers['x-user-id'];
    
    if (!username || !userId) {
      return res.status(401).json({ ok: false, error: 'Not authenticated' });
    }

    console.log('🧹 Cleaning up duplicate name mappings in database...');

    // Get all mappings from database
    const result = await pool.query(
      'SELECT id, reddit_username, first_initial, last_initial FROM shared_name_mappings ORDER BY id ASC'
    );

    const seenLowercase = {};
    const idsToDelete = [];

    for (const row of result.rows) {
      const lowerUsername = row.reddit_username.toLowerCase();

      if (!seenLowercase[lowerUsername]) {
        // First occurrence - keep it
        seenLowercase[lowerUsername] = row;
      } else {
        // Duplicate found
        const existingRow = seenLowercase[lowerUsername];
        
        // If current row is lowercase and existing is not, delete existing and keep current
        if (row.reddit_username === lowerUsername && existingRow.reddit_username !== lowerUsername) {
          idsToDelete.push(existingRow.id);
          seenLowercase[lowerUsername] = row;
        } else {
          // Otherwise delete current (keep first one)
          idsToDelete.push(row.id);
        }
      }
    }

    // Delete duplicates
    if (idsToDelete.length > 0) {
      await pool.query(
        'DELETE FROM shared_name_mappings WHERE id = ANY($1)',
        [idsToDelete]
      );
      console.log(`✅ Removed ${idsToDelete.length} duplicate database entries`);
    }

    res.json({ 
      ok: true, 
      duplicatesRemoved: idsToDelete.length,
      message: `Removed ${idsToDelete.length} duplicate(s)`
    });
  } catch (error) {
    console.error('Error cleaning up duplicate mappings:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get setting (generic - must be AFTER specific routes)
app.get('/api/settings/:key', async (req, res) => {
  try {
    console.log(`🔍 Getting setting: key="${req.params.key}"`);
    
    const result = await pool.query(
      'SELECT value FROM settings WHERE key = $1',
      [req.params.key]
    );

    if (result.rows.length === 0) {
      console.log(`⚠️  Setting not found: "${req.params.key}"`);
      return res.json({ ok: true, data: null });
    }

    const responsePayload = { ok: true, data: result.rows[0].value };
    console.log(`✅ Setting found: value="${result.rows[0].value}"`);
    console.log(`✅ Sending response:`, responsePayload);
    res.json(responsePayload);
  } catch (error) {
    console.error('Error fetching setting:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Debug endpoint: Get ALL settings
app.get('/api/settings-debug/all', async (req, res) => {
  try {
    const result = await pool.query('SELECT key, value, updated_at FROM settings ORDER BY key');
    res.json({ ok: true, settings: result.rows });
  } catch (error) {
    console.error('Error fetching all settings:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============ REDDIT SCANNING ENDPOINT ============

app.post('/api/reddit/scan', async (req, res) => {
  try {
    const { redditLink, costPerSpot, totalSpots, existingCommentIds, currentAssignedSpots } = req.body;

    if (!redditLink || !costPerSpot) {
      return res.status(400).json({
        ok: false,
        error: 'Missing redditLink or costPerSpot'
      });
    }

    // Path to Python script (AI-powered version)
    const pythonScript = path.join(__dirname, '..', 'app', 'reddit_parser.py');

    console.log('Starting Reddit scan:', redditLink, 'Cost:', costPerSpot);
    console.log(`📊 Total spots: ${totalSpots || 'unlimited'}`);
    console.log(`📊 Current assigned spots: ${currentAssignedSpots || 0}`);
    console.log(`📊 Existing comment IDs to skip: ${existingCommentIds?.length || 0}`);

    // Build arguments for Python script
    const args = [pythonScript, redditLink, costPerSpot.toString()];
    
    // Always add totalSpots to maintain consistent argument positions (use 'null' if not provided)
    args.push(totalSpots ? totalSpots.toString() : 'null');
    
    // Add existingCommentIds as JSON string if provided, otherwise empty array
    args.push(existingCommentIds && existingCommentIds.length > 0 ? JSON.stringify(existingCommentIds) : '[]');
    
    // Add currentAssignedSpots (use '0' if not provided)
    args.push(currentAssignedSpots !== undefined && currentAssignedSpots !== null ? currentAssignedSpots.toString() : '0');

    // Spawn Python process
    const python = spawn('python3', args, {
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

// ============ PARSER CORRECTION LEARNING ENDPOINT ============

// Record parser correction for automatic learning
app.post('/api/parser/record-correction', async (req, res) => {
  try {
    const { comment, wrongParse, correctParse } = req.body;

    // Validate input
    if (!comment || wrongParse === undefined || correctParse === undefined) {
      return res.status(400).json({
        ok: false,
        error: 'Missing required fields: comment, wrongParse, correctParse'
      });
    }

    // Check if historical learning is enabled
    try {
      const settingsResult = await pool.query(
        'SELECT value FROM settings WHERE key = $1',
        ['historical_learning_enabled']
      );
      const learningEnabled = settingsResult.rows.length > 0 
        ? settingsResult.rows[0].value === 'true' 
        : true; // Default to enabled if setting doesn't exist

      if (!learningEnabled) {
        console.log('⏸️  Historical learning is DISABLED - skipping correction recording');
        return res.json({
          ok: true,
          skipped: true,
          message: 'Historical learning is currently disabled'
        });
      }
    } catch (settingsError) {
      // If settings table doesn't exist, just continue (default to enabled)
      console.warn('Settings table not found, defaulting to learning enabled');
    }

    // Path to Python script with record_correction function
    const pythonScript = '/home/ubuntu/takobot-electron/app/record_parser_correction.py';

    console.log('📝 Recording parser correction:');
    console.log(`  Comment: "${comment}"`);
    console.log(`  Wrong: ${wrongParse} → Correct: ${correctParse}`);

    // Call Python script to record correction
    const python = spawn('python3', [pythonScript, comment, wrongParse.toString(), correctParse.toString()], {
      timeout: 10000 // 10 seconds
    });

    let stdout = '';
    let stderr = '';

    python.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    python.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    python.on('close', (code) => {
      if (code !== 0) {
        console.error('Failed to record correction:', stderr || stdout);
        return res.status(500).json({
          ok: false,
          error: 'Failed to record correction'
        });
      }

      console.log('✅ Correction recorded successfully');
      res.json({
        ok: true,
        message: 'Correction recorded - parser will learn from this!'
      });
    });

    python.on('error', (err) => {
      console.error('Python process error:', err);
      res.status(500).json({
        ok: false,
        error: `Process error: ${err.message}`
      });
    });

  } catch (error) {
    console.error('Record correction error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// System Status endpoint
app.get('/api/system/status', async (req, res) => {
  try {
    const fs = require('fs');
    const path = require('path');

    // Check Gmail OAuth credentials
    const credPath = path.join(__dirname, 'credentials.json');
    const gmailConnected = fs.existsSync(credPath);

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

    // ✅ Update last_login timestamp on successful login
    await pool.query(
      'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = $1',
      [user.id]
    );

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

    // Get ALL raffles (for overall completion rate)
    const allRafflesResult = await pool.query(
      `SELECT status FROM raffle_history`
    );
    const allRaffles = allRafflesResult.rows;
    const allCompleted = allRaffles.filter(r => r.status === 'completed').length;
    const allCancelled = allRaffles.filter(r => r.status === 'cancelled').length;
    const allTotal = allCompleted + allCancelled;
    const overallCompletionRate = allTotal > 0 ? Math.round((allCompleted / allTotal) * 100) : 0;

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
        uniqueUsers,
        overallCompletionRate
      }
    });

  } catch (error) {
    console.error('Admin analytics error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get user breakdown for a specific month
app.get('/api/admin/user-breakdown/:year/:month', async (req, res) => {
  try {
    // Check admin access from headers (passed by FastAPI proxy)
    const isAdmin = req.headers['x-user-admin'] === 'true';
    const username = req.headers['x-user-name'];

    if (!isAdmin) {
      return res.status(403).json({ ok: false, error: 'Access denied. Admin only.' });
    }

    const year = parseInt(req.params.year);
    const month = parseInt(req.params.month); // 1-12

    // Get all raffles for the specified month/year
    const raffleResult = await pool.query(
      `SELECT * FROM raffle_history
       WHERE EXTRACT(YEAR FROM raffle_date) = $1
       AND EXTRACT(MONTH FROM raffle_date) = $2
       ORDER BY raffle_date`,
      [year, month]
    );

    const raffles = raffleResult.rows;

    // Group raffles by username and calculate stats
    const userStats = {};

    raffles.forEach(raffle => {
      const user = raffle.username || 'Unknown';
      
      if (!userStats[user]) {
        userStats[user] = {
          username: user,
          completed: 0,
          cancelled: 0,
          total: 0,
          completionRate: 0
        };
      }

      if (raffle.status === 'completed') {
        userStats[user].completed++;
      } else if (raffle.status === 'cancelled') {
        userStats[user].cancelled++;
      }
      userStats[user].total++;
    });

    // Calculate completion rates and convert to array
    const userArray = Object.values(userStats).map(user => ({
      ...user,
      completionRate: user.total > 0 ? Math.round((user.completed / user.total) * 100) : 0
    }));

    // Sort by total raffles (descending)
    userArray.sort((a, b) => b.total - a.total);

    res.json({
      ok: true,
      data: userArray
    });

  } catch (error) {
    console.error('User breakdown error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============ PROFILE ENDPOINTS ============

// Get profile
app.get('/api/profile', async (req, res) => {
  try {
    // Get user info from headers (passed by FastAPI proxy)
    const username = req.headers['x-user-name'];

    if (!username) {
      return res.status(401).json({ ok: false, error: 'Not authenticated' });
    }

    const result = await pool.query(
      'SELECT id, username, email, fullname, is_admin, default_polling, timezone, bio, created_at FROM users WHERE username = $1',
      [username]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ ok: false, error: 'User not found' });
    }

    const user = result.rows[0];
    res.json({
      ok: true,
      data: {
        id: user.id,
        username: user.username,
        email: user.email,
        fullname: user.fullname,
        isAdmin: user.is_admin,
        defaultPolling: user.default_polling,
        timezone: user.timezone,
        bio: user.bio,
        createdAt: user.created_at
      }
    });
  } catch (error) {
    console.error('Profile fetch error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Update profile
app.put('/api/profile', async (req, res) => {
  try {
    const username = 'maki'; // TODO: Replace with session
    const { email, fullname, defaultPolling, timezone, bio } = req.body;

    const result = await pool.query(
      `UPDATE users
       SET email = $1, fullname = $2, default_polling = $3, timezone = $4, bio = $5, updated_at = NOW()
       WHERE username = $6
       RETURNING id, username, email, fullname, is_admin, default_polling, timezone, bio, created_at`,
      [email, fullname, defaultPolling, timezone, bio, username]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ ok: false, error: 'User not found' });
    }

    res.json({ ok: true, data: result.rows[0] });
  } catch (error) {
    console.error('Profile update error:', error);
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

    // Get raffle stats - FILTERED BY USERNAME
    const raffleResult = await pool.query(
      `SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
        SUM(CASE WHEN status = 'completed' THEN total_paid ELSE 0 END) as revenue
       FROM raffle_history
       WHERE username = $1`,
      [username]
    );

    const stats = raffleResult.rows[0];

    res.json({
      ok: true,
      data: {
        totalRaffles: parseInt(stats.total) || 0,
        completedRaffles: parseInt(stats.completed) || 0,
        totalRevenue: parseFloat(stats.revenue) || 0,
        joinDate: userResult.rows[0].created_at
      }
    });
  } catch (error) {
    console.error('Profile stats error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get profile response times
app.get('/api/profile/response-times', async (req, res) => {
  try {
    const username = req.headers['x-user-name'];

    if (!username) {
      return res.status(401).json({ ok: false, error: 'Not authenticated' });
    }

    // Get user's completed raffles (we don't track filled_at or completed_at timestamps yet)
    // For now, just return null for all metrics until we add timestamp tracking
    // TODO: Add created_at, filled_at, completed_at columns to raffle_history table
    
    const raffles = await pool.query(
      `SELECT raffle_date, status FROM raffle_history WHERE username = $1`,
      [username]
    );

    let paymentConfirmation = null;
    let raffleFillRate = null;
    let raffleCompletion = null;

    // TODO: Calculate these metrics when we have timestamp data
    // For now, return null to show "No data" in the UI

    res.json({
      ok: true,
      data: {
        paymentConfirmation,
        raffleFillRate,
        raffleCompletion
      }
    });
  } catch (error) {
    console.error('Profile response times error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get profile retention stats
app.get('/api/profile/retention', async (req, res) => {
  try {
    const username = req.headers['x-user-name'];

    if (!username) {
      return res.status(401).json({ ok: false, error: 'Not authenticated' });
    }

    // Get all completed raffles for this user
    const raffleResult = await pool.query(
      `SELECT participants FROM raffle_history 
       WHERE username = $1 AND status = 'completed'`,
      [username]
    );

    if (raffleResult.rows.length === 0) {
      // No data yet
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

    // Count participant appearances across all raffles
    const participantCounts = {};
    raffleResult.rows.forEach(raffle => {
      const participants = raffle.participants || [];
      participants.forEach(p => {
        const username = (p.redditUser || p.username || '').trim().toLowerCase();
        if (username) {
          participantCounts[username] = (participantCounts[username] || 0) + 1;
        }
      });
    });

    const totalParticipants = Object.keys(participantCounts).length;
    
    if (totalParticipants === 0) {
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

    // Calculate stats
    const returningParticipants = Object.values(participantCounts).filter(count => count > 1).length;
    const returnRate = Math.round((returningParticipants / totalParticipants) * 100);
    
    const totalRaffleParticipations = Object.values(participantCounts).reduce((sum, count) => sum + count, 0);
    const avgRafflesPerParticipant = (totalRaffleParticipations / totalParticipants).toFixed(1);
    
    const loyalParticipants = Object.values(participantCounts).filter(count => count >= 3).length;

    // Get new participants this month
    const thisMonth = new Date();
    thisMonth.setDate(1);
    thisMonth.setHours(0, 0, 0, 0);
    
    const monthRaffles = await pool.query(
      `SELECT participants FROM raffle_history 
       WHERE username = $1 AND status = 'completed' AND raffle_date >= $2`,
      [username, thisMonth]
    );

    const newThisMonth = monthRaffles.rows.reduce((count, raffle) => {
      const participants = raffle.participants || [];
      return count + participants.length;
    }, 0);

    res.json({
      ok: true,
      data: {
        returnRate,
        avgRafflesPerParticipant: parseFloat(avgRafflesPerParticipant),
        loyalParticipants,
        newThisMonth
      }
    });
  } catch (error) {
    console.error('Profile retention error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Get profile comparison stats
app.get('/api/profile/comparison', async (req, res) => {
  try {
    const username = req.headers['x-user-name'];

    if (!username) {
      return res.status(401).json({ ok: false, error: 'Not authenticated' });
    }

    // Get current user's completion rate
    const userStats = await pool.query(
      `SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
       FROM raffle_history
       WHERE username = $1`,
      [username]
    );

    const userTotal = parseInt(userStats.rows[0].total) || 0;
    const userCompleted = parseInt(userStats.rows[0].completed) || 0;
    
    if (userTotal === 0) {
      // No data for this user yet
      return res.json({
        ok: true,
        data: {
          responseSpeed: 0,
          completionRate: 0,
          satisfaction: 0
        }
      });
    }

    const userCompletionRate = (userCompleted / userTotal) * 100;

    // Get all other users' completion rates for comparison
    const allUsers = await pool.query(
      `SELECT username,
        COUNT(*) as total,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
       FROM raffle_history
       WHERE username != $1
       GROUP BY username
       HAVING COUNT(*) > 0`,
      [username]
    );

    if (allUsers.rows.length === 0) {
      // No other users to compare against - return 50th percentile
      return res.json({
        ok: true,
        data: {
          responseSpeed: 50,
          completionRate: 50,
          satisfaction: 50
        }
      });
    }

    // Calculate how many users have lower completion rates
    const usersWithLowerRate = allUsers.rows.filter(u => {
      const total = parseInt(u.total) || 0;
      const completed = parseInt(u.completed) || 0;
      if (total === 0) return false;
      const rate = (completed / total) * 100;
      return rate < userCompletionRate;
    }).length;

    const totalUsers = allUsers.rows.length;
    const completionRatePercentile = totalUsers > 0 ? Math.round((usersWithLowerRate / totalUsers) * 100) : 50;

    // For now, use completion rate as a proxy for other metrics
    // TODO: Track response speed and satisfaction separately
    res.json({
      ok: true,
      data: {
        responseSpeed: 0,              // Not tracked yet
        completionRate: completionRatePercentile,
        satisfaction: 0                // Not tracked yet
      }
    });
  } catch (error) {
    console.error('Profile comparison error:', error);
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ============================================
// USER MANAGEMENT ROUTES
// ============================================
require('./user-routes')(app, pool);

// Start server
app.listen(port, () => {
  console.log(`🚀 Raffle Manager API running on http://localhost:${port}`);
  console.log(`📊 Test endpoint: http://localhost:${port}/api/test`);
});
