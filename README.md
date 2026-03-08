# KPI Dashboard — International Office

A lightweight, feature-rich Flask-based web application designed for the International Office to manage student registrations, track project tasks, monitor KPI (Key Performance Indicator) scores, and maintain a centralized database.

## Features

- **Authentication System:** Secure login for administrators.
- **Dashboard & Leaderboard:** View ongoing/upcoming projects, media logs, recent tasks, and top performers across different departments.
- **Task Management (Kanban-style):** Create and track tasks across various stages (Planning, In-Progress, Execution, Documentation, Lecturer Review, Done).
- **Student Database:** Register new students, assign departments, and track their accumulated KPI scores based on task contributions.
- **Data Export & Integration:** 
  - Export data locally as CSV or SQL files.
  - Push student statistics seamlessly to Google Sheets using a Google Apps Script Web App sync.
- **File-based Storage Engine:** Uses robust CSV file handling to store data while automatically generating SQL backup statements.

## Departments & Task Categories

**Departments:**
- Head of International Office
- Secretary
- Administration
- Media & Design
- Hospitality
- Community Impact

**Task Categories:**
- Publication
- Event
- Camp

## Project Structure

```text
KPI-Dashboard/
├── app.py                  # Main Flask application and backend API routes
├── database/               # File-based database storage
│   ├── student_data.csv    # CSV containing student records
│   ├── student_data.sql    # Auto-generated SQL statements for students
│   ├── task_data.csv       # CSV containing task records
│   ├── task_data.sql       # Auto-generated SQL statements for tasks
│   ├── task_contributors.csv # CSV linking students to tasks with points
│   └── task_contributors.sql # Auto-generated SQL for contributors
├── static/                 # Static assets (CSS, JS, images)
└── templates/              # HTML Templates (Jinja2)
    ├── login.html          # Authentication page
    ├── home.html           # Main dashboard and leaderboards
    ├── database.html       # Full student database view
    ├── kanban.html         # Task tracking board
    └── registration.html   # New student registration form
```

## Setup & Installation

**Prerequisites:**
- Python 3.7+
- pip (Python package installer)

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd KPI-Dashboard
   ```

2. **Install dependencies:**
   It is recommended to use a virtual environment.
   ```bash
   pip install flask requests werkzeug
   ```

3. **Configure Environment Variables (Optional):**
   - You can define a custom `SECRET_KEY` for Flask sessions.
   - For Google Sheets integration, update the `WEB_APP_URL` in `app.py` to point to your deployed Google Apps Script.

4. **Run the Application:**
   ```bash
   python app.py
   ```
   The application will start in debug mode on `http://127.0.0.1:5000/`.

## Credentials
The default administrator credentials are defined in `app.py`.
- **Username:** `admin-cis`
- **Password:** *(Hash specified in source; ensure you know the original key or change the hash)*

## Usage

1. Open a web browser and navigate to `http://127.0.0.1:5000/`.
2. Login using the admin credentials.
3. Use the navigation to:
   - **Register** new students.
   - **Manage Database** to view all student stats and export data.
   - **Kanban** to add and update task statuses.
   - Track active tasks and **Leaderboard** on the Home dashboard.

## Important Notes on Data Storage
This application primarily uses CSV files as its storage engine. Each time a CSV file is updated, a corresponding `.sql` file is regenerated automatically as a backup. Ensure your application has basic read/write permissions to the `database` folder.
