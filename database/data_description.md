# Main Data Description

## Student Data

- **name_id**: student name
- **department_id**: department, each student has their own department
  1. Head of International Office
  2. Secretary
  3. Administration
  4. Media & Design
  5. Hospitality
  6. Community Impact
- **nim_id**: Student ID Number
- **score**: Calculated score based on performance of the students.

## Task Data

- **task_id**: id number assigned to each jobdesc automatically. The equation is based on the input date + type of jobdesc.
- **task_name**: The name of the job
- **type_id**: Type of the job taken by students.
  1. Publication
  2. Event
  3. Camp
- **start_date**: Starting date of the job.
- **end_date**: Date the job ended.
- **status_id**: Status of the job defined as follows:
  1. Planning
  2. In-Progress
  3. Execution
  4. Documentation
  5. Lecturer Review

# NAME LIST

This system utilizes a **Relational Model** to ensure data efficiency, eliminate redundancy, and allow for automated calculations. The core logic connects **Who** (Students) with **What** (Tasks) through **How Much** (Contribution Points).

Below is the list of tables and the Supabase database:

## 'Student-Database'
1. `id`: 		int8
2. `create_at`: 	timestamptz
3. `name_id`: 		text
4. `email_id`: 	text
5. `department_id`: 	int2
6. `nim_id`: 		text
7. `score`: 		float8
8. `password`: 	text

## 'task_data'
1. `id`: 			int_8
2. `created_at`: 	timestamptz
3. `task_name`: 	text
4. `type_id`: 		int2
5. `start_date`: 	date
6. `end_date`: 	date
7. `status_id`: 	int2
8. `pic`: 		text
9. `related_links`: 	text
10. `description`: 	text

## 'task_contributors'
1. `id`: 			int8
2. `created_at`: 		timestamptz
3. `task_id`: 		int2
4. `student_id`: 		int8
5. `points`: 		float8
6. `contribution_detail`: 	text

# Relation Explanation

### Supabase Configuration
To connect this system to your Supabase project, you will need the following environment variables (which you can place in a `.env` file):

- **SUPABASE_URL**: `[INSERT_YOUR_SUPABASE_PROJECT_URL_HERE]`
- **SUPABASE_KEY**: `[INSERT_YOUR_SUPABASE_SERVICE_ROLE_KEY_HERE]`

### 1. Table: `Student-Database` (The "Who")
This is the master table containing profiles for all organization members (approx. 80 people).
* **Primary Key:** `id` (Unique Identifier).
* **Characteristics:** Each row represents one unique student.
* **Relationships:**
    * **One-to-Many** to `task_data` (linked as the primary PIC).
    * **One-to-Many** to `task_contributors` (linked as a team contributor).

### 2. Table: `task_data` (The "What")
This table stores the metadata for every project, event, or task within the organization.
* **Primary Key:** `id` (Unique Identifier).
* **Note:** The `pic` column should ideally be a **Foreign Key** pointing to `Student-Database.id` to ensure the "Person in Charge" is a registered member.
* **Relationships:**
    * **One-to-Many** to `task_contributors`. A single task can have multiple contribution entries from different students.

### 3. Table: `task_contributors` (The "Bridge")
This is the **Junction Table** that handles the **Many-to-Many** relationship between Students and Tasks.
* **Primary Key:** `id`.
* **Foreign Key 1 (`task_id`):** References `task_data.id`.
* **Foreign Key 2 (`student_id`):** References `Student-Database.id`.
* **Logic:** Every row in this table records one instance of a student contributing to a specific task, along with the points earned for that specific contribution.

---

## Data Flow Illustration

> **Students (80 Members)** $\rightarrow$ **Contributions (Bridge)** $\leftarrow$ **Tasks (Projects)**

If **Reza** and **Alex** both work on the task **"SeaTeacher 2026"**, the data is recorded as follows:

1.  In `task_data`, there is **one entry** for "SeaTeacher 2026" (e.g., ID: 101).
2.  In `task_contributors`, **two separate rows** are created:
    * Row 1: `task_id: 101`, `student_id: (Reza's ID)`, `points: 10.0`.
    * Row 2: `task_id: 101`, `student_id: (Alex's ID)`, `points: 8.5`.

---

## Technical Notes for Developers

To ensure the Streamlit application remains performant for 80+ active users:

* **Referential Integrity:** Set `Foreign Keys` in Supabase to `CASCADE` on delete. If a task is deleted, the associated points in `task_contributors` should be automatically removed to prevent "orphan" data.
* **Real-time Updates:** Enable **Supabase Realtime** on the `task_contributors` and `task_data` tables. This allows the organization's leadership dashboard to update instantly whenever a member logs new points.
* **Indexing:** Create indexes on `task_id` and `student_id` within the `task_contributors` table to ensure that fetching a specific student's history is instantaneous.
* **Calculated Fields:** Total scores should not be typed manually. They should be calculated using a summation of points:
    $$\text{Total Score} = \sum_{i=1}^{n} \text{points}_i$$
    Where $n$ is the number of tasks contributed to by a specific student.
