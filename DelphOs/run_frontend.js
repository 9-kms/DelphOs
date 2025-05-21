// Simple HTTP server to serve the React frontend
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3000;
console.log('Starting DelphOs Crypto Dashboard Frontend...');

// Create HTTP server
const server = http.createServer((req, res) => {
  // Default to serving index.html
  let filePath = './frontend/public/index.html';
  
  // For other files, map the URL to the corresponding file
  if (req.url !== '/') {
    // Remove any query string
    const reqPath = req.url.split('?')[0];
    filePath = './frontend/public' + reqPath;
  }
  
  // Get file extension to determine content type
  const extname = path.extname(filePath);
  let contentType = 'text/html';
  
  // Set content type based on file extension
  switch (extname) {
    case '.js':
      contentType = 'text/javascript';
      break;
    case '.css':
      contentType = 'text/css';
      break;
    case '.json':
      contentType = 'application/json';
      break;
    case '.png':
      contentType = 'image/png';
      break;
    case '.jpg':
    case '.jpeg':
      contentType = 'image/jpeg';
      break;
    case '.svg':
      contentType = 'image/svg+xml';
      break;
  }
  
  // Read and serve the file
  fs.readFile(filePath, (err, content) => {
    if (err) {
      if (err.code === 'ENOENT') {
        // If the file doesn't exist, try serving index.html
        fs.readFile('./frontend/public/index.html', (indexErr, indexContent) => {
          if (indexErr) {
            res.writeHead(500);
            res.end('Error loading index.html');
          } else {
            res.writeHead(200, { 'Content-Type': 'text/html' });
            res.end(indexContent, 'utf-8');
          }
        });
      } else {
        // Server error
        res.writeHead(500);
        res.end(`Server Error: ${err.code}`);
      }
    } else {
      // Success - serve the file
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content, 'utf-8');
    }
  });
});

// Start the server
server.listen(PORT, '0.0.0.0', () => {
  console.log(`DelphOs Frontend is running at http://0.0.0.0:${PORT}/`);
  console.log('You can now use your crypto dashboard with terminal-style interface.');
  console.log('The backend API is running at http://0.0.0.0:5000/');
});