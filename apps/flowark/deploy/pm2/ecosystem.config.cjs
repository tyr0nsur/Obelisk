const path = require('node:path');

const repoRoot = path.resolve(__dirname, '../..');

module.exports = {
  apps: [{
    name: 'ark-dashboard',
    cwd: path.join(repoRoot, 'server'),
    script: 'server.js',
    exec_mode: 'fork',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '512M',
    kill_timeout: 10000,
    env: {
      NODE_ENV: process.env.NODE_ENV || 'production',
    },
  }],
};
