-- ========================================
-- Enable Row Level Security for UAReport
-- ========================================
-- This script enables RLS and creates policies for the records table
-- to ensure proper access control and data security.
--
-- Security Model:
-- - Service role (backend) has full access for LINE Bot and Dashboard operations
-- - Anonymous and authenticated users have NO direct access
-- - All data access must go through the backend application

-- Enable Row Level Security on records table
ALTER TABLE public.records ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if any (for clean re-run)
DROP POLICY IF EXISTS "Enable full access for service role" ON public.records;
DROP POLICY IF EXISTS "Service role full access" ON public.records;

-- Policy: Allow service role (backend connection) full access only
-- This is secure because:
-- 1. Only the backend application can access data
-- 2. No direct public/anonymous access
-- 3. Backend controls all business logic and validation
CREATE POLICY "Service role full access"
ON public.records
FOR ALL
TO postgres, service_role
USING (true)
WITH CHECK (true);

-- Alternative: More restrictive policies (uncomment if needed)
/*
-- Policy 2: Allow INSERT for authenticated users only
CREATE POLICY "Enable insert for authenticated users"
ON public.records
FOR INSERT
TO authenticated
WITH CHECK (true);

-- Policy 3: Allow SELECT for authenticated users only
CREATE POLICY "Enable select for authenticated users"
ON public.records
FOR SELECT
TO authenticated
USING (true);

-- Policy 4: Allow UPDATE for authenticated users only
CREATE POLICY "Enable update for authenticated users"
ON public.records
FOR UPDATE
TO authenticated
USING (true)
WITH CHECK (true);

-- Policy 5: Allow DELETE for authenticated users only
CREATE POLICY "Enable delete for authenticated users"
ON public.records
FOR DELETE
TO authenticated
USING (true);
*/

-- Verify RLS is enabled
SELECT
    schemaname,
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
AND tablename = 'records';

-- View all policies on the records table
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE schemaname = 'public'
AND tablename = 'records';
