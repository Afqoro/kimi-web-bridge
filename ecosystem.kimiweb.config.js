module.exports = {
  apps: [{
    name: 'kimi-web-bridge',
    script: './kimi-web-bridge',
    cwd: '/home/agentuser/apps/kimi-web-bridge',
    max_memory_restart: '100M',
    out_file: '/home/agentuser/apps/kimi-web-bridge/logs/out.log',
    error_file: '/home/agentuser/apps/kimi-web-bridge/logs/err.log',
    time: true
  }]
};
