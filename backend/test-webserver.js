// Simple test to start the web server only
import { WebServer } from './server/web-server.js';

console.log('Starting web server test...');

const webServer = new WebServer();

webServer.start()
  .then(() => {
    console.log('Web server started successfully on port 3003');
  })
  .catch((error) => {
    console.error('Failed to start web server:', error);
    process.exit(1);
  });