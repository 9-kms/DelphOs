// Simple HTTP server to serve the React frontend
const http = require('http');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

const PORT = 3000;
console.log('Setting up DelphOs Crypto Dashboard frontend...');

// First, check if we need to start the React development server
const useDevServer = true;

if (useDevServer) {
  console.log('Starting React development server...');
  const child = exec('cd frontend && npm start');
  
  child.stdout.on('data', (data) => {
    console.log(`Frontend: ${data}`);
  });
  
  child.stderr.on('data', (data) => {
    console.error(`Frontend error: ${data}`);
  });
  
  child.on('close', (code) => {
    console.log(`Frontend process exited with code ${code}`);
  });
} else {
  // Fallback to static file server if needed
  const MIME_TYPES = {
    '.html': 'text/html',
    '.js': 'text/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
  };

  const server = http.createServer((req, res) => {
    console.log(`Request: ${req.url}`);
    
    // Default to index.html for the root path or if no file extension
    let filePath;
    if (req.url === '/' || !path.extname(req.url)) {
      filePath = './frontend/public/index.html';
    } else {
      // Remove any query params
      const urlPath = req.url.split('?')[0];
      filePath = './frontend/public' + urlPath;
    }
    
    const extname = path.extname(filePath);
    const contentType = MIME_TYPES[extname] || 'application/octet-stream';
    
    fs.readFile(filePath, (error, content) => {
      if (error) {
        if (error.code === 'ENOENT') {
          // If the specific file wasn't found, serve index.html for client-side routing
          fs.readFile('./frontend/public/index.html', (err, indexContent) => {
            if (err) {
              res.writeHead(500);
              res.end('Error loading index.html');
            } else {
              res.writeHead(200, { 'Content-Type': 'text/html' });
              res.end(indexContent, 'utf-8');
            }
          });
        } else {
          res.writeHead(500);
          res.end(`Server Error: ${error.code}`);
        }
      } else {
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(content, 'utf-8');
      }
    });
  });

  server.listen(PORT, '0.0.0.0', () => {
    console.log(`DelphOs frontend server running at http://0.0.0.0:${PORT}/`);
  });
}