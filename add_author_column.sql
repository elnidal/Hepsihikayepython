-- Add author column to the post table
ALTER TABLE post ADD COLUMN IF NOT EXISTS author VARCHAR(100);

-- Update any existing posts to have a default author if desired
-- UPDATE post SET author = 'Admin' WHERE author IS NULL; 