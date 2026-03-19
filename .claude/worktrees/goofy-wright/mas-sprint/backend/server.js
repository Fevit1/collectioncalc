require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3001;

// CORS — allow martechb2c.com and localhost for testing
app.use(cors({
  origin: [
    'https://martechb2c.com',
    'https://www.martechb2c.com',
    'https://mas.martechb2c.com',
    'http://localhost:3000',
    'http://localhost:3001',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:3001'
  ],
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'x-mas-password']
}));

app.use(express.json({ limit: '1mb' }));

// Serve frontend static files (for local dev convenience)
app.use(express.static(path.join(__dirname, '..', 'frontend')));

// Health check (no auth required)
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Password middleware for /api routes (except health)
const passwordAuth = (req, res, next) => {
  if (req.headers['x-mas-password'] !== process.env.MAS_PASSWORD) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
};

// Proxy endpoint — forwards to Anthropic Messages API
app.post('/api/claude', passwordAuth, async (req, res) => {
  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': process.env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify(req.body)
    });

    if (!response.ok) {
      const errorBody = await response.text();
      console.error(`Anthropic API error ${response.status}:`, errorBody);
      return res.status(response.status).json({
        error: 'Anthropic API error',
        status: response.status,
        detail: errorBody
      });
    }

    const data = await response.json();
    res.json(data);
  } catch (err) {
    console.error('Proxy error:', err.message);
    res.status(502).json({ error: 'Failed to reach Anthropic API', detail: err.message });
  }
});

// SPA fallback — serve index.html for all non-API routes
app.get('*', (req, res) => {
  if (!req.path.startsWith('/api')) {
    res.sendFile(path.join(__dirname, '..', 'frontend', 'index.html'));
  }
});

app.listen(PORT, () => {
  console.log(`MAS Proxy running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/api/health`);
});
