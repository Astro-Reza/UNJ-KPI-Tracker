"""
KPI Dashboard — Flask Backend
International Office Student Registration & Task Management
"""

import os
import csv
import json
import datetime
import functools
import requests
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# ── Authentication ───────────────────────────────────
ADMIN_USERNAME = 'admin-cis'
ADMIN_PASSWORD_HASH = 'scrypt:32768:8:1$mfjM50HyCVvDkVfl$025eee058823aff663e2fbee27051d162ea40fcb65019fd51adbb3ab93ec011ff6b174187ac2afb50a4b16736e7ba238fadf7551acd1ace2b987ff8d7b8aa851'


def login_required(f):
    """Decorator that redirects to /login if user is not authenticated."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            # API routes return 401 JSON; page routes redirect
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Paste the URL you copied from the deployment step
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbz0m7XTeCG404waRV07RmZJWTut-hSb_FpTOMQWQsPWlUZXMBrHctk_o2E2E9zVDlqXnw/exec"

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, 'database')
STUDENT_CSV = os.path.join(DATABASE_DIR, 'student_data.csv')
STUDENT_SQL = os.path.join(DATABASE_DIR, 'student_data.sql')
TASK_CSV = os.path.join(DATABASE_DIR, 'task_data.csv')
TASK_SQL = os.path.join(DATABASE_DIR, 'task_data.sql')
CONTRIB_CSV = os.path.join(DATABASE_DIR, 'task_contributors.csv')
CONTRIB_SQL = os.path.join(DATABASE_DIR, 'task_contributors.sql')
CSV_HEADER = ['name_id', 'email_id', 'department_id', 'nim_id', 'score', 'job_id_list', 'password']
TASK_HEADER = ['task_id', 'task_name', 'type_id', 'start_date', 'end_date', 'status_id', 'pic', 'related_links', 'description']
CONTRIB_HEADER = ['task_id', 'nim_id', 'points']

DEPARTMENTS = {
    1: 'Head of International Office',
    2: 'Secretary',
    3: 'Administration',
    4: 'Media & Design',
    5: 'Hospitality',
    6: 'Community Impact',
}

TASK_TYPES = {1: 'Publication', 2: 'Event', 3: 'Camp'}
TASK_STATUSES = {1: 'Planning', 2: 'In-Progress', 3: 'Execution', 4: 'Documentation', 5: 'Lecturer Review', 6: 'Done'}


# ── Student Helpers ──────────────────────────────────
def _ensure_csv():
    """Create CSV with header if it doesn't exist or is empty."""
    if not os.path.exists(STUDENT_CSV) or os.path.getsize(STUDENT_CSV) == 0:
        with open(STUDENT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)


def _read_students():
    """Return list of student dicts from CSV."""
    _ensure_csv()
    students = []
    with open(STUDENT_CSV, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['department_id'] = int(row['department_id'])
            row['department_name'] = DEPARTMENTS.get(row['department_id'], '')
            row['score'] = float(row.get('score', 0))
            if 'password' not in row or not row['password']:
                # Default password is the nim_id hashed
                row['password'] = generate_password_hash(row['nim_id'])
            students.append(row)
    return students


def _append_student(name_id, email_id, department_id, nim_id):
    """Append a student row to the CSV."""
    _ensure_csv()
    with open(STUDENT_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        default_pw = generate_password_hash(nim_id)
        writer.writerow([name_id, email_id, department_id, nim_id, 0, '', default_pw])


def _write_sql():
    """Regenerate the SQL file from current CSV data."""
    students = _read_students()
    with open(STUDENT_SQL, 'w', encoding='utf-8') as f:
        f.write('-- Student Data INSERT statements\n')
        f.write(f'-- Generated on {datetime.datetime.now().isoformat()}\n\n')
        for s in students:
            name = s['name_id'].replace("'", "''")
            email = s.get('email_id', '').replace("'", "''")
            nim = s['nim_id'].replace("'", "''")
            job = s.get('job_id_list', '').replace("'", "''")
            pwd = s.get('password', '').replace("'", "''")
            f.write(
                f"INSERT INTO student_data (name_id, email_id, department_id, nim_id, score, job_id_list, password) "
                f"VALUES ('{name}', '{email}', {s['department_id']}, '{nim}', {s['score']}, '{job}', '{pwd}');\n"
            )


def _nim_exists(nim_id):
    """Check if a NIM already exists in the CSV."""
    students = _read_students()
    return any(s['nim_id'] == nim_id for s in students)


def _write_students(students):
    """Rewrite the entire student CSV from a list of dicts."""
    with open(STUDENT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        for s in students:
            writer.writerow([
                s.get('name_id', ''),
                s.get('email_id', ''),
                s.get('department_id', ''),
                s.get('nim_id', ''),
                s.get('score', 0),
                s.get('job_id_list', ''),
                s.get('password', '')
            ])


# ── Task Helpers ─────────────────────────────────────

def _ensure_task_csv():
    """Create task CSV with header if it doesn't exist or is empty."""
    if not os.path.exists(TASK_CSV) or os.path.getsize(TASK_CSV) == 0:
        with open(TASK_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(TASK_HEADER)


def _read_tasks():
    """Return list of task dicts from CSV."""
    _ensure_task_csv()
    tasks = []
    with open(TASK_CSV, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['type_id'] = int(row['type_id'])
            row['status_id'] = int(row['status_id'])
            row['type_name'] = TASK_TYPES.get(row['type_id'], '')
            row['status_name'] = TASK_STATUSES.get(row['status_id'], '')
            tasks.append(row)
    return tasks


def _generate_task_id(type_id):
    """Generate a unique task ID: YYYYMMDD-{type}-{seq}."""
    today = datetime.date.today().strftime('%Y%m%d')
    tasks = _read_tasks()
    prefix = f"{today}-{type_id}-"
    existing = [t['task_id'] for t in tasks if t['task_id'].startswith(prefix)]
    seq = len(existing) + 1
    return f"{prefix}{seq:03d}"


def _append_task(task_id, task_name, type_id, start_date, end_date, status_id, pic, related_links, description):
    """Append a task row to the CSV."""
    _ensure_task_csv()
    with open(TASK_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([task_id, task_name, type_id, start_date, end_date, status_id, pic, related_links, description])
    _write_task_sql()


def _update_tasks(tasks):
    """Rewrite entire task CSV from a list of dicts."""
    with open(TASK_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(TASK_HEADER)
        for t in tasks:
            writer.writerow([
                t.get('task_id', ''),
                t.get('task_name', ''),
                t.get('type_id', ''),
                t.get('start_date', ''),
                t.get('end_date', ''),
                t.get('status_id', ''),
                t.get('pic', ''),
                t.get('related_links', ''),
                t.get('description', ''),
            ])
    _write_task_sql()


# ── Task SQL Generation ──────────────────────────────

def _write_task_sql():
    """Regenerate task_data.sql from current CSV data."""
    tasks = _read_tasks()
    with open(TASK_SQL, 'w', encoding='utf-8') as f:
        f.write('-- Task Data INSERT statements\n')
        f.write(f'-- Generated on {datetime.datetime.now().isoformat()}\n\n')
        for t in tasks:
            tid = str(t.get('task_id', '')).replace("'", "''")
            tname = str(t.get('task_name', '')).replace("'", "''")
            pic = str(t.get('pic', '')).replace("'", "''")
            links = str(t.get('related_links', '')).replace("'", "''")
            desc = str(t.get('description', '')).replace("'", "''")
            f.write(
                f"INSERT INTO task_data (task_id, task_name, type_id, start_date, end_date, status_id, pic, related_links, description) "
                f"VALUES ('{tid}', '{tname}', {t.get('type_id', 0)}, '{t.get('start_date', '')}', '{t.get('end_date', '')}', "
                f"{t.get('status_id', 0)}, '{pic}', '{links}', '{desc}');\n"
            )


# ── Contributor Helpers ──────────────────────────────

def _ensure_contrib_csv():
    """Create contributor CSV with header if it doesn't exist or is empty."""
    if not os.path.exists(CONTRIB_CSV) or os.path.getsize(CONTRIB_CSV) == 0:
        with open(CONTRIB_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CONTRIB_HEADER)


def _read_task_contributors(task_id):
    """Return list of contributor dicts for a given task."""
    _ensure_contrib_csv()
    results = []
    with open(CONTRIB_CSV, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['task_id'] == task_id:
                row['points'] = float(row.get('points', 0))
                results.append(row)
    return results


def _write_task_contributors(task_id, rows):
    """Rewrite contributors for a specific task. Keeps other tasks' rows intact."""
    _ensure_contrib_csv()
    # Read all existing rows
    all_rows = []
    with open(CONTRIB_CSV, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['task_id'] != task_id:
                all_rows.append(row)
    # Add new rows for this task
    for r in rows:
        all_rows.append({'task_id': task_id, 'nim_id': r['nim_id'], 'points': r.get('points', 0)})
    # Write back
    with open(CONTRIB_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(CONTRIB_HEADER)
        for row in all_rows:
            writer.writerow([row['task_id'], row['nim_id'], row['points']])
    _write_contrib_sql()


def _write_contrib_sql():
    """Regenerate task_contributors.sql from current CSV data."""
    _ensure_contrib_csv()
    all_rows = []
    with open(CONTRIB_CSV, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_rows.append(row)
    with open(CONTRIB_SQL, 'w', encoding='utf-8') as f:
        f.write('-- Task Contributors INSERT statements\n')
        f.write(f'-- Generated on {datetime.datetime.now().isoformat()}\n\n')
        for row in all_rows:
            tid = str(row.get('task_id', '')).replace("'", "''")
            nim = str(row.get('nim_id', '')).replace("'", "''")
            pts = float(row.get('points', 0))
            f.write(
                f"INSERT INTO task_contributors (task_id, nim_id, points) "
                f"VALUES ('{tid}', '{nim}', {pts});\n"
            )

def _update_student_selection(nim_id, selected_task_ids):
    """Update the student's task list in both student_data and task_contributors."""
    students = _read_students()
    student = next((s for s in students if s['nim_id'] == nim_id), None)
    if not student:
        return False

    old_task_ids = set(student.get('job_id_list', '').split(';')) if student.get('job_id_list') else set()
    # Filter out empty strings if any
    old_task_ids = {t for t in old_task_ids if t.strip()}
    new_task_ids = set(selected_task_ids)

    student['job_id_list'] = ';'.join(new_task_ids)
    _write_students(students)
    _write_sql()

    added_tasks = new_task_ids - old_task_ids
    removed_tasks = old_task_ids - new_task_ids

    if added_tasks or removed_tasks:
        _ensure_contrib_csv()
        all_rows = []
        with open(CONTRIB_CSV, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                all_rows.append(row)

        # Remove student from unselected tasks
        all_rows = [row for row in all_rows if not (row['nim_id'] == nim_id and row['task_id'] in removed_tasks)]

        # Add student to newly selected tasks
        for tid in added_tasks:
            all_rows.append({'task_id': tid, 'nim_id': nim_id, 'points': 0})

        with open(CONTRIB_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CONTRIB_HEADER)
            for row in all_rows:
                writer.writerow([row['task_id'], row['nim_id'], row['points']])

        _write_contrib_sql()

    return True

# ── Auth Routes ──────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Show login form (GET) or process login (POST)."""
    if session.get('logged_in'):
        return redirect(url_for('index'))

    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
        else:
            error = 'Invalid username or password.'

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    """Clear session and redirect to login."""
    session.clear()
    return redirect(url_for('login'))


# ── Routes ───────────────────────────────────────────

@app.route('/')
def index():
    tasks = _read_tasks()
    students = _read_students()

    # Count and list contributors per task
    for task in tasks:
        tid = task['task_id']
        contributors = []
        for s in students:
            if tid in s.get('job_id_list', '').split(';'):
                contributors.append(s['name_id'])
        task['contributor_count'] = len(contributors)
        task['contributors_list'] = contributors

    # Event/Camp tasks (type 2, 3) for projects
    ongoing_projects = [t for t in tasks if t['type_id'] in (2, 3) and t['status_id'] in (2, 3)]
    upcoming_projects = [t for t in tasks if t['type_id'] in (2, 3) and t['status_id'] == 1]

    # Publication tasks (type 1) for media log
    media_log = [t for t in tasks if t['type_id'] == 1]

    # Recently viewed = all tasks, most recent first
    recent_tasks = list(reversed(tasks))

    # ── Leaderboard ──────────────────────────────────
    # Overall top performer
    top_overall = max(students, key=lambda s: s['score']) if students else None

    # Top performer per department (skip dept 1 = Head, dept 2 = Secretary)
    dept_leaders = []
    for dept_id in [3, 4, 5, 6]:
        dept_students = [s for s in students if s['department_id'] == dept_id]
        if dept_students:
            best = max(dept_students, key=lambda s: s['score'])
            dept_leaders.append({
                'department_name': DEPARTMENTS[dept_id],
                'name': best['name_id'],
                'score': int(best['score']),
            })

    return render_template('home.html',
                           ongoing_projects=ongoing_projects,
                           upcoming_projects=upcoming_projects,
                           media_log=media_log,
                           recent_tasks=recent_tasks,
                           top_overall=top_overall,
                           dept_leaders=dept_leaders)


@app.route('/database')
@login_required
def database_page():
    students = _read_students()
    dept_counts = {}
    for s in students:
        dept_counts[s['department_id']] = dept_counts.get(s['department_id'], 0) + 1
    scores = [s['score'] for s in students]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0
    top_score = int(max(scores)) if scores else 0

    students_json = json.dumps(students, default=str)
    return render_template('database.html',
                           students=students,
                           students_json=students_json,
                           dept_counts=dept_counts,
                           avg_score=avg_score,
                           top_score=top_score)


@app.route('/student')
def registration():
    return render_template('registration.html')


@app.route('/leaderboard')
@login_required
def leaderboard():
    return render_template('leaderboard.html')


@app.route('/kanban')
@login_required
def kanban():
    tasks = _read_tasks()
    students = _read_students()
    for task in tasks:
        tid = task['task_id']
        contributors = [s['name_id'] for s in students if tid in s.get('job_id_list', '').split(';')]
        task['contributor_count'] = len(contributors)
        task['contributors_list'] = contributors
    planning = [t for t in tasks if t['status_id'] == 1]
    doing = [t for t in tasks if t['status_id'] in (2, 3)]
    review = [t for t in tasks if t['status_id'] == 5]
    done = [t for t in tasks if t['status_id'] == 6]
    return render_template('kanban.html',
                           planning=planning, doing=doing,
                           review=review, done=done)


# ── Student API ──────────────────────────────────────

@app.route('/api/students', methods=['GET'])
@login_required
def get_students():
    """Return all registered students as JSON."""
    students = _read_students()
    return jsonify(students)


@app.route('/api/register', methods=['POST'])
@login_required
def register_student():
    """Register a new student. Expects JSON body."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request body'}), 400

    name_id = (data.get('name_id') or '').strip()
    email_id = (data.get('email_id') or '').strip()
    department_id = data.get('department_id')
    nim_id = (data.get('nim_id') or '').strip()

    # Validation
    errors = {}
    if not name_id:
        errors['name_id'] = 'Student name is required'
    if not email_id:
        errors['email_id'] = 'Email address is required'
    if not department_id or int(department_id) not in DEPARTMENTS:
        errors['department_id'] = 'Please select a valid department'
    if not nim_id:
        errors['nim_id'] = 'Student ID (NIM) is required'
    elif _nim_exists(nim_id):
        errors['nim_id'] = 'This NIM is already registered'

    if errors:
        return jsonify({'errors': errors}), 422

    department_id = int(department_id)
    _append_student(name_id, email_id, department_id, nim_id)
    _write_sql()

    return jsonify({
        'message': f'{name_id} registered successfully!',
        'student': {
            'name_id': name_id,
            'email_id': email_id,
            'department_id': department_id,
            'department_name': DEPARTMENTS[department_id],
            'nim_id': nim_id,
            'score': 0,
            'job_id_list': ''
        }
    }), 201


@app.route('/api/students/save-all', methods=['POST'])
@login_required
def save_all_students():
    """Rewrite the entire student CSV from the provided JSON array."""
    data = request.get_json()
    if not data or 'students' not in data:
        return jsonify({'error': 'Invalid request body'}), 400
    _write_students(data['students'])
    _write_sql()
    return jsonify({'message': f'Saved {len(data["students"])} students'}), 200

@app.route('/api/student/auth', methods=['POST'])
def student_auth():
    """Authenticate a returning student by NIM and password (default NIM). Return student and available tasks."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request body'}), 400
        
    nim_id = (data.get('nim_id') or '').strip()
    password = (data.get('password') or '').strip()
    
    if not nim_id or not password:
        return jsonify({'error': 'NIM and password are required'}), 400
        
    students = _read_students()
    student = next((s for s in students if s['nim_id'] == nim_id), None)
    
    if not student:
        return jsonify({'error': 'Student not found'}), 404
        
    if not check_password_hash(student.get('password', ''), password):
        return jsonify({'error': 'Incorrect password'}), 401
        
    tasks = _read_tasks()
    # Return tasks that are currently available to pick (e.g. Planning, In-progress, Execution)
    available_tasks = [t for t in tasks if t['status_id'] in (1, 2, 3)]
    
    # Do not expose the hashed password to the client profile
    student_profile = {k: v for k, v in student.items() if k != 'password'}
    
    return jsonify({
        'student': student_profile,
        'tasks': available_tasks
    }), 200

@app.route('/api/student/change_password', methods=['POST'])
def change_password():
    """Change a student's password."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request body'}), 400
        
    nim_id = (data.get('nim_id') or '').strip()
    old_password = (data.get('old_password') or '').strip()
    new_password = (data.get('new_password') or '').strip()
    
    if not nim_id or not old_password or not new_password:
        return jsonify({'error': 'All fields are required'}), 400
        
    students = _read_students()
    student_idx = next((i for i, s in enumerate(students) if s['nim_id'] == nim_id), None)
    
    if student_idx is None:
        return jsonify({'error': 'Student not found'}), 404
        
    if not check_password_hash(students[student_idx].get('password', ''), old_password):
        return jsonify({'error': 'Incorrect current password'}), 401
        
    students[student_idx]['password'] = generate_password_hash(new_password)
    _write_students(students)
    _write_sql()
    
    return jsonify({'message': 'Password updated successfully!'}), 200

@app.route('/api/student/tasks', methods=['POST'])
def update_student_tasks():
    """Update a specific student's selected tasks without admin auth"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request body'}), 400
        
    nim_id = (data.get('nim_id') or '').strip()
    task_ids = data.get('task_ids', [])
    
    if not nim_id:
        return jsonify({'error': 'NIM is required'}), 400
        
    success = _update_student_selection(nim_id, task_ids)
    if not success:
        return jsonify({'error': 'Student not found'}), 404
        
    return jsonify({'message': 'Tasks saved successfully!'}), 200

# ── Task API ─────────────────────────────────────────

@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    """Return all tasks as JSON."""
    tasks = _read_tasks()
    return jsonify(tasks)


@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task():
    """Create a new task. Expects JSON body."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request body'}), 400

    task_name = (data.get('task_name') or '').strip()
    type_id = data.get('type_id')
    start_date = (data.get('start_date') or '').strip()
    end_date = (data.get('end_date') or '').strip()
    status_id = data.get('status_id')
    pic = (data.get('pic') or '').strip()
    related_links = (data.get('related_links') or '').strip()
    description = (data.get('description') or '').strip()

    errors = {}
    if not task_name:
        errors['task_name'] = 'Task name is required'
    if not type_id or int(type_id) not in TASK_TYPES:
        errors['type_id'] = 'Please select a valid task type'
    if not start_date:
        errors['start_date'] = 'Start date is required'
    if not end_date:
        errors['end_date'] = 'End date is required'
    if not status_id or int(status_id) not in TASK_STATUSES:
        errors['status_id'] = 'Please select a valid status'

    if errors:
        return jsonify({'errors': errors}), 422

    type_id = int(type_id)
    status_id = int(status_id)
    task_id = _generate_task_id(type_id)

    _append_task(task_id, task_name, type_id, start_date, end_date, status_id, pic, related_links, description)

    return jsonify({
        'message': 'Task created successfully!',
        'task': {
            'task_id': task_id,
            'task_name': task_name,
            'type_id': type_id,
            'type_name': TASK_TYPES[type_id],
            'start_date': start_date,
            'end_date': end_date,
            'status_id': status_id,
            'status_name': TASK_STATUSES[status_id],
            'pic': pic,
            'related_links': related_links,
            'description': description,
        }
    }), 201


@app.route('/api/tasks/<task_id>', methods=['PUT', 'POST'])
@login_required
def update_task(task_id):
    """Update an existing task. Expects JSON body."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request body'}), 400

    tasks = _read_tasks()
    task_idx = next((i for i, t in enumerate(tasks) if t['task_id'] == task_id), None)
    
    if task_idx is None:
        return jsonify({'error': 'Task not found'}), 404

    task_name = (data.get('task_name') or '').strip()
    type_id = data.get('type_id')
    start_date = (data.get('start_date') or '').strip()
    end_date = (data.get('end_date') or '').strip()
    status_id = data.get('status_id')
    pic = (data.get('pic') or '').strip()
    related_links = (data.get('related_links') or '').strip()
    description = (data.get('description') or '').strip()

    errors = {}
    if not task_name:
        errors['task_name'] = 'Task name is required'
    if not type_id or int(type_id) not in TASK_TYPES:
        errors['type_id'] = 'Please select a valid task type'
    if not start_date:
        errors['start_date'] = 'Start date is required'
    if not end_date:
        errors['end_date'] = 'End date is required'
    if not status_id or int(status_id) not in TASK_STATUSES:
        errors['status_id'] = 'Please select a valid status'

    if errors:
        return jsonify({'errors': errors}), 422

    type_id = int(type_id)
    status_id = int(status_id)

    # Update only the allowed fields
    t = tasks[task_idx]
    t['task_name'] = task_name
    t['type_id'] = type_id
    t['start_date'] = start_date
    t['end_date'] = end_date
    t['status_id'] = status_id
    t['pic'] = pic
    t['related_links'] = related_links
    t['description'] = description

    _update_tasks(tasks)

    return jsonify({
        'message': 'Task updated successfully!',
        'task': {
            'task_id': task_id,
            'task_name': task_name,
            'type_id': type_id,
            'type_name': TASK_TYPES[type_id],
            'start_date': start_date,
            'end_date': end_date,
            'status_id': status_id,
            'status_name': TASK_STATUSES[status_id],
            'pic': pic,
            'related_links': related_links,
            'description': description,
        }
    }), 200


@app.route('/api/tasks/<task_id>/contributors', methods=['GET'])
@login_required
def get_task_contributors(task_id):
    """Return contributors for a task, enriched with student info."""
    contribs = _read_task_contributors(task_id)
    students = _read_students()
    student_map = {s['nim_id']: s for s in students}

    result = []
    for c in contribs:
        s = student_map.get(c['nim_id'], {})
        result.append({
            'nim_id': c['nim_id'],
            'name': s.get('name_id', 'Unknown'),
            'department': s.get('department_name', ''),
            'points': c['points'],
        })
    return jsonify(result)


@app.route('/api/tasks/<task_id>/contributors', methods=['PUT'])
@login_required
def update_task_contributors(task_id):
    """Update contributors for a task. Expects JSON array [{nim_id, points}, ...]."""
    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({'error': 'Expected a JSON array'}), 400

    rows = []
    for item in data:
        nim = str(item.get('nim_id', '')).strip()
        pts = float(item.get('points', 0))
        if nim:
            rows.append({'nim_id': nim, 'points': pts})

    _write_task_contributors(task_id, rows)
    return jsonify({'message': f'Saved {len(rows)} contributors for task {task_id}'}), 200


# ── Export ────────────────────────────────────────────

@app.route('/api/export/csv')
@login_required
def export_csv():
    """Download student_data.csv."""
    _ensure_csv()
    return send_file(STUDENT_CSV, as_attachment=True, download_name='student_data.csv')


@app.route('/api/export/sql')
@login_required
def export_sql():
    """Download student_data.sql."""
    _write_sql()
    return send_file(STUDENT_SQL, as_attachment=True, download_name='student_data.sql')


@app.route('/api/export/sheets', methods=['POST'])
@login_required
def export_sheets():
    """Send student_data.csv to Google Sheets via Web App URL."""
    _ensure_csv()
    try:
        with open(STUDENT_CSV, 'r', encoding='utf-8') as f:
            csv_string = f.read()

        response = requests.post(WEB_APP_URL, data={'csv_data': csv_string})

        if response.status_code == 200:
            return jsonify({'message': 'Data sent to Google Sheets successfully!'}), 200
        else:
            err_msg = response.text
            if '<html' in err_msg.lower():
                err_msg = "Google Apps Script URL returned an HTML error page. Please check the URL and deployment settings."
            return jsonify({'error': f'Failed to send: {err_msg}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Run ──────────────────────────────────────────────
if __name__ == '__main__':
    _ensure_csv()
    _ensure_task_csv()
    app.run(debug=True, port=5000)

