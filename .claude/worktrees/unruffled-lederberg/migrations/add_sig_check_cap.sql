-- Migration: Add signature identification usage cap
-- Session 88: Beta user cost control

ALTER TABLE users ADD COLUMN IF NOT EXISTS sig_checks_this_month INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS sig_checks_reset_date TIMESTAMPTZ;
