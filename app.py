"""
KPI Dashboard — Flask Backend
International Office Student Registration & Task Management
"""

import os
import io
import csv
import json
import time
import datetime
import functools
from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__)
secret_key = os.environ.get('SECRET_KEY')
if not secret_key:
    raise RuntimeError('SECRET_KEY must be set in the environment')
app.secret_key = secret_key

url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_KEY", "")

# Initialize Supabase client globally only if env vars are present (to prevent immediate crash if empty spot)
supabase: Client = None
if url and key:
    supabase = create_client(url, key)

# ── Authentication ───────────────────────────────────
ADMIN_USERNAME = 'admin-cis'
ADMIN_PASSWORD_HASH = 'scrypt:32768:8:1$mfjM50HyCVvDkVfl$025eee058823aff663e2fbee27051d162ea40fcb65019fd51adbb3ab93ec011ff6b174187ac2afb50a4b16736e7ba238fadf7551acd1ace2b987ff8d7b8aa851'


def login_required(f):
    """Decorator that redirects to /login if user is not authenticated."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Column headers (used for CSV export generation)
CSV_HEADER = ['name_id', 'email_id', 'department_id', 'nim_id', 'score', 'job_id_list']
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
TASK_STATUSES = {1: 'Planning', 2: 'In-Progress', 3: 'Execution', 4: 'Documentation', 5: 'Lecturer Review', 6: 'Done', 7: 'Finished'}


# ── Student 

def _read_students():
    """Return list of student dicts from Supabase."""
    if not supabase: return []
    try:
        result = supabase.table('student_database').select('*').execute()
    except Exception as e:
        print(f"[Supabase Error] _read_students failed. Type: {type(e).__name__}, Error: {e}")
        return []
    
    students = []
    for row in result.data:
        try:
            row['department_id'] = int(row.get('department_id', 0))
        except (ValueError, TypeError):
            row['department_id'] = 0
        row['department_name'] = DEPARTMENTS.get(row['department_id'], '')
        try:
            row['score'] = float(row.get('score', 0))
        except (ValueError, TypeError):
            row['score'] = 0.0
        if 'password' in row:
            del row['password']
        students.append(row)
    return students


def _write_students(students):
    """Save the entire student list to Supabase via Upsert."""
    if not supabase: return
    rows = []
    for s in students:
        rows.append({
            'name_id': s.get('name_id', ''),
            'email_id': s.get('email_id', ''),
            'department_id': int(s.get('department_id', 0)),
            'nim_id': s.get('nim_id', ''),
            'score': float(s.get('score', 0)),
            'job_id_list': s.get('job_id_list', '')
        })
    # Warning: Supabase upsert requires the primary key (nim_id) to match
    try:
        supabase.table('student_database').upsert(rows).execute()
    except Exception as e:
        print(f"[Supabase Error] _write_students failed. Type: {type(e).__name__}, Error: {e}")
        raise


def _append_student(name_id, email_id, department_id, nim_id):
    """Add a new student to Supabase."""
    if not supabase: return
    
    try:
        # Create user in Supabase Auth
        # The database trigger 'on_auth_user_created' in setup.sql will automatically 
        # create the entry in student_database when this succeeds.
        supabase.auth.admin.create_user({
            "email": email_id,
            "password": nim_id,
            "email_confirm": True,
            "user_metadata": {
                "nim_id": nim_id, 
                "name_id": name_id,
                "department_id": department_id
            }
        })
    except Exception as e:
        message = str(e).lower()
        print(f"[Supabase Error] _append_student failed. Type: {type(e).__name__}, Error: {e}")
        duplicate_markers = (
            'already registered',
            'already exists',
            'duplicate key',
            'user already exists',
        )
        if any(marker in message for marker in duplicate_markers):
            print(f"Auth user already exists for {email_id}: {e}")
            return
        raise RuntimeError(f"Failed to create auth user for {email_id}: {e}") from e


def _nim_exists(nim_id):
    """Check if a NIM already exists."""
    if not supabase: return False
    try:
        result = supabase.table('student_database').select('nim_id').eq('nim_id', nim_id).execute()
        return len(result.data) > 0
    except Exception as e:
        print(f"[Supabase Error] _nim_exists failed. Type: {type(e).__name__}, Error: {e}")
        return False


import re

def _parse_date(date_str):
    """Convert Google Sheets/JS date strings to YYYY-MM-DD."""
    if not date_str:
        return None
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
    try:
        # Try parsing "Thu Mar 05 2026 00:00:00 GMT+0700" to "Mar 05 2026"
        parts = date_str.split(' ')
        if len(parts) >= 4:
            dt_str = f"{parts[1]} {parts[2]} {parts[3]}"
            dt = datetime.datetime.strptime(dt_str, "%b %d %Y")
            return dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    if 'T' in date_str:
        return date_str.split('T')[0]
    return date_str

# ── Task Helpers ─────────────────────────────────────

def _read_tasks():
    """Return list of task dicts from Supabase."""
    if not supabase: return []
    try:
        result = supabase.table('task_data').select('*').execute()
    except Exception as e:
        print(f"[Supabase Error] _read_tasks failed. Type: {type(e).__name__}, Error: {e}")
        return []
        
    tasks = []
    for row in result.data:
        try:
            row['type_id'] = int(row.get('type_id', 0))
        except (ValueError, TypeError):
            row['type_id'] = 0
        try:
            row['status_id'] = int(row.get('status_id', 0))
        except (ValueError, TypeError):
            row['status_id'] = 0
            
        row['start_date'] = row.get('start_date', '') or ''
        row['end_date'] = row.get('end_date', '') or ''
        
        row['type_name'] = TASK_TYPES.get(row['type_id'], '')
        row['status_name'] = TASK_STATUSES.get(row['status_id'], '')
        tasks.append(row)
    return tasks


def _write_tasks(tasks):
    """Save the entire task list to Supabase."""
    if not supabase: return
    rows = []
    for t in tasks:
        rows.append({
            'task_id': str(t.get('task_id', '')),
            'task_name': str(t.get('task_name', '')),
            'type_id': int(t.get('type_id', 0)),
            'start_date': _parse_date(t.get('start_date', '')),
            'end_date': _parse_date(t.get('end_date', '')),
            'status_id': int(t.get('status_id', 0)),
            'pic': str(t.get('pic', '')),
            'related_links': str(t.get('related_links', '')),
            'description': str(t.get('description', '')),
        })
    try:
        supabase.table('task_data').upsert(rows).execute()
    except Exception as e:
        print(f"[Supabase Error] _write_tasks failed. Type: {type(e).__name__}, Error: {e}")
        raise


def _generate_task_id(type_id):
    """Generate a unique task ID: YYYYMMDD-{type}-{seq}."""
    today = datetime.date.today().strftime('%Y%m%d')
    tasks = _read_tasks()
    prefix = f"{today}-{type_id}-"
    existing = [t['task_id'] for t in tasks if t['task_id'].startswith(prefix)]
    seq = len(existing) + 1
    return f"{prefix}{seq:03d}"


def _append_task(task_id, task_name, type_id, start_date, end_date, status_id, pic, related_links, description):
    """Add a new task to Supabase."""
    if not supabase:
        raise RuntimeError('Supabase client is not initialized')

    try:
        return supabase.table('task_data').insert({
            'task_id': task_id,
            'task_name': task_name,
            'type_id': int(type_id),
            'start_date': _parse_date(start_date),
            'end_date': _parse_date(end_date),
            'status_id': int(status_id),
            'pic': pic,
            'related_links': related_links,
            'description': description
        }).execute()
    except Exception as e:
        print(f"[Supabase Error] _append_task failed. Type: {type(e).__name__}, Error: {e}")
        raise


def _update_tasks(tasks):
    """Rewrite entire task list in Supabase."""
    _write_tasks(tasks)


# ── Contributor Helpers ──────────────────────────────

def _read_all_contributors():
    """Return all contributor rows from Supabase."""
    if not supabase: return []
    try:
        result = supabase.table('task_contributors').select('*').execute()
    except Exception as e:
        print(f"[Supabase Error] _read_all_contributors failed. Type: {type(e).__name__}, Error: {e}")
        return []
        
    rows = []
    for row in result.data:
        try:
            row['points'] = float(row.get('points', 0))
        except (ValueError, TypeError):
            row['points'] = 0.0
        rows.append(row)
    return rows


def _write_all_contributors(rows):
    """Save all contributor rows to Supabase (destructive clear and insert since no PK present)."""
    if not supabase: return
    # This is inefficient in Postgres, but mimics the original list-overwrite approach
    # We first delete all then reinsert.
    try:
        supabase.table('task_contributors').delete().neq('id', -1).execute()
        data = []
        for r in rows:
            data.append({
                'task_id': str(r.get('task_id', '')),
                'nim_id': str(r.get('nim_id', '')),
                'points': float(r.get('points', 0))
            })
        if data:
            supabase.table('task_contributors').insert(data).execute()
    except Exception as e:
        print(f"[Supabase Error] _write_all_contributors failed. Type: {type(e).__name__}, Error: {e}")
        raise


def _read_task_contributors(task_id):
    """Return list of contributor dicts for a given task from Supabase."""
    if not supabase: return []
    try:
        result = supabase.table('task_contributors').select('*').eq('task_id', task_id).execute()
        return result.data
    except Exception as e:
        print(f"[Supabase Error] _read_task_contributors failed. Type: {type(e).__name__}, Error: {e}")
        return []


def _write_task_contributors(task_id, rows):
    """Rewrite contributors for a specific task."""
    if not supabase: return
    try:
        # 1. Delete existing for this task
        supabase.table('task_contributors').delete().eq('task_id', task_id).execute()
        # 2. Insert new rows
        data = []
        for r in rows:
            data.append({
                'task_id': task_id,
                'nim_id': r['nim_id'],
                'points': float(r.get('points', 0))
            })
        if data:
            supabase.table('task_contributors').insert(data).execute()
    except Exception as e:
        print(f"[Supabase Error] _write_task_contributors failed. Type: {type(e).__name__}, Error: {e}")
        raise


def _update_student_selection(nim_id, selected_task_ids):
    """Update the student's task list in both student_data and task_contributors."""
    if not supabase: return False
    
    try:
        # Fetch student
        res_student = supabase.table('student_database').select('*').eq('nim_id', nim_id).execute()
        if not res_student.data:
            return False
        student = res_student.data[0]

        old_task_ids = set(student.get('job_id_list', '').split(';')) if student.get('job_id_list') else set()
        old_task_ids = {t for t in old_task_ids if t.strip()}
        new_task_ids = set(selected_task_ids)

        student['job_id_list'] = ';'.join(new_task_ids)
        
        # Update student record
        supabase.table('student_database').update({'job_id_list': student['job_id_list']}).eq('nim_id', nim_id).execute()

        added_tasks = new_task_ids - old_task_ids
        removed_tasks = old_task_ids - new_task_ids

        if removed_tasks:
            # Remove student from unselected tasks
            supabase.table('task_contributors').delete().eq('nim_id', nim_id).in_('task_id', list(removed_tasks)).execute()
            
        if added_tasks:
            # Add student to newly selected tasks
            new_contribs = [{'task_id': tid, 'nim_id': nim_id, 'points': 0.0} for tid in added_tasks]
            supabase.table('task_contributors').insert(new_contribs).execute()

        return True
    except Exception as e:
        print(f"[Supabase Error] _update_student_selection failed. Type: {type(e).__name__}, Error: {e}")
        raise


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

    # Publication tasks (type 1) for media log, excluding finished (7)
    media_log = [t for t in tasks if t['type_id'] == 1 and t['status_id'] != 7]

    # Recently viewed = all tasks, most recent first, excluding finished (7)
    recent_tasks = [t for t in reversed(tasks) if t['status_id'] != 7]

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


@app.route('/api/dashboard')
@login_required
def api_dashboard():
    """Return all dashboard data as JSON for AJAX partial reloads."""
    tasks = _read_tasks()
    students = _read_students()

    for task in tasks:
        tid = task['task_id']
        contributors = [s['name_id'] for s in students if tid in s.get('job_id_list', '').split(';')]
        task['contributor_count'] = len(contributors)
        task['contributors_list'] = contributors

    ongoing_projects = [t for t in tasks if t['type_id'] in (2, 3) and t['status_id'] in (2, 3)]
    upcoming_projects = [t for t in tasks if t['type_id'] in (2, 3) and t['status_id'] == 1]
    media_log = [t for t in tasks if t['type_id'] == 1 and t['status_id'] != 7]
    recent_tasks = [t for t in reversed(tasks) if t['status_id'] != 7]

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

    # Serialise top_overall (remove password)
    top_data = None
    if top_overall:
        top_data = {'name_id': top_overall['name_id'], 'score': int(top_overall['score'])}

    return jsonify({
        'recent_tasks': recent_tasks,
        'ongoing_projects': ongoing_projects,
        'upcoming_projects': upcoming_projects,
        'media_log': media_log,
        'top_overall': top_data,
        'dept_leaders': dept_leaders,
    })


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
                           students_json=json.dumps(students),
                           dept_counts=dept_counts,
                           avg_score=avg_score,
                           top_score=top_score)


@app.route('/database/tasks')
@login_required
def task_database_page():
    tasks = _read_tasks()
    status_counts = {}
    for t in tasks:
        status_counts[t.get('status_id', 0)] = status_counts.get(t.get('status_id', 0), 0) + 1
    
    return render_template('task_database.html',
                           tasks=tasks,
                           tasks_json=json.dumps(tasks),
                           status_counts=status_counts)


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
    try:
        _append_student(name_id, email_id, department_id, nim_id)
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 500

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
    try:
        _write_students(data['students'])
    except Exception as exc:
        print(f"[Supabase Error] _write_students in save_all_students failed. Type: {type(exc).__name__}, Error: {exc}")
        return jsonify({'error': str(exc)}), 500
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
        
    if not supabase: return jsonify({'error': 'DB not initialized'}), 500
    try:
        res = supabase.table('student_database').select('*').eq('nim_id', nim_id).execute()
    except Exception as e:
        print(f"[Supabase Error] student_auth failed. Type: {type(e).__name__}, Error: {e}")
        return jsonify({'error': 'Database error'}), 500
        
    if not res.data:
        return jsonify({'error': 'Student not found'}), 404
    student = res.data[0]
    email = student.get('email_id')
        
    try:
        temp_client = create_client(url, key)
        auth_res = temp_client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e:
        return jsonify({'error': 'Incorrect password or authentication failed'}), 401
        
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
        
    if not supabase: return jsonify({'error': 'DB not initialized'}), 500
    try:
        res = supabase.table('student_database').select('*').eq('nim_id', nim_id).execute()
    except Exception as e:
        print(f"[Supabase Error] change_password lookup failed. Type: {type(e).__name__}, Error: {e}")
        return jsonify({'error': 'Database error'}), 500
        
    if not res.data:
        return jsonify({'error': 'Student not found'}), 404
        
    student = res.data[0]
    email = student.get('email_id')
    
    try:
        temp_client = create_client(url, key)
        auth_res = temp_client.auth.sign_in_with_password({"email": email, "password": old_password})
        if not auth_res or not getattr(auth_res, 'session', None) or not auth_res.session.access_token:
            return jsonify({'error': 'Failed to establish an authenticated session'}), 401
        temp_client.auth.update_user({'password': new_password})
    except Exception as e:
        return jsonify({'error': f'Incorrect current password or update failed: {e}'}), 401
    
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
    try:
        success = _update_student_selection(nim_id, task_ids)
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500

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

    try:
        _append_task(task_id, task_name, type_id, start_date, end_date, status_id, pic, related_links, description)
    except Exception as exc:
        print(f"[Supabase Error] _append_task in create_task failed. Type: {type(exc).__name__}, Error: {exc}")
        return jsonify({'error': f'Failed to save task to Supabase: {exc}'}), 500

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

    if not supabase:
        return jsonify({'error': 'Supabase client is not initialized'}), 500

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

    try:
        supabase.table('task_data').update({
            'task_name': task_name,
            'type_id': type_id,
            'start_date': _parse_date(start_date),
            'end_date': _parse_date(end_date),
            'status_id': status_id,
            'pic': pic,
            'related_links': related_links,
            'description': description
        }).eq('task_id', task_id).execute()
    except Exception as exc:
        print(f"[Supabase Error] update_task failed. Type: {type(exc).__name__}, Error: {exc}")
        return jsonify({'error': f'Failed to update task in Supabase: {exc}'}), 500

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


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    """Delete a task and remove all its contributor points from students."""
    if not supabase: return jsonify({'error': 'DB not initialized'}), 500
    
    # 1. Check if task exists
    try:
        task_res = supabase.table('task_data').select('*').eq('task_id', task_id).execute()
        if not task_res.data:
            return jsonify({'error': 'Task not found'}), 404

        # 2. Get task contributors to update student scores
        contributors_res = supabase.table('task_contributors').select('nim_id, points').eq('task_id', task_id).execute()
        task_contribs = contributors_res.data
    except Exception as e:
        print(f"[Supabase Error] Task lookup/contributors lookup failed in delete. Type: {type(e).__name__}, Error: {e}")
        return jsonify({'error': 'Database error'}), 500
    
    # 3. Update student records (score and job_id_list)
    if task_contribs:
        students = _read_students()
        updates = []
        for tc in task_contribs:
            nim_id = tc['nim_id']
            points = tc.get('points', 0.0)
            
            student = next((s for s in students if s['nim_id'] == nim_id), None)
            if student:
                try:
                    student['score'] -= float(points)
                except ValueError:
                    student['score'] = 0.0
                
                # Remove task_id from job_id_list
                job_list = student.get('job_id_list', '').split(';')
                if task_id in job_list:
                    job_list.remove(task_id)
                student['job_id_list'] = ';'.join(filter(None, job_list))
                updates.append({
                    'nim_id': student['nim_id'],
                    'score': student['score'],
                    'job_id_list': student['job_id_list']
                })
        
        for u in updates:
            try:
                supabase.table('student_database').update({'score': u['score'], 'job_id_list': u['job_id_list']}).eq('nim_id', u['nim_id']).execute()
            except Exception as e:
                print(f"[Supabase Error] student_database update in delete_task failed. Type: {type(e).__name__}, Error: {e}")

    # 4. Delete the task (task_contributors will cascade delete if database is configured to CASCADE, but we explicitly delete here for safety in case CASCADE isn't set up yet)
    try:
        supabase.table('task_contributors').delete().eq('task_id', task_id).execute()
        supabase.table('task_data').delete().eq('task_id', task_id).execute()
    except Exception as e:
        print(f"[Supabase Error] Task deletion failed. Type: {type(e).__name__}, Error: {e}")
        return jsonify({'error': 'Database error during deletion'}), 500
        
    return jsonify({'message': 'Task deleted successfully'}), 200


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

    try:
        _write_task_contributors(task_id, rows)
    except Exception as exc:
        print(f"[Supabase Error] _write_task_contributors in update_task_contributors failed. Type: {type(exc).__name__}, Error: {exc}")
        return jsonify({'error': str(exc)}), 500
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
    """Generate and download student_data.sql from Supabase data."""
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
            f"INSERT INTO student_database (name_id, email_id, department_id, nim_id, score, job_id_list, password) "
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
    app.run(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true', port=int(os.environ.get('PORT', 5000)))
