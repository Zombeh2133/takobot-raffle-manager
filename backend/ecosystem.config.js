module.exports = {
  apps: [{
    name: 'raffle-backend',
    script: './server.js',
    instances: 1,
    exec_mode: 'fork',
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      PORT: 3001,
      DATABASE_URL: 'postgresql://maki:MAKI2144@localhost:5432/raffle_manager'
    }
  }]
};
