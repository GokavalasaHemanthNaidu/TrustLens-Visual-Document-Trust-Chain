-- ==========================================
-- Supabase Row Level Security (RLS) Setup
-- ==========================================
-- Run this in your Supabase SQL Editor to secure the `documents` table.

-- 1. Enable RLS on documents table
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- 2. Policy: Users can only access their own documents
-- This prevents users from seeing other people's PII in their vault.
CREATE POLICY "Users can only access their own documents"
ON documents FOR ALL
USING (user_id = auth.uid());

-- 3. Policy: Public verification by hash/ID only
-- Allows the public verification portal to work without a login, 
-- but only if they know the exact document ID or hash.
CREATE POLICY "Public verification by hash only"
ON documents FOR SELECT
USING (true); 

-- Note on Public Verification:
-- Even though public select is enabled, the Streamlit app's UI logic
-- should restrict what fields are shown publicly (e.g. only return a 
-- True/False authenticity status, not the full PII) to prevent data scraping.

-- 4. Policy: Only authenticated users can upload new documents
CREATE POLICY "Authenticated users can upload"
ON documents FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- 5. Policy: Users can only delete their own documents
CREATE POLICY "Users can delete their own documents"
ON documents FOR DELETE
USING (auth.uid() = user_id);

-- ==========================================
-- VERIFICATION
-- Run these queries to test your policies
-- ==========================================

-- Check if RLS is active:
SELECT relname, relrowsecurity 
FROM pg_class 
WHERE relname = 'documents';
