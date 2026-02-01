#!/bin/bash

echo "🔧 Adding auth middleware to server.js..."
echo ""

# Backup
cp ~/takobot-electron/backend/server.js ~/takobot-electron/backend/server.js.pre-middleware

# Add the auth middleware right after session setup
cat > /tmp/add_middleware.py << 'PYTHON_SCRIPT'
import re

with open('/home/ubuntu/takobot-electron/backend/server.js', 'r') as f:
    content = f.read()

# Find the session setup block and add middleware after it
old_block = r'''  }
\}\)\);

// Serve the React build files'''

new_block = r'''  }
}));

// Auth middleware - Extract session data and populate headers for existing endpoints
app.use((req, res, next) => {
  if (req.session && req.session.user) {
    req.headers['x-user-id'] = String(req.session.user.id);
    req.headers['x-user-name'] = req.session.user.username;
    req.headers['x-user-admin'] = String(req.session.user.is_admin);
  }
  next();
});

// Serve the React build files'''

content = re.sub(old_block, new_block, content)

with open('/home/ubuntu/takobot-electron/backend/server.js', 'w') as f:
    f.write(content)

print("✅ Added auth middleware!")
PYTHON_SCRIPT

python3 /tmp/add_middleware.py

echo ""
echo "✅ Auth middleware added!"
echo ""
echo "📝 The middleware extracts session data and populates:"
echo "  - X-User-Id"
echo "  - X-User-Name"
echo "  - X-User-Admin"
echo ""
echo "🔄 Restarting Node.js server..."

# Restart the server
pm2 restart takobot-node

echo ""
echo "✅ Server restarted!"
echo ""
echo "🌐 Hard refresh your browser (Ctrl+Shift+R) and try the Reddit scan again!"
