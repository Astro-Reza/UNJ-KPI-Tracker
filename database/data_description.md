# KPI Dashboard Data Description (Firebase Migration)

This document describes the data structure and schema for the KPI Dashboard, currently utilizing **Firebase Firestore** as the primary database. The system follows a relational logic adapted for a NoSQL environment to track student performance and task management.

---

## 1. Core Data Collections

### **Collection: `students`**
Contains profiles and performance stats for all organization members.
- **Document ID**: `user_uid` (Authenticated Firebase User UID)
- **Fields**:
  - `name`: (string) Full name of the student.
  - `email`: (string) University/Personal email.
  - `department_id`: (int) ID of the department (see [Constants](#constants)).
  - `nim_id`: (string) Student ID Number (Unique).
  - `score`: (number) Total accumulated points from finished tasks.
  - `job_id_list`: (array of strings) List of `task_id`s the student is contributing to.
  - `created_at`: (timestamp) Registration date.
  - `updated_at`: (timestamp) Last profile update.

### **Collection: `tasks`**
Stores metadata for projects, events, and recurring tasks.
- **Document ID**: Auto-generated string (or formatted ID like `YYYYMMDD-Type-Seq`).
- **Fields**:
  - `task_name`: (string) Name of the project or activity.
  - `type_id`: (int) Category of the task (see [Constants](#constants)).
  - `start_date`: (string/date) Project commencement.
  - `end_date`: (string/date) Project deadline/completion.
  - `status_id`: (int) Current status of the task (see [Constants](#constants)).
  - `pic`: (string) Person in Charge (Name or Student ID).
  - `related_links`: (string/array) Links to documentation, assets, or reports.
  - `description`: (string) Detailed brief of the task.
  - `created_at`: (timestamp)
  - `updated_at`: (timestamp)

### **Collection: `contributions`** (The "Bridge")
Handles the Many-to-Many relationship between Students and Tasks.
- **Document ID**: Auto-generated string.
- **Fields**:
  - `task_id`: (string) Reference to the document in `tasks`.
  - `uid`: (string) Reference to the document in `students`.
  - `points`: (number) Contribution points awarded for this specific task.
  - `created_at`: (timestamp)

---

## 2. Constants & Enums

These mappings are defined in the application logic (`app.py`) to maintain consistency across the UI and database.

### **Departments (`department_id`)**
1. **Head of International Office**
2. **Secretary**
3. **Administration**
4. **Media & Design**
5. **Hospitality**
6. **Community Impact**

### **Task Types (`type_id`)**
1. **Publication** (e.g., Social Media, Newsletter)
2. **Event** (e.g., Seminars, Workshops)
3. **Camp** (e.g., International Student Camp)

### **Task Statuses (`status_id`)**
1. **Planning**: Initial drafting and concept.
2. **In-Progress**: Actively being worked on.
3. **Execution**: The main event or publication is live.
4. **Documentation**: Finalizing reports and archives.
5. **Lecturer Review**: Awaiting approval from mentors/lecturers.
6. **Done**: Internal completion.
7. **Finished**: Fully finalized and points are eligible for calculation.

---

## 3. Data Logic & Relations

### **Score Calculation**
Total scores are calculated dynamically or synced using the `_sync_student_stats` logic:
$$\text{Student Score} = \sum (\text{points from } \textit{contributions} \text{ where } \textit{task.status\_id} == 7)$$

### **The "Bridge" Logic**
Instead of a single list, the `contributions` collection acts as a junction.
- To find all students for a task: Query `contributions` where `task_id == [ID]`.
- To find all tasks for a student: Query `contributions` where `uid == [UID]`.

### **Referential Integrity**
During the migration from Supabase, ensuring that `nim_id` and `email` remain unique is handled at the application level and through Firebase Authentication.

---

## 4. Technical Environment

- **Database**: Firebase (Admin SDK 6.0.0+)
- **Platform**: Flask 3.0.0
- **Authentication**: Firebase Auth (email/password)
- **Environment Config**:
  - `FIREBASE_PROJECT_ID`: The ID of your Firebase project.
  - `FIREBASE_CREDENTIALS_PATH`: Path to your `serviceAccountKey.json`.
  - `DATABASE_URL`: The URL for your Realtime Database (if used) or Firestore config.
