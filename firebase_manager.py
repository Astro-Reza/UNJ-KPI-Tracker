"""
Firebase Migration Helper
Provides utilities to migrate from Supabase to Firebase
"""

import firebase_admin
from firebase_admin import credentials, db, auth, firestore
import os
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

class FirebaseManager:
    """Manages all Firebase operations for KPI Tracker"""
    
    def __init__(self):
        """Initialize Firebase connection"""
        cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH')
        if not cred_path or not os.path.exists(cred_path):
            raise FileNotFoundError(f"Service account key not found at {cred_path}")
        
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': os.environ.get('DATABASE_URL')
            })
        except ValueError:
            # App already initialized
            pass
        
        self.fs = firestore.client()  # Firestore (recommended)
        self.db = db.reference()       # Realtime Database (alternative)
    
    # ══════════════════════════════════════════════════════════════
    # STUDENTS OPERATIONS
    # ══════════════════════════════════════════════════════════════
    
    def create_student(self, user_uid, student_data):
        """Create a new student document"""
        try:
            self.fs.collection('students').document(user_uid).set({
                'name': student_data.get('name'),
                'email': student_data.get('email'),
                'department_id': student_data.get('department_id'),
                'nim_id': student_data.get('nim_id'),
                'score': student_data.get('score', 0),
                'job_id_list': student_data.get('job_id_list', []),
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            return {'status': 'success', 'uid': user_uid}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_all_students(self):
        """Retrieve all students"""
        try:
            docs = self.fs.collection('students').stream()
            students = []
            for doc in docs:
                student = doc.to_dict()
                student['uid'] = doc.id
                students.append(student)
            return students
        except Exception as e:
            print(f"Error fetching students: {e}")
            return []
    
    def get_student(self, uid):
        """Get a specific student by UID"""
        try:
            doc = self.fs.collection('students').document(uid).get()
            if doc.exists:
                student = doc.to_dict()
                student['uid'] = doc.id
                return student
            return None
        except Exception as e:
            print(f"Error fetching student {uid}: {e}")
            return None
    
    def update_student(self, uid, update_data):
        """Update student information"""
        try:
            update_data['updated_at'] = firestore.SERVER_TIMESTAMP
            self.fs.collection('students').document(uid).update(update_data)
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def delete_student(self, uid):
        """Delete a student"""
        try:
            self.fs.collection('students').document(uid).delete()
            auth.delete_user(uid)
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_students_by_department(self, department_id):
        """Get students filtered by department"""
        try:
            docs = self.fs.collection('students').where(
                'department_id', '==', department_id
            ).stream()
            return [{'uid': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            print(f"Error fetching students by department: {e}")
            return []
    
    # ══════════════════════════════════════════════════════════════
    # TASKS OPERATIONS
    # ══════════════════════════════════════════════════════════════
    
    def create_task(self, task_data):
        """Create a new task"""
        try:
            task_ref = self.fs.collection('tasks').document()
            task_ref.set({
                'task_name': task_data.get('task_name'),
                'type_id': task_data.get('type_id'),
                'start_date': task_data.get('start_date'),
                'end_date': task_data.get('end_date'),
                'status_id': task_data.get('status_id', 1),
                'pic': task_data.get('pic'),
                'related_links': task_data.get('related_links', []),
                'description': task_data.get('description'),
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP
            })
            return {'status': 'success', 'task_id': task_ref.id}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_all_tasks(self):
        """Retrieve all tasks"""
        try:
            docs = self.fs.collection('tasks').stream()
            tasks = []
            for doc in docs:
                task = doc.to_dict()
                task['task_id'] = doc.id
                tasks.append(task)
            return tasks
        except Exception as e:
            print(f"Error fetching tasks: {e}")
            return []
    
    def get_task(self, task_id):
        """Get a specific task"""
        try:
            doc = self.fs.collection('tasks').document(task_id).get()
            if doc.exists:
                task = doc.to_dict()
                task['task_id'] = doc.id
                return task
            return None
        except Exception as e:
            print(f"Error fetching task: {e}")
            return None
    
    def update_task(self, task_id, update_data):
        """Update task information"""
        try:
            update_data['updated_at'] = firestore.SERVER_TIMESTAMP
            self.fs.collection('tasks').document(task_id).update(update_data)
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def delete_task(self, task_id):
        """Delete a task"""
        try:
            self.fs.collection('tasks').document(task_id).delete()
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_tasks_by_status(self, status_id):
        """Get tasks filtered by status"""
        try:
            docs = self.fs.collection('tasks').where(
                'status_id', '==', status_id
            ).stream()
            return [{'task_id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            print(f"Error fetching tasks by status: {e}")
            return []
    
    # ══════════════════════════════════════════════════════════════
    # CONTRIBUTIONS OPERATIONS
    # ══════════════════════════════════════════════════════════════
    
    def add_contribution(self, task_id, uid, points):
        """Add student contribution to a task"""
        try:
            contrib_ref = self.fs.collection('contributions').document()
            contrib_ref.set({
                'task_id': task_id,
                'uid': uid,
                'points': points,
                'created_at': firestore.SERVER_TIMESTAMP
            })
            return {'status': 'success', 'contribution_id': contrib_ref.id}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_contributions_for_task(self, task_id):
        """Get all contributions for a specific task"""
        try:
            docs = self.fs.collection('contributions').where(
                'task_id', '==', task_id
            ).stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            print(f"Error fetching contributions: {e}")
            return []
    
    def get_student_contributions(self, uid):
        """Get all contributions by a student"""
        try:
            docs = self.fs.collection('contributions').where(
                'uid', '==', uid
            ).stream()
            return [{'id': doc.id, **doc.to_dict()} for doc in docs]
        except Exception as e:
            print(f"Error fetching student contributions: {e}")
            return []
    
    # ══════════════════════════════════════════════════════════════
    # AUTHENTICATION OPERATIONS
    # ══════════════════════════════════════════════════════════════
    
    def create_user(self, email, password):
        """Create a new Firebase Auth user"""
        try:
            user = auth.create_user(email=email, password=password)
            return {'status': 'success', 'uid': user.uid}
        except auth.EmailAlreadyExistsError:
            return {'status': 'error', 'message': 'Email already exists'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def verify_user(self, email, password):
        """Verify user credentials (use Firebase Auth for this)"""
        # This requires the Requests library to call Firebase REST API
        # For production, use Google's identity toolkit
        return {'status': 'use_firebase_auth_client_sdk'}
    
    def delete_user(self, uid):
        """Delete a Firebase Auth user"""
        try:
            auth.delete_user(uid)
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_user(self, uid):
        """Get user information"""
        try:
            user = auth.get_user(uid)
            return {
                'uid': user.uid,
                'email': user.email,
                'email_verified': user.email_verified,
                'disabled': user.disabled
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    # ══════════════════════════════════════════════════════════════
    # BATCH OPERATIONS & UTILITIES
    # ══════════════════════════════════════════════════════════════
    
    def export_data(self, collection_name):
        """Export collection data as JSON"""
        try:
            docs = self.fs.collection(collection_name).stream()
            data = []
            for doc in docs:
                item = doc.to_dict()
                item['id'] = doc.id
                data.append(item)
            
            filename = f"{collection_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            return {'status': 'success', 'filename': filename, 'count': len(data)}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def import_data(self, collection_name, json_file):
        """Import data from JSON file into collection"""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            count = 0
            for item in data:
                doc_id = item.pop('id', None) or self.fs.collection(collection_name).document().id
                self.fs.collection(collection_name).document(doc_id).set(item)
                count += 1
            
            return {'status': 'success', 'imported': count}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_collection_stats(self, collection_name):
        """Get statistics about a collection"""
        try:
            docs = self.fs.collection(collection_name).stream()
            count = sum(1 for _ in docs)
            return {'collection': collection_name, 'document_count': count}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


# ══════════════════════════════════════════════════════════════
# EXAMPLE USAGE
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    # Initialize Firebase Manager
    fm = FirebaseManager()
    
    print("Firebase Migration Helper Initialized ✓")
    print("\nExample Usage:")
    print("-" * 50)
    
    # Example: Get all students
    # students = fm.get_all_students()
    # print(f"Found {len(students)} students")
    
    # Example: Create a student
    # result = fm.create_student('user123', {
    #     'name': 'John Doe',
    #     'email': 'john@example.com',
    #     'department_id': 1,
    #     'nim_id': '12345'
    # })
    # print(result)
    
    print("\nUse fm.get_all_students() to fetch students")
    print("Use fm.create_task() to create tasks")
    print("Use fm.add_contribution() to track contributions")
    print("\nFor detailed API, see FirebaseManager class methods above")