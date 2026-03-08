"""
KPI Dashboard — Flask Backend
International Office Student Registration & Task Management
"""

import os
import io
import csv
import json
import datetime
import functools
import requests
from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
# IMPORTANT: In a serverless environment like Vercel, os.urandom() will reset the secret key 
# on every function invocation, logging users out immediately. We use a static fallback.
app.secret_key = os.environ.get('SECRET_KEY', 'default-static-secret-key-for-dev-only')

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

# ── Google Sheets API URL ────────────────────────────
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxsaxXPZo4spsrn1SGP9ViluzsVeniAYlOsMpeCD6a-gGlNH-QRUhjsJO64GV3J4csx2A/exec"

# Column headers (used for CSV export generation)
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


# ── Google Sheets API Helper ────────────────────────

def _sheets_request(action, data=None):
    """Send a POST request to the Google Apps Script web app."""
    payload = {'action': action}
    if data is not None:
        payload['data'] = data
    try:
        response = requests.post(
            WEB_APP_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        # Google Apps Script may redirect (302) — requests follows by default
        result = response.json()
        if not result.get('success'):
            raise Exception(result.get('error', 'Unknown error from Sheets API'))
        return result
    except requests.exceptions.RequestException as e:
        raise Exception(f'Failed to connect to Google Sheets: {str(e)}')


# ── Student Helpers ──────────────────────────────────

def _read_students():
    """Return list of student dicts from Google Sheets."""
    result = _sheets_request('getStudents')
    students = []
    for row in result.get('data', []):
        try:
            row['department_id'] = int(row.get('department_id', 0))
        except (ValueError, TypeError):
            row['department_id'] = 0
        row['department_name'] = DEPARTMENTS.get(row['department_id'], '')
        try:
            row['score'] = float(row.get('score', 0))
        except (ValueError, TypeError):
            row['score'] = 0.0
        if not row.get('password'):
            row['password'] = generate_password_hash(row.get('nim_id', ''))
        students.append(row)
    return students


def _write_students(students):
    """Save the entire student list to Google Sheets."""
    rows = []
    for s in students:
        rows.append({
            'name_id': s.get('name_id', ''),
            'email_id': s.get('email_id', ''),
            'department_id': str(s.get('department_id', '')),
            'nim_id': s.get('nim_id', ''),
            'score': str(s.get('score', 0)),
            'job_id_list': s.get('job_id_list', ''),
            'password': s.get('password', '')
        })
    _sheets_request('saveStudents', rows)


def _append_student(name_id, email_id, department_id, nim_id):
    """Add a new student to Google Sheets."""
    students = _read_students()
    default_pw = generate_password_hash(nim_id)
    students.append({
        'name_id': name_id,
        'email_id': email_id,
        'department_id': department_id,
        'nim_id': nim_id,
        'score': 0,
        'job_id_list': '',
        'password': default_pw
    })
    _write_students(students)


def _nim_exists(nim_id):
    """Check if a NIM already exists."""
    students = _read_students()
    return any(s['nim_id'] == nim_id for s in students)


# ── Task Helpers ─────────────────────────────────────

def _read_tasks():
    """Return list of task dicts from Google Sheets."""
    result = _sheets_request('getTasks')
    tasks = []
    for row in result.get('data', []):
        try:
            row['type_id'] = int(row.get('type_id', 0))
        except (ValueError, TypeError):
            row['type_id'] = 0
        try:
            row['status_id'] = int(row.get('status_id', 0))
        except (ValueError, TypeError):
            row['status_id'] = 0
        row['type_name'] = TASK_TYPES.get(row['type_id'], '')
        row['status_name'] = TASK_STATUSES.get(row['status_id'], '')
        tasks.append(row)
    return tasks


def _write_tasks(tasks):
    """Save the entire task list to Google Sheets."""
    rows = []
    for t in tasks:
        rows.append({
            'task_id': str(t.get('task_id', '')),
            'task_name': str(t.get('task_name', '')),
            'type_id': str(t.get('type_id', '')),
            'start_date': str(t.get('start_date', '')),
            'end_date': str(t.get('end_date', '')),
            'status_id': str(t.get('status_id', '')),
            'pic': str(t.get('pic', '')),
            'related_links': str(t.get('related_links', '')),
            'description': str(t.get('description', '')),
        })
    _sheets_request('saveTasks', rows)


def _generate_task_id(type_id):
    """Generate a unique task ID: YYYYMMDD-{type}-{seq}."""
    today = datetime.date.today().strftime('%Y%m%d')
    tasks = _read_tasks()
    prefix = f"{today}-{type_id}-"
    existing = [t['task_id'] for t in tasks if t['task_id'].startswith(prefix)]
    seq = len(existing) + 1
    return f"{prefix}{seq:03d}"


def _append_task(task_id, task_name, type_id, start_date, end_date, status_id, pic, related_links, description):
    """Add a new task to Google Sheets."""
    tasks = _read_tasks()
    tasks.append({
        'task_id': task_id,
        'task_name': task_name,
        'type_id': type_id,
        'start_date': start_date,
        'end_date': end_date,
        'status_id': status_id,
        'pic': pic,
        'related_links': related_links,
        'description': description
    })
    _write_tasks(tasks)


def _update_tasks(tasks):
    """Rewrite entire task list in Google Sheets."""
    _write_tasks(tasks)


# ── Contributor Helpers ──────────────────────────────

def _read_all_contributors():
    """Return all contributor rows from Google Sheets."""
    result = _sheets_request('getContributors')
    rows = []
    for row in result.get('data', []):
        try:
            row['points'] = float(row.get('points', 0))
        except (ValueError, TypeError):
            row['points'] = 0.0
        rows.append(row)
    return rows


def _write_all_contributors(rows):
    """Save all contributor rows to Google Sheets."""
    data = []
    for r in rows:
        data.append({
            'task_id': str(r.get('task_id', '')),
            'nim_id': str(r.get('nim_id', '')),
            'points': str(r.get('points', 0))
        })
    _sheets_request('saveContributors', data)


def _read_task_contributors(task_id):
    """Return list of contributor dicts for a given task."""
    all_rows = _read_all_contributors()
    return [r for r in all_rows if r['task_id'] == task_id]


def _write_task_contributors(task_id, rows):
    """Rewrite contributors for a specific task. Keeps other tasks' rows intact."""
    all_rows = _read_all_contributors()
    # Remove existing rows for this task
    all_rows = [r for r in all_rows if r['task_id'] != task_id]
    # Add new rows for this task
    for r in rows:
        all_rows.append({'task_id': task_id, 'nim_id': r['nim_id'], 'points': r.get('points', 0)})
    _write_all_contributors(all_rows)


def _update_student_selection(nim_id, selected_task_ids):
    """Update the student's task list in both student_data and task_contributors."""
    students = _read_students()
    student = next((s for s in students if s['nim_id'] == nim_id), None)
    if not student:
        return False

    old_task_ids = set(student.get('job_id_list', '').split(';')) if student.get('job_id_list') else set()
    old_task_ids = {t for t in old_task_ids if t.strip()}
    new_task_ids = set(selected_task_ids)

    student['job_id_list'] = ';'.join(new_task_ids)
    _write_students(students)

    added_tasks = new_task_ids - old_task_ids
    removed_tasks = old_task_ids - new_task_ids

    if added_tasks or removed_tasks:
        all_rows = _read_all_contributors()
        # Remove student from unselected tasks
        all_rows = [r for r in all_rows if not (r['nim_id'] == nim_id and r['task_id'] in removed_tasks)]
        # Add student to newly selected tasks
        for tid in added_tasks:
            all_rows.append({'task_id': tid, 'nim_id': nim_id, 'points': 0})
        _write_all_contributors(all_rows)

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
@login_required
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
    top_overall = max(students, key=lambda s: s['score']) if students else None

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
    """Rewrite the entire student list from the provided JSON array."""
    data = request.get_json()
    if not data or 'students' not in data:
        return jsonify({'error': 'Invalid request body'}), 400
    _write_students(data['students'])
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
    available_tasks = [t for t in tasks if t['status_id'] in (1, 2, 3)]
    
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
    """Generate and download student_data.csv from Google Sheets data."""
    students = _read_students()
    output = io.StringIO()
    writer = csv.writer(output)
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
    csv_content = output.getvalue()
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=student_data.csv'}
    )


@app.route('/api/export/sql')
@login_required
def export_sql():
    """Generate and download student_data.sql from Google Sheets data."""
    students = _read_students()
    lines = ['-- Student Data INSERT statements\n']
    lines.append(f'-- Generated on {datetime.datetime.now().isoformat()}\n\n')
    for s in students:
        name = s['name_id'].replace("'", "''")
        email = s.get('email_id', '').replace("'", "''")
        nim = s['nim_id'].replace("'", "''")
        job = s.get('job_id_list', '').replace("'", "''")
        pwd = s.get('password', '').replace("'", "''")
        lines.append(
            f"INSERT INTO student_data (name_id, email_id, department_id, nim_id, score, job_id_list, password) "
            f"VALUES ('{name}', '{email}', {s['department_id']}, '{nim}', {s['score']}, '{job}', '{pwd}');\n"
        )
    sql_content = ''.join(lines)
    return Response(
        sql_content,
        mimetype='text/sql',
        headers={'Content-Disposition': 'attachment; filename=student_data.sql'}
    )


@app.route('/api/export/sheets', methods=['POST'])
@login_required
def export_sheets():
    """Data is already in Google Sheets — this is now a no-op confirmation."""
    return jsonify({'message': 'Data is already synced with Google Sheets!'}), 200


# ── Run ──────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, port=5000)
