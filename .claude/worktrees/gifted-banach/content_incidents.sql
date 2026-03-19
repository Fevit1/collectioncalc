-- Content Moderation: Incident Logging Table
-- Run this on your database before deploying

CREATE TABLE IF NOT EXISTS content_incidents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    endpoint VARCHAR(255) NOT NULL,
    was_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    reason TEXT,
    labels JSONB,
    image_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for quick admin lookups
CREATE INDEX IF NOT EXISTS idx_content_incidents_blocked ON content_incidents(was_blocked, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_incidents_user ON content_incidents(user_id);
