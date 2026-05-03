"""
KPI Dashboard — Flask Backend (Firebase Version)
International Office Student Registration & Task Management
Converted from Supabase to Firebase
"""

import os
import io
import csv
import json
import time
import datetime
import functools
from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth, firestore
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

limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")
csrf = CSRFProtect(app)

# ── Firebase Initialization ───────────────────────────────────
cred_path = os.environ.get("FIREBASE_CREDENTIALS_PATH")
if not cred_path or not os.path.exists(cred_path):
    raise RuntimeError(f'Firebase credentials not found at {cred_path}')

try:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'databaseURL': os.environ.get('DATABASE_URL')
    })
except ValueError:
    # App already initialized
    pass

fs = firestore.client()  # Firestore reference

# ── Security Configuration ───────────────────────────────────
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

# ── Authentication Configuration ───────────────────────────────────
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

# ── Constants ───────────────────────────────────────────────────────
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

# ══════════════════════════════════════════════════════════════
# AUTH ROUTES
# ══════════════════════════════════════════════════════════════

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    """Login with admin username and password"""
    if request.method == 'GET':
        return render_template('login.html')
    
    data = request.form if request.method == 'POST' else request.json
    username = data.get('username')
    password = data.get('password')
    
    if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
        session['logged_in'] = True
        session['username'] = username
        
        if request.method == 'POST' and request.headers.get('Content-Type') == 'application/json':
            return jsonify({'success': True, 'message': 'Logged in successfully'}), 200
        
        return redirect(url_for('home'))
    
    if request.method == 'POST' and request.headers.get('Content-Type') == 'application/json':
        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    
    return render_template('login.html', error='Invalid username or password'), 401

@app.route('/logout')
def logout():
    """Logout the user"""
    session.clear()
    return redirect(url_for('login'))

# ══════════════════════════════════════════════════════════════
# STUDENT OPERATIONS
# ══════════════════════════════════════════════════════════════

@app.route('/api/students', methods=['GET'])
@login_required
def get_students():
    """Retrieve all students from Firestore"""
    try:
        docs = fs.collection('students').stream()
        students = []
        for doc in docs:
            student = doc.to_dict()
            student['uid'] = doc.id
            students.append(student)
        return jsonify(students), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/students/<uid>', methods=['GET'])
@login_required
def get_student(uid):
    """Get a specific student"""
    try:
        doc = fs.collection('students').document(uid).get()
        if doc.exists:
            student = doc.to_dict()
            student['uid'] = doc.id
            return jsonify(student), 200
        return jsonify({'error': 'Student not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/students', methods=['POST'])
@login_required
def create_student():
    """Create a new student"""
    try:
        data = request.json
        
        # Create Firebase Auth user
        user = auth.create_user(
            email=data.get('email'),
            password=data.get('password', 'defaultPassword123')
        )
        
        # Store student data in Firestore
        fs.collection('students').document(user.uid).set({
            'name': data.get('name'),
            'email': data.get('email'),
            'department_id': data.get('department_id'),
            'nim_id': data.get('nim_id'),
            'score': data.get('score', 0),
            'job_id_list': data.get('job_id_list', []),
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({'message': 'Student created', 'uid': user.uid}), 201
    except auth.EmailAlreadyExistsError:
        return jsonify({'error': 'Email already exists'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/students/<uid>', methods=['PUT'])
@login_required
def update_student(uid):
    """Update student information"""
    try:
        data = request.json
        data['updated_at'] = firestore.SERVER_TIMESTAMP
        fs.collection('students').document(uid).update(data)
        return jsonify({'message': 'Student updated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/students/<uid>', methods=['DELETE'])
@login_required
def delete_student(uid):
    """Delete a student"""
    try:
        # Delete from Firestore
        fs.collection('students').document(uid).delete()
        # Delete from Firebase Auth
        auth.delete_user(uid)
        return jsonify({'message': 'Student deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ══════════════════════════════════════════════════════════════
# TASK OPERATIONS
# ══════════════════════════════════════════════════════════════

@app.route('/api/tasks', methods=['GET'])
@login_required
def get_tasks():
    """Retrieve all tasks"""
    try:
        docs = fs.collection('tasks').stream()
        tasks = []
        for doc in docs:
            task = doc.to_dict()
            task['task_id'] = doc.id
            tasks.append(task)
        return jsonify(tasks), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['GET'])
@login_required
def get_task(task_id):
    """Get a specific task"""
    try:
        doc = fs.collection('tasks').document(task_id).get()
        if doc.exists:
            task = doc.to_dict()
            task['task_id'] = doc.id
            return jsonify(task), 200
        return jsonify({'error': 'Task not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
@login_required
def create_task():
    """Create a new task"""
    try:
        data = request.json
        task_ref = fs.collection('tasks').document()
        
        task_ref.set({
            'task_name': data.get('task_name'),
            'type_id': data.get('type_id'),
            'start_date': data.get('start_date'),
            'end_date': data.get('end_date'),
            'status_id': data.get('status_id', 1),
            'pic': data.get('pic'),
            'related_links': data.get('related_links', []),
            'description': data.get('description'),
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({'message': 'Task created', 'task_id': task_ref.id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    """Update a task"""
    try:
        data = request.json
        data['updated_at'] = firestore.SERVER_TIMESTAMP
        fs.collection('tasks').document(task_id).update(data)
        return jsonify({'message': 'Task updated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    """Delete a task"""
    try:
        fs.collection('tasks').document(task_id).delete()
        return jsonify({'message': 'Task deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ══════════════════════════════════════════════════════════════
# CONTRIBUTION OPERATIONS
# ══════════════════════════════════════════════════════════════

@app.route('/api/contributions', methods=['POST'])
@login_required
def add_contribution():
    """Add a student contribution to a task"""
    try:
        data = request.json
        contrib_ref = fs.collection('contributions').document()
        
        contrib_ref.set({
            'task_id': data.get('task_id'),
            'uid': data.get('uid'),
            'points': data.get('points'),
            'created_at': firestore.SERVER_TIMESTAMP
        })
        
        # Update student score
        student_ref = fs.collection('students').document(data.get('uid'))
        student_doc = student_ref.get()
        if student_doc.exists:
            current_score = student_doc.get('score', 0)
            student_ref.update({'score': current_score + data.get('points', 0)})
        
        return jsonify({'message': 'Contribution added', 'contribution_id': contrib_ref.id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/contributions/task/<task_id>', methods=['GET'])
@login_required
def get_task_contributions(task_id):
    """Get contributions for a specific task"""
    try:
        docs = fs.collection('contributions').where('task_id', '==', task_id).stream()
        contributions = [{'id': doc.id, **doc.to_dict()} for doc in docs]
        return jsonify(contributions), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/contributions/student/<uid>', methods=['GET'])
@login_required
def get_student_contributions(uid):
    """Get contributions by a specific student"""
    try:
        docs = fs.collection('contributions').where('uid', '==', uid).stream()
        contributions = [{'id': doc.id, **doc.to_dict()} for doc in docs]
        return jsonify(contributions), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ══════════════════════════════════════════════════════════════
# EXPORT OPERATIONS
# ══════════════════════════════════════════════════════════════

@app.route('/api/export/students', methods=['GET'])
@login_required
def export_students():
    """Export students as CSV"""
    try:
        docs = fs.collection('students').stream()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(CSV_HEADER)
        
        for doc in docs:
            student = doc.to_dict()
            writer.writerow([
                student.get('name', ''),
                student.get('email', ''),
                student.get('department_id', ''),
                student.get('nim_id', ''),
                student.get('score', 0),
                ','.join(student.get('job_id_list', []))
            ])
        
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": "attachment;filename=students.csv"}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/tasks', methods=['GET'])
@login_required
def export_tasks():
    """Export tasks as CSV"""
    try:
        docs = fs.collection('tasks').stream()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(TASK_HEADER)
        
        for doc in docs:
            task = doc.to_dict()
            writer.writerow([
                doc.id,
                task.get('task_name', ''),
                task.get('type_id', ''),
                task.get('start_date', ''),
                task.get('end_date', ''),
                task.get('status_id', ''),
                task.get('pic', ''),
                ','.join(task.get('related_links', [])),
                task.get('description', '')
            ])
        
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-disposition": "attachment;filename=tasks.csv"}
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ══════════════════════════════════════════════════════════════
# PAGE ROUTES
# ══════════════════════════════════════════════════════════════

@app.route('/')
@login_required
def home():
    """Dashboard home page"""
    return render_template('home.html')

@app.route('/database')
@login_required
def database():
    """Database management page"""
    return render_template('database.html')

@app.route('/kanban')
@login_required
def kanban():
    """Kanban board page"""
    return render_template('kanban.html')

@app.route('/tasks')
@login_required
def tasks():
    """Task management page"""
    return render_template('task_database.html')

# ══════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ══════════════════════════════════════════════════════════════

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Internal server error'}), 500

# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    app.run(
        debug=os.environ.get('FLASK_ENV') == 'development',
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000))
    )