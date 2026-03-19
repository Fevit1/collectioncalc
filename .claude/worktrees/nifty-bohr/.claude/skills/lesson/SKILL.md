---
name: lesson
description: Log a bug fix or learning to tfo_lessons table in Supabase
disable-model-invocation: true
---

Log a lesson learned from a bug or fix to the `tfo_lessons` table.

**Usage:** `/lesson <brief description of what happened>`

## Steps:

1. First, ensure the `tfo_lessons` table exists (Supabase project ID: `kgqnwfpklodyyiqariid`). If not, create it:
   ```sql
   CREATE TABLE IF NOT EXISTS tfo_lessons (
     id SERIAL PRIMARY KEY,
     created_at TIMESTAMPTZ DEFAULT NOW(),
     category TEXT NOT NULL,        -- 'bug', 'fix', 'pattern', 'gotcha'
     summary TEXT NOT NULL,         -- one-line description
     details TEXT,                  -- full context
     file_path TEXT,                -- relevant file if applicable
     prevention TEXT,               -- how to avoid this in the future
     severity TEXT DEFAULT 'medium' -- 'low', 'medium', 'high', 'critical'
   );
   ```

2. Analyze the current conversation context to extract:
   - **category**: What type of lesson is this?
   - **summary**: One-line description
   - **details**: What happened and why
   - **file_path**: Which file was involved (if any)
   - **prevention**: How to prevent this in the future

3. Insert the lesson using the Supabase MCP:
   ```sql
   INSERT INTO tfo_lessons (category, summary, details, file_path, prevention, severity)
   VALUES (...);
   ```

4. Confirm the lesson was saved and show the record.
