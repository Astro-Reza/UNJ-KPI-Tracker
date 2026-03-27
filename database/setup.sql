-- ============================================
-- KPI Dashboard — PostgreSQL Schema (Supabase)
-- Consolidated Setup Script
-- ============================================

-- 1. Initialize Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Clean Start (Optional: Only if you want to wipe existing tables)
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

DROP FUNCTION IF EXISTS public.handle_new_user ();

DROP TABLE IF EXISTS public.task_contributors CASCADE;

DROP TABLE IF EXISTS public.task_data CASCADE;

DROP TABLE IF EXISTS public.student_database CASCADE;

-- 3. Create Tables

-- Profile table (student_database)
CREATE TABLE public.student_database (
    nim_id TEXT PRIMARY KEY, -- Main business identifier
    user_id UUID UNIQUE REFERENCES auth.users ON DELETE CASCADE, -- Link to Supabase Auth
    created_at TIMESTAMPTZ DEFAULT NOW(),
    name_id TEXT NOT NULL,
    email_id TEXT NOT NULL UNIQUE,
    department_id SMALLINT NOT NULL CHECK (department_id BETWEEN 1 AND 6),
    score DOUBLE PRECISION DEFAULT 0.0,
    job_id_list TEXT DEFAULT '',
    role TEXT DEFAULT 'student' CHECK (role IN ('student', 'admin'))
);

-- Task Metadata table
CREATE TABLE public.task_data (
    task_id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    task_name TEXT NOT NULL,
    type_id SMALLINT NOT NULL CHECK (type_id IN (1, 2, 3)),
    start_date DATE,
    end_date DATE,
    status_id SMALLINT NOT NULL DEFAULT 1 CHECK (status_id BETWEEN 1 AND 7),
    pic TEXT, -- NIM of the PIC student
    related_links TEXT,
    description TEXT
);

-- Junction Table
CREATE TABLE public.task_contributors (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    task_id TEXT REFERENCES public.task_data (task_id) ON DELETE CASCADE,
    nim_id TEXT REFERENCES public.student_database (nim_id) ON DELETE CASCADE,
    points DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    contribution_detail TEXT
);

-- 4. Enable RLS
ALTER TABLE public.student_database ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.task_data ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.task_contributors ENABLE ROW LEVEL SECURITY;

-- 5. RLS Policies
CREATE POLICY "Public profiles are viewable by all" ON public.student_database FOR
SELECT USING (true);

CREATE POLICY "Service role full access on students" ON public.student_database
  FOR ALL TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access on tasks" ON public.task_data
  FOR ALL TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access on contributors" ON public.task_contributors
  FOR ALL TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Users can update their own profile" ON public.student_database FOR
UPDATE USING (auth.uid () = user_id);

CREATE POLICY "Tasks are viewable by all" ON public.task_data FOR
SELECT USING (true);

CREATE POLICY "Contributions are viewable by all" ON public.task_contributors FOR
SELECT USING (true);

-- 6. Auth Trigger (Automatic Profile Creation)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.student_database (user_id, nim_id, name_id, email_id, department_id)
  VALUES (
    new.id, 
    COALESCE(new.raw_user_meta_data->>'nim_id', 'NIM-PENDING'),
    COALESCE(new.raw_user_meta_data->>'name_id', 'New Student'), 
    new.email,
    COALESCE((new.raw_user_meta_data->>'department_id')::smallint, 1)
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();