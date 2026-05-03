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
import firebase_admin
from firebase_admin import credentials, db, auth
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect, CSRFError



load_dotenv()

app = Flask(__name__)
secret_key = os.environ.get('SECRET_KEY')
if not secret_key:
    raise RuntimeError('SECRET_KEY must be set in the environment')
app.secret_key = secret_key

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="memory://",
    # On Vercel (serverless), rate limiting state is per-instance and resets on cold start.
    # This is acceptable for basic abuse prevention.
    enabled=True
)
csrf = CSRFProtect(app)

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'CSRF token missing or invalid'}), 400
    return redirect(url_for('login'))

@app.after_request
def set_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:;"
    )
    return response

# Firebase Initialization
try:
    # Try to construct service account from individual environment variables
    # This is more reliable for Vercel's environment variable UI
    firebase_config = {
        "type": os.environ.get("FIREBASE_TYPE", "service_account"),
        "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
        "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
        "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
        "auth_uri": os.environ.get("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
        "token_uri": os.environ.get("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
        "auth_provider_x509_cert_url": os.environ.get("FIREBASE_AUTH_PROVIDER_X509_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
        "client_x509_cert_url": os.environ.get("FIREBASE_CLIENT_X509_CERT_URL"),
        "universe_domain": os.environ.get("FIREBASE_UNIVERSE_DOMAIN", "googleapis.com")
    }

    # Validation: Check if the most critical parts are missing
    if not firebase_config["private_key"] or not firebase_config["client_email"]:
        # Fallback for local development using the file path
        cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH", "./serviceAccountKey.json")
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
        else:
            raise RuntimeError(
                "Firebase configuration is incomplete. "
                "Ensure individual FIREBASE_* environment variables are set or "
                "serviceAccountKey.json exists."
            )
    else:
        cred = credentials.Certificate(firebase_config)

    firebase_admin.initialize_app(cred, {
        'databaseURL': os.environ.get('DATABASE_URL')
    })
    print("[Startup] Firebase Admin SDK initialized successfully.")
except Exception as _firebase_init_error:
    print(f"[Startup FATAL] Firebase initialization failed: {_firebase_init_error}")
    raise

# Reference to database
from firebase_admin import firestore
fs = firestore.client()


# ── Authentication ───────────────────────────────────
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH')
if not ADMIN_USERNAME or not ADMIN_PASSWORD_HASH:
    raise RuntimeError("Admin credentials not set in environment.")


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


# ── Health & Debug Routes ─────────────────────────────

@app.route('/api/health')
def health_check():
    """Quick health check — confirms the app started successfully."""
    try:
        # Ping Firestore to ensure the connection is alive
        fs.collection('students').limit(1).stream()
        return jsonify({'status': 'ok', 'firebase': 'connected'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/debug-env')
def debug_env():
    """Shows which critical environment variables are SET vs MISSING. Values are hidden."""
    keys = [
        'SECRET_KEY', 'ADMIN_USERNAME', 'ADMIN_PASSWORD_HASH',
        'FIREBASE_TYPE', 'FIREBASE_PROJECT_ID', 'FIREBASE_PRIVATE_KEY_ID',
        'FIREBASE_PRIVATE_KEY', 'FIREBASE_CLIENT_EMAIL', 'DATABASE_URL',
    ]
    result = {k: ('SET ✓' if os.environ.get(k) else 'MISSING ✗') for k in keys}
    pk = os.environ.get('FIREBASE_PRIVATE_KEY', '')
    result['FIREBASE_PRIVATE_KEY_len'] = len(pk)
    result['FIREBASE_PRIVATE_KEY_starts_with'] = pk[:30] if pk else 'N/A'
    return jsonify(result), 200



def _read_students():
    """Return list of student dicts from Firestore."""
    try:
        docs = fs.collection('students').stream()
        students = []
        for doc in docs:
            row = doc.to_dict()
            row['nim_id'] = row.get('nim_id', '')
            row['department_id'] = int(row.get('department_id', 0))
            row['department_name'] = DEPARTMENTS.get(row['department_id'], '')
            row['score'] = float(row.get('score', 0))
            row['job_id_list'] = row.get('job_id_list', '')
            if isinstance(row['job_id_list'], list): row['job_id_list'] = ';'.join(row['job_id_list'])
            if 'password' in row: del row['password']
            students.append(row)
        return students
    except Exception as e:
        print(f"[Firestore Error] _read_students failed: {e}")
        return []


def _write_students(students):
    """Save the entire student list to Firestore."""
    try:
        batch = fs.batch()
        for s in students:
            nim = s.get('nim_id')
            if not nim: continue
            docs = list(fs.collection('students').where('nim_id', '==', nim).limit(1).stream())
            doc_ref = docs[0].reference if docs else fs.collection('students').document()
            batch.set(doc_ref, {
                'name_id': s.get('name_id', ''),
                'email_id': s.get('email_id', ''),
                'department_id': int(s.get('department_id', 0)),
                'nim_id': nim,
                'score': float(s.get('score', 0)),
                'job_id_list': s.get('job_id_list', '').split(';') if isinstance(s.get('job_id_list', ''), str) else s.get('job_id_list', [])
            }, merge=True)
        batch.commit()
    except Exception as e:
        print(f"[Firestore Error] _write_students failed: {e}")
        raise


def _append_student(name_id, email_id, department_id, nim_id):
    """Add a new student to Firebase Auth and Firestore."""
    try:
        # Use NIM as the default password to match frontend expectations
        user = auth.create_user(email=email_id, password=nim_id)
        fs.collection('students').document(user.uid).set({
            'name_id': name_id,
            'email_id': email_id,
            'department_id': department_id,
            'nim_id': nim_id,
            'score': 0.0,
            'job_id_list': []
        })
        
        # Trigger Firebase email verification
        try:
            import httpx
            api_key = os.environ.get('FIREBASE_API_KEY')
            if api_key:
                login_url = f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}'
                login_res = httpx.post(login_url, json={'email': email_id, 'password': nim_id, 'returnSecureToken': True})
                if login_res.status_code == 200:
                    id_token = login_res.json().get('idToken')
                    verify_url = f'https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}'
                    httpx.post(verify_url, json={'requestType': 'VERIFY_EMAIL', 'idToken': id_token})
        except Exception as email_err:
            print(f"[Firebase Email Error] Failed to send verification email for {email_id}: {email_err}")

        return nim_id
    except Exception as e:
        print(f"[Firebase Error] _append_student failed: {e}")
        if 'email-already-exists' in str(e).lower():
            return None
        raise RuntimeError(f"Failed to create auth user for {email_id}: {e}") from e


def _nim_exists(nim_id):
    """Check if a NIM already exists."""
    try:
        docs = fs.collection('students').where('nim_id', '==', nim_id).limit(1).stream()
        return len(list(docs)) > 0
    except Exception as e:
        print(f"[Firestore Error] _nim_exists failed: {e}")
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
    """Return list of task dicts from Firestore."""
    try:
        docs = fs.collection('tasks').stream()
        tasks = []
        for doc in docs:
            row = doc.to_dict()
            row['type_id'] = int(row.get('type_id', 0))
            row['status_id'] = int(row.get('status_id', 0))
            row['start_date'] = row.get('start_date', '')
            row['end_date'] = row.get('end_date', '')
            row['type_name'] = TASK_TYPES.get(row['type_id'], '')
            row['status_name'] = TASK_STATUSES.get(row['status_id'], '')
            row['task_id'] = row.get('task_id', doc.id)
            tasks.append(row)
        return tasks
    except Exception as e:
        print(f"[Firestore Error] _read_tasks failed: {e}")
        return []


def _write_tasks(tasks):
    """Save the entire task list to Firestore."""
    try:
        batch = fs.batch()
        for t in tasks:
            tid = t.get('task_id')
            if not tid: continue
            docs = list(fs.collection('tasks').where('task_id', '==', tid).limit(1).stream())
            doc_ref = docs[0].reference if docs else fs.collection('tasks').document()
            batch.set(doc_ref, {
                'task_id': tid,
                'task_name': str(t.get('task_name', '')),
                'type_id': int(t.get('type_id', 0)),
                'start_date': _parse_date(t.get('start_date', '')),
                'end_date': _parse_date(t.get('end_date', '')),
                'status_id': int(t.get('status_id', 0)),
                'pic': str(t.get('pic', '')),
                'related_links': str(t.get('related_links', '')),
                'description': str(t.get('description', ''))
            }, merge=True)
        batch.commit()
    except Exception as e:
        print(f"[Firestore Error] _write_tasks failed: {e}")
        raise


def _generate_task_id(type_id):
    """Generate a unique task ID: YYYYMMDD-{type}-{seq}."""
    today = datetime.date.today().strftime('%Y%m%d')
    tasks = _read_tasks()
    prefix = f"{today}-{type_id}-"
    
    max_seq = 0
    for t in tasks:
        tid = t.get('task_id', '')
        if tid.startswith(prefix):
            try:
                seq_num = int(tid.split('-')[-1])
                if seq_num > max_seq:
                    max_seq = seq_num
            except (ValueError, IndexError):
                pass
                
    return f"{prefix}{max_seq + 1:03d}"


def _append_task(task_id, task_name, type_id, start_date, end_date, status_id, pic, related_links, description):
    """Add a new task to Firestore."""
    try:
        fs.collection('tasks').document().set({
            'task_id': task_id,
            'task_name': task_name,
            'type_id': int(type_id),
            'start_date': _parse_date(start_date),
            'end_date': _parse_date(end_date),
            'status_id': int(status_id),
            'pic': pic,
            'related_links': related_links,
            'description': description
        })
    except Exception as e:
        print(f"[Firestore Error] _append_task failed: {e}")
        raise


def _update_tasks(tasks):
    """Rewrite entire task list in Supabase."""
    _write_tasks(tasks)


# ── Contributor Helpers ──────────────────────────────

def _read_all_contributors():
    """Return all contributor rows from Firestore."""
    try:
        docs = fs.collection('contributions').stream()
        rows = []
        for doc in docs:
            row = doc.to_dict()
            row['points'] = float(row.get('points', 0))
            rows.append(row)
        return rows
    except Exception as e:
        print(f"[Firestore Error] _read_all_contributors failed: {e}")
        return []


def _write_all_contributors(rows):
    """Save all contributor rows to Firestore (destructive clear)."""
    try:
        # Delete all
        docs = fs.collection('contributions').stream()
        batch = fs.batch()
        for doc in docs: batch.delete(doc.reference)
        batch.commit()
        # Insert new
        for i in range(0, len(rows), 500):
            batch = fs.batch()
            for r in rows[i:i+500]:
                doc_ref = fs.collection('contributions').document()
                batch.set(doc_ref, {
                    'task_id': str(r.get('task_id', '')),
                    'nim_id': str(r.get('nim_id', '')),
                    'points': float(r.get('points', 0))
                })
            batch.commit()
    except Exception as e:
        print(f"[Firestore Error] _write_all_contributors failed: {e}")
        raise


def _read_task_contributors(task_id):
    """Return list of contributor dicts for a given task."""
    try:
        docs = fs.collection('contributions').where('task_id', '==', task_id).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"[Firestore Error] _read_task_contributors failed: {e}")
        return []


def _write_task_contributors(task_id, rows):
    """Rewrite contributors for a specific task."""
    try:
        # Delete existing
        docs = fs.collection('contributions').where('task_id', '==', task_id).stream()
        batch = fs.batch()
        for doc in docs: batch.delete(doc.reference)
        batch.commit()
        # Insert new
        batch = fs.batch()
        for r in rows:
            doc_ref = fs.collection('contributions').document()
            batch.set(doc_ref, {
                'task_id': task_id,
                'nim_id': r['nim_id'],
                'points': float(r.get('points', 0))
            })
        batch.commit()
    except Exception as e:
        print(f"[Firestore Error] _write_task_contributors failed: {e}")
        raise

def _sync_student_stats():
    """Recalculate both 'score' and 'job_id_list' for all students."""
    try:
        # Fetch tasks
        tasks = fs.collection('tasks').stream()
        finished_task_ids = {t.to_dict().get('task_id') for t in tasks if t.to_dict().get('status_id') == 7}
        # Fetch contribs
        contribs = fs.collection('contributions').stream()
        student_stats = {}
        for c in contribs:
            data = c.to_dict()
            nim = data.get('nim_id')
            tid = data.get('task_id')
            pts = float(data.get('points', 0.0))
            if not nim: continue
            if nim not in student_stats: student_stats[nim] = {'score': 0.0, 'job_list': []}
            student_stats[nim]['job_list'].append(tid)
            if tid in finished_task_ids: student_stats[nim]['score'] += pts
        # Update students
        students = fs.collection('students').stream()
        batch = fs.batch()
        for s in students:
            nim = s.to_dict().get('nim_id')
            stats = student_stats.get(nim, {'score': 0.0, 'job_list': []})
            new_score = float(stats['score'])
            new_jobs = ';'.join(filter(None, stats['job_list']))
            batch.update(s.reference, {'score': new_score, 'job_id_list': new_jobs})
        batch.commit()
    except Exception as e:
        print(f"[Firestore Error] _sync_student_stats failed: {e}")

def _update_student_selection(nim_id, selected_task_ids):
    """Update the student's task list in both students and contributions."""
    try:
        docs = list(fs.collection('students').where('nim_id', '==', nim_id).limit(1).stream())
        if not docs: return False
        student_ref = docs[0].reference
        student = docs[0].to_dict()
        old_task_ids = set(student.get('job_id_list', '').split(';')) if isinstance(student.get('job_id_list'), str) else set(student.get('job_id_list', []))
        old_task_ids = {t for t in old_task_ids if t.strip()}
        new_task_ids = set(selected_task_ids)
        student_ref.update({'job_id_list': ';'.join(new_task_ids)})
        added_tasks = new_task_ids - old_task_ids
        removed_tasks = old_task_ids - new_task_ids
        if removed_tasks:
            for tid in removed_tasks:
                cdocs = fs.collection('contributions').where('nim_id', '==', nim_id).where('task_id', '==', tid).stream()
                for c in cdocs: c.reference.delete()
        if added_tasks:
            for tid in added_tasks:
                fs.collection('contributions').document().set({'task_id': tid, 'nim_id': nim_id, 'points': 0.0})
        _sync_student_stats()
        return True
    except Exception as e:
        print(f"[Firestore Error] _update_student_selection failed: {e}")
        raise


# ── Auth Routes ──────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
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
                           students_json=students_json,
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
                           tasks_json=json.dumps(tasks, default=str),
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

    if errors:
        return jsonify({'errors': errors}), 422

    department_id = int(department_id)
    try:
        docs = list(fs.collection('students').where('nim_id', '==', nim_id).limit(1).stream())
        if docs:
            # Update existing student
            doc_ref = docs[0].reference
            uid = doc_ref.id
            doc_ref.update({
                'name_id': name_id,
                'email_id': email_id,
                'department_id': department_id
            })
            try:
                auth.update_user(uid, email=email_id)
            except Exception as e:
                print(f"[Firebase Error] Failed to update auth email for {uid}: {e}")
            message = f'{name_id} updated successfully!'
        else:
            # Create new student
            pwd = _append_student(name_id, email_id, department_id, nim_id)
            message = f'{name_id} registered successfully!'
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({
        'message': message,
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


@app.route('/api/students/bulk-import', methods=['POST'])
@login_required
def bulk_import_students():
    """Bulk upsert students. Expects JSON object with 'students' array."""
    data = request.get_json()
    if not data or 'students' not in data:
        return jsonify({'error': 'Invalid request body'}), 400
    
    results = {'added': 0, 'updated': 0, 'failed': 0, 'errors': []}
    processed_students = []

    for s in data['students']:
        name_id = str(s.get('name_id') or '').strip()
        email_id = str(s.get('email_id') or '').strip()
        department_id = int(s.get('department_id') or 1)
        nim_id = str(s.get('nim_id') or '').strip()

        if not nim_id or not name_id:
            results['failed'] += 1
            continue

        try:
            docs = list(fs.collection('students').where('nim_id', '==', nim_id).limit(1).stream())
            if docs:
                # Update
                doc_ref = docs[0].reference
                uid = doc_ref.id
                doc_ref.update({
                    'name_id': name_id,
                    'email_id': email_id,
                    'department_id': department_id
                })
                try:
                    auth.update_user(uid, email=email_id)
                except: pass
                results['updated'] += 1
                
                # Fetch full data to return to frontend
                updated_data = doc_ref.get().to_dict()
                updated_data['department_name'] = DEPARTMENTS.get(department_id, '')
                if 'password' in updated_data: del updated_data['password']
                processed_students.append(updated_data)
            else:
                # Create
                _append_student(name_id, email_id, department_id, nim_id)
                results['added'] += 1
                new_student = {
                    'name_id': name_id, 'email_id': email_id, 
                    'department_id': department_id, 'nim_id': nim_id,
                    'department_name': DEPARTMENTS.get(department_id, ''),
                    'score': 0, 'job_id_list': ''
                }
                processed_students.append(new_student)
        except Exception as e:
            print(f"[Bulk Import Error] NIM {nim_id}: {e}")
            results['failed'] += 1
            results['errors'].append(f"{nim_id}: {str(e)}")

    return jsonify({
        'message': f"Processed {len(data['students'])} students.",
        'results': results,
        'students': processed_students
    }), 200


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
        print(f"[Firestore Error] _write_students in save_all_students failed. Type: {type(exc).__name__}, Error: {exc}")
        return jsonify({'error': str(exc)}), 500
    return jsonify({'message': f'Saved {len(data["students"])} students'}), 200

@app.route('/api/student/auth', methods=['POST'])
@csrf.exempt
@limiter.limit("10 per minute")
def student_auth():
    """Authenticate a returning student by NIM and password (default NIM). Return student and available tasks."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request body'}), 400
        
    nim_id = (data.get('nim_id') or '').strip()
    password = (data.get('password') or '').strip()
    
    if not nim_id or not password:
        return jsonify({'error': 'NIM and password are required'}), 400
        
    try:
        docs = list(fs.collection('students').where('nim_id', '==', nim_id).limit(1).stream())
    except Exception as e:
        print(f"[Firestore Error] student_auth failed. Type: {type(e).__name__}, Error: {e}")
        return jsonify({'error': 'Database error'}), 500
        
    if not docs:
        return jsonify({'error': 'Student not found'}), 404
    student = docs[0].to_dict()
    email = student.get('email_id')
        
    try:
        import httpx
        payload = {'email': email, 'password': password, 'returnSecureToken': True}
        api_key = os.environ.get('FIREBASE_API_KEY')
        url = f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}'
        
        r = httpx.post(url, json=payload)
        
        if r.status_code != 200:
            error_data = r.json()
            error_message = error_data.get('error', {}).get('message', 'Unknown Firebase Auth error')
            return jsonify({'error': f"Authentication failed: {error_message}"}), 401
            
    except Exception as e:
        return jsonify({'error': f"Internal server error during auth: {str(e)}"}), 500
        
    tasks = _read_tasks()
    available_tasks = [t for t in tasks if t['status_id'] in (1, 2, 3)]
    
    student_profile = {k: v for k, v in student.items() if k != 'password'}
    if isinstance(student_profile.get('job_id_list'), list):
        student_profile['job_id_list'] = ';'.join(student_profile['job_id_list'])
    elif not student_profile.get('job_id_list'):
        student_profile['job_id_list'] = ''
        
    return jsonify({
        'student': student_profile,
        'tasks': available_tasks
    }), 200

@app.route('/api/student/change_password', methods=['POST'])
@csrf.exempt
@limiter.limit("5 per minute")
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
        
    try:
        docs = list(fs.collection('students').where('nim_id', '==', nim_id).limit(1).stream())
    except Exception as e:
        print(f"[Firestore Error] change_password lookup failed. Type: {type(e).__name__}, Error: {e}")
        return jsonify({'error': 'Database error'}), 500
        
    if not docs:
        return jsonify({'error': 'Student not found'}), 404
        
    student = docs[0].to_dict()
    email = student.get('email_id')
    
    try:
        
        import requests
        payload = {'email': email, 'password': old_password, 'returnSecureToken': True}
        api_key = os.environ.get('FIREBASE_API_KEY')
        r = requests.post(f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}', json=payload)
        if r.status_code != 200: raise Exception('Invalid password')
        if False:
            return jsonify({'error': 'Failed to establish an authenticated session'}), 401
        auth.update_user(user.uid, password=new_password)
    except Exception as e:
        return jsonify({'error': f'Incorrect current password or update failed: {e}'}), 401
    
    return jsonify({'message': 'Password updated successfully!'}), 200

@app.route('/api/student/tasks', methods=['POST'])
@csrf.exempt
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
        print(f"[Firestore Error] _append_task in create_task failed. Type: {type(exc).__name__}, Error: {exc}")
        return jsonify({'error': f'Failed to save task to Firestore: {exc}'}), 500

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
        docs = list(fs.collection('tasks').where('task_id', '==', task_id).limit(1).stream())
        if not docs:
            return jsonify({'error': 'Task not found'}), 404
            
        docs[0].reference.update({
            'task_name': task_name,
            'type_id': type_id,
            'start_date': _parse_date(start_date),
            'end_date': _parse_date(end_date),
            'status_id': status_id,
            'pic': pic,
            'related_links': related_links,
            'description': description
        })
        
        # Sync scores if status changed
        _sync_student_stats()
        
    except Exception as exc:
        print(f"[Firestore Error] update_task failed. Type: {type(exc).__name__}, Error: {exc}")
        return jsonify({'error': f'Failed to update task in Firestore: {exc}'}), 500

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
    """Delete a task and sync student stats."""
    # Check if task exists
    try:
        docs = list(fs.collection('tasks').where('task_id', '==', task_id).limit(1).stream())
        if not docs:
            return jsonify({'error': 'Task not found'}), 404
    except Exception as e:
        print(f"[Firestore Error] Task lookup in delete failed. Type: {type(e).__name__}, Error: {e}")
        return jsonify({'error': 'Database error'}), 500

    # Delete the task
    try:
        [doc.reference.delete() for doc in fs.collection('contributions').where('task_id', '==', task_id).stream()]
        [doc.reference.delete() for doc in fs.collection('tasks').where('task_id', '==', task_id).stream()]
        
        # Sync scores and job lists
        _sync_student_stats()
        
    except Exception as e:
        print(f"[Firestore Error] Task deletion failed. Type: {type(e).__name__}, Error: {e}")
        return jsonify({'error': 'Database error during deletion'}), 500
    
    return jsonify({'message': 'Task deleted successfully!'}), 200

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
        _sync_student_stats()
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
    
    def q(v):
        return str(v).replace("\\", "\\\\").replace("'", "\\'").replace("\x00", "")
        
    for s in students:
        lines.append(
            f"INSERT INTO student_database (name_id, email_id, department_id, nim_id, score, job_id_list) "
            f"VALUES ('{q(s.get('name_id', ''))}', '{q(s.get('email_id', ''))}', "
            f"{int(s.get('department_id', 0))}, '{q(s.get('nim_id', ''))}', "
            f"{float(s.get('score', 0))}, '{q(s.get('job_id_list', ''))}');\n"
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


# ── Enhanced Student Management APIs ─────────────────

@app.route('/api/students/<nim_id>', methods=['GET'])
@login_required
def get_student(nim_id):
    """Return a single student with their task contributions."""
    try:
        docs = list(fs.collection('students').where('nim_id', '==', nim_id).limit(1).stream())
        if not docs:
            return jsonify({'error': 'Student not found'}), 404
        student = docs[0].to_dict()
        student.pop('password', None)
        if isinstance(student.get('job_id_list'), list):
            student['job_id_list'] = ';'.join(student['job_id_list'])
        elif not student.get('job_id_list'):
            student['job_id_list'] = ''

        contribs = [doc.to_dict() for doc in fs.collection('contributions').where('nim_id', '==', nim_id).stream()]
        task_ids = [c['task_id'] for c in contribs]
        tasks_map = {}
        if task_ids:
            tasks_docs = [doc.to_dict() for doc in fs.collection('tasks').where('task_id', 'in', task_ids).stream()]
            tasks_map = {t['task_id']: t for t in tasks_docs}

        contributions = []
        for c in contribs:
            t = tasks_map.get(c['task_id'], {})
            contributions.append({
                'task_id': c['task_id'],
                'task_name': t.get('task_name', c['task_id']),
                'status_id': t.get('status_id', 0),
                'type_id': t.get('type_id', 0),
                'points': c['points'],
                'contribution_detail': c.get('contribution_detail', ''),
            })

        return jsonify({'student': student, 'contributions': contributions}), 200
    except Exception as e:
        print(f"[Firestore Error] get_student failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/students/<nim_id>', methods=['PUT'])
@login_required
def update_student(nim_id):
    """Update a single student's editable fields."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request body'}), 400
    try:
        allowed = ['name_id', 'email_id', 'department_id', 'score']
        update = {k: data[k] for k in allowed if k in data}
        if 'department_id' in update:
            update['department_id'] = int(update['department_id'])
        if 'score' in update:
            update['score'] = float(update['score'])
        [doc.reference.update(update) for doc in fs.collection('students').where('nim_id', '==', nim_id).stream()]
        return jsonify({'message': 'Student updated'}), 200
    except Exception as e:
        print(f"[Firestore Error] update_student failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/students/<nim_id>', methods=['DELETE'])
@login_required
def delete_student(nim_id):
    """Permanently delete a student from both Supabase Auth and the database."""
    try:
        docs = list(fs.collection('students').where('nim_id', '==', nim_id).limit(1).stream())
        if not docs:
            return jsonify({'error': 'Student not found'}), 404
        user_id = docs[0].id

        [doc.reference.delete() for doc in fs.collection('contributions').where('nim_id', '==', nim_id).stream()]
        [doc.reference.delete() for doc in fs.collection('students').where('nim_id', '==', nim_id).stream()]

        if user_id:
            try:
                auth.delete_user(user_id)
            except Exception as auth_e:
                print(f"[Auth] Could not delete auth user {user_id}: {auth_e}")

        _sync_student_stats()
        return jsonify({'message': f'Student {nim_id} deleted successfully'}), 200
    except Exception as e:
        print(f"[Firestore Error] delete_student failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/students/<nim_id>/reset-password', methods=['POST'])
@login_required
def reset_student_password(nim_id):
    """Send a Firebase password reset email to the student."""
    try:
        docs = list(fs.collection('students').where('nim_id', '==', nim_id).limit(1).stream())
        if not docs:
            return jsonify({'error': 'Student not found'}), 404
        
        student_data = docs[0].to_dict()
        email_id = student_data.get('email_id')
        if not email_id:
            return jsonify({'error': 'Student has no email address'}), 400

        import httpx
        api_key = os.environ.get('FIREBASE_API_KEY')
        if not api_key:
            return jsonify({'error': 'FIREBASE_API_KEY not configured'}), 500
            
        url = f'https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}'
        res = httpx.post(url, json={'requestType': 'PASSWORD_RESET', 'email': email_id})
        
        if res.status_code == 200:
            return jsonify({'message': 'Password reset email sent successfully'}), 200
        else:
            error_msg = res.json().get('error', {}).get('message', 'Unknown error')
            return jsonify({'error': f'Failed to send email: {error_msg}'}), 500
            
    except Exception as e:
        print(f"[Firestore Error] reset_student_password failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/students/sync-scores', methods=['POST'])
@login_required
def sync_scores():
    """Recalculate all student scores and job_id_lists from task_contributors."""
    try:
        _sync_student_stats()
        students = _read_students()
        return jsonify({'message': 'Scores synced successfully', 'students': students}), 200
    except Exception as e:
        print(f"[Supabase Error] sync_scores failed: {e}")
        return jsonify({'error': str(e)}), 500


# ── Run ──────────────────────────────────────────────
if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, port=int(os.environ.get('PORT', 5000)))