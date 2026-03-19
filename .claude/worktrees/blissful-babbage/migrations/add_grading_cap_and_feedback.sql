-- Migration: Add grading usage cap + user feedback table
-- Session 88: Beta user management

-- Grading usage tracking (mirrors existing valuations_this_month pattern)
ALTER TABLE users ADD COLUMN IF NOT EXISTS gradings_this_month INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS gradings_reset_date TIMESTAMPTZ;

-- User feedback table
CREATE TABLE IF NOT EXISTS user_feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    feedback_type VARCHAR(20) NOT NULL,  -- 'grading_rating' or 'general'
    rating INTEGER,                       -- 1-5 stars, or 1=thumbs up / 0=thumbs down
    comment TEXT,
    page_url TEXT,
    grading_id INTEGER,                   -- links to assessment if grading feedback
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_feedback_user ON user_feedback(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_feedback_type ON user_feedback(feedback_type, created_at DESC);
