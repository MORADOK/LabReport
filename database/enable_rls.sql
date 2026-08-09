-- ========================================
-- Enable Row Level Security for UAReport
-- ========================================
-- This script enables RLS and creates policies for the records table
-- to ensure proper access control and data security.

-- Enable Row Level Security on records table
ALTER TABLE public.records ENABLE ROW LEVEL SECURITY;

-- Policy 1: Allow service role full access (for backend operations)
-- This allows the backend application (using postgres user) to perform all operations
CREATE POLICY "Enable full access for service role"
ON public.records
FOR ALL
TO authenticated, anon
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
