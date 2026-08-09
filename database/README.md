# Database Security Setup

## 🔒 Row Level Security (RLS)

### ⚠️ Security Warning
The Supabase linter detected that RLS is **not enabled** on the `public.records` table. This is a **critical security issue** that must be addressed before production deployment.

### Why RLS is Important
- Prevents unauthorized direct access to database tables
- Enforces access control at the database level
- Required for PostgREST API security
- Protects sensitive patient data (CYBOW 11M test results)

---

## 📋 Setup Instructions

### Step 1: Enable RLS
Run the SQL script in your Supabase SQL Editor:

```bash
# Option 1: Copy and paste the content of enable_rls.sql into Supabase SQL Editor
# Option 2: Use psql command (if you have direct access)
psql $DATABASE_URL -f database/enable_rls.sql
```

### Step 2: Verify RLS is Enabled
After running the script, verify in Supabase Dashboard:

1. Go to **Database** → **Tables** → **records**
2. Click on the table
3. Check that "Enable Row Level Security" is **ON**

### Step 3: Test Policies
Run this query to see active policies:

```sql
SELECT * FROM pg_policies WHERE tablename = 'records';
```

---

## 🔑 Current Policy

### Policy: "Enable full access for service role"
- **Applies to:** `authenticated` and `anon` roles
- **Operations:** ALL (SELECT, INSERT, UPDATE, DELETE)
- **Condition:** Always allows access

**⚠️ Note:** This is a permissive policy suitable for backend-only access. If you plan to expose the database via PostgREST API directly to clients, you should implement more restrictive policies.

---

## 🛡️ Alternative: Restrictive Policies

If you need more granular access control, uncomment the alternative policies in `enable_rls.sql`:

### Policy Options:
1. **INSERT Policy** - Allow authenticated users to insert records
2. **SELECT Policy** - Allow authenticated users to read records
3. **UPDATE Policy** - Allow authenticated users to modify records
4. **DELETE Policy** - Allow authenticated users to delete records

### Example: User-Specific Data Isolation
If you want users to only see their own records, modify the policy:

```sql
CREATE POLICY "Users can only see their own records"
ON public.records
FOR SELECT
TO authenticated
USING (notes = auth.uid()::text);  -- Assumes 'notes' stores user ID
```

---

## 📊 Database Schema

### Table: `public.records`

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| date | TIMESTAMP | Test date/time |
| urobilinogen | VARCHAR(50) | Urobilinogen level |
| glucose | VARCHAR(50) | Glucose level |
| bilirubin | VARCHAR(50) | Bilirubin level |
| ketones | VARCHAR(50) | Ketones level |
| specific_gravity | REAL | Specific gravity |
| blood | VARCHAR(50) | Blood level |
| ph | REAL | pH value |
| protein | VARCHAR(50) | Protein level |
| nitrite | VARCHAR(50) | Nitrite level |
| leukocytes | VARCHAR(50) | Leukocytes level |
| ascorbic_acid | VARCHAR(50) | Ascorbic acid level |
| notes | TEXT | Patient name/notes |

---

## 🚀 Production Deployment Checklist

Before deploying to production:

- [ ] Enable RLS on `public.records` table
- [ ] Create appropriate policies based on access requirements
- [ ] Test policies with different user roles
- [ ] Review Supabase Database Linter warnings
- [ ] Ensure `DATABASE_URL` uses secure connection (SSL)
- [ ] Rotate database credentials if exposed
- [ ] Set up database backups
- [ ] Configure connection pooling limits

---

## 📝 Maintenance

### Check RLS Status
```sql
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public';
```

### View Active Policies
```sql
SELECT * FROM pg_policies WHERE schemaname = 'public';
```

### Disable RLS (NOT RECOMMENDED)
```sql
ALTER TABLE public.records DISABLE ROW LEVEL SECURITY;
```

---

## 🔗 Resources

- [Supabase RLS Documentation](https://supabase.com/docs/guides/auth/row-level-security)
- [PostgreSQL RLS Guide](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Database Linter Rules](https://supabase.com/docs/guides/database/database-linter)
