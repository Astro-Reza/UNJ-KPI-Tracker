-- ============================================
-- KPI Dashboard — Database Schema
-- International Office Student & Jobdesc Data
-- ============================================

CREATE TABLE IF NOT EXISTS student_data (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name_id         TEXT    NOT NULL,
    email_id        TEXT    NOT NULL,
    department_id   INTEGER NOT NULL CHECK (department_id BETWEEN 1 AND 6),
    nim_id          TEXT    NOT NULL UNIQUE,
    score           REAL    DEFAULT 0,
    job_id_list     TEXT    DEFAULT ''
);

-- Department reference:
--   1 = Head of International Office
--   2 = Secretary
--   3 = Administration
--   4 = Media & Design
--   5 = Hospitality
--   6 = Community Impact

CREATE TABLE IF NOT EXISTS jobdesc_data (
    job_id      TEXT    PRIMARY KEY,
    job_name    TEXT    NOT NULL,
    type_id     TEXT    NOT NULL,
    start_date  TEXT    NOT NULL,
    end_date    TEXT,
    status_id   INTEGER NOT NULL DEFAULT 1 CHECK (status_id BETWEEN 1 AND 5)
);

-- Status reference:
--   1 = Planning
--   2 = In-Progress
--   3 = Execution
--   4 = Documentation
--   5 = Lecturer Review
