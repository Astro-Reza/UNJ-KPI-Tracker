# Firebase Integration Guide for UNJ-KPI-Tracker

## **YES, You Can Use Firebase!** ✅

Your Flask application currently uses **Supabase** as its backend database, but Firebase is absolutely compatible with Flask. Here's everything you need to know:

---

## **Current Stack Analysis**

- **Framework**: Flask 3.0.0 (Python)
- **Current DB**: Supabase (PostgreSQL-based)
- **Dependencies**: 
  - `supabase>=2.13.0` for database operations
  - `flask-limiter`, `flask-wtf` for security
  - `python-dotenv` for environment variables

---

## **Why Firebase Works with Flask**

Firebase Realtime Database and Cloud Firestore are REST/SDK-based services that work independently of your framework. Flask doesn't care which database backend you use—you just make HTTP requests to Firebase APIs.

**Advantages of Firebase:**
- ✅ Real-time database updates
- ✅ Built-in authentication (Firebase Auth)
- ✅ Automatic scaling
- ✅ Free tier available
- ✅ Easy integration with frontend (already has JS SDKs loaded in your templates)
- ✅ No server setup needed for database

---

## **Integration Steps**

### **Step 1: Install Firebase Admin SDK**

Replace Supabase dependency with Firebase:

```bash
pip install firebase-admin python-dotenv
```

Update `requirements.txt`:
```
Flask==3.0.0
Werkzeug==3.0.1
firebase-admin>=6.0.0
httpx>=0.28.1
python-dotenv==1.0.0
flask-limiter>=3.5.0
flask-wtf>=1.2.0
```

### **Step 2: Set Up Firebase Project**

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project (or use existing)
3. Download service account key:
   - Project Settings → Service Accounts → Generate New Private Key
   - Save as `serviceAccountKey.json` (add to `.gitignore`)

### **Step 3: Update `.env` File**

```env
SECRET_KEY=your-secret-key-here
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD_HASH=your_hashed_password
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_PATH=./serviceAccountKey.json
DATABASE_URL=https://your-project.firebaseio.com
```

### **Step 4: Replace Supabase Initialization in `app.py`**

**Before (Supabase):**
```python
from supabase import create_client, Client

url = os.environ.get("SUPABASE_URL", "")
key = os.environ.get("SUPABASE_KEY", "")
supabase = create_client(url, key) if url and key else None
```

**After (Firebase):**
```python
import firebase_admin
from firebase_admin import credentials, db, auth

# Initialize Firebase
cred = credentials.Certificate(os.environ.get("FIREBASE_CREDENTIALS_PATH"))
firebase_admin.initialize_app(cred, {
    'databaseURL': os.environ.get('DATABASE_URL')
})

# Reference to database
firebase_db = db.reference()
```

---

## **Key Code Changes Required**

### **1. User Registration & Authentication**

**Supabase:**
```python
supabase.auth.sign_up(email=email, password=password)
```

**Firebase:**
```python
from firebase_admin import auth

user = auth.create_user(email=email, password=password)
user_uid = user.uid
```

### **2. Data Operations**

**Supabase:**
```python
response = supabase.table('students').select('*').execute()
data = response.data

supabase.table('students').insert(new_student).execute()
```

**Firebase Realtime Database:**
```python
# Read
ref = db.reference('students')
students = ref.get().val()

# Create
ref.child('student_' + uid).set(new_student_data)

# Update
ref.child('student_' + uid).update(updated_data)

# Delete
ref.child('student_' + uid).delete()
```

**Firebase Firestore (Alternative, more structured):**
```python
from firebase_admin import firestore

fs = firestore.client()

# Read
docs = fs.collection('students').stream()
for doc in docs:
    print(doc.to_dict())

# Create
fs.collection('students').document(uid).set(new_student_data)

# Update
fs.collection('students').document(uid).update(updated_data)

# Delete
fs.collection('students').document(uid).delete()
```

### **3. Query Operations**

**Supabase:**
```python
response = supabase.table('students').select('*').eq('department_id', 1).execute()
```

**Firebase Firestore:**
```python
docs = fs.collection('students').where('department_id', '==', 1).stream()
```

---

## **Migration Strategy**

### **Option A: Complete Rewrite (Recommended for new projects)**
- Start fresh with Firebase SDK
- Migrate all database schemas
- Update all API endpoints

### **Option B: Gradual Migration**
- Keep Supabase for existing data
- Use Firebase for new features
- Sync data between databases during transition

### **Option C: Use Firebase SDK from Frontend**
- Keep Flask backend minimal
- Use Firebase JavaScript SDK directly in your HTML templates (you already have it loaded!)
- Use Flask only for authentication/authorization checks

---

## **Database Structure Example**

### **Firestore Collection Structure:**
```
students/
  ├── user_uid_1/
  │   ├── name: "John Doe"
  │   ├── email: "john@example.com"
  │   ├── department_id: 1
  │   ├── nim_id: "12345"
  │   └── score: 85
  │
  └── user_uid_2/
      └── ...

tasks/
  ├── task_id_1/
  │   ├── task_name: "Event Planning"
  │   ├── type_id: 2
  │   ├── status_id: 1
  │   └── ...
  │
  └── task_id_2/
      └── ...
```

---

## **Security Rules (Firestore)**

Add these rules in Firebase Console → Firestore → Rules:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Only authenticated users can read/write
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
    
    // Admin only operations
    match /admin/{document=**} {
      allow read, write: if request.auth.token.admin == true;
    }
  }
}
```

---

## **Complete Flask-Firebase Example**

```python
import firebase_admin
from firebase_admin import credentials, db, auth, firestore
from flask import Flask, request, jsonify, session
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# Initialize Firebase
cred = credentials.Certificate(os.environ.get('FIREBASE_CREDENTIALS_PATH'))
firebase_admin.initialize_app(cred, {
    'databaseURL': os.environ.get('DATABASE_URL')
})

fs = firestore.client()  # For Firestore
firebase_db = db.reference()  # For Realtime Database (alternative)

# ── Registration ───────────────────────────────────
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    try:
        # Create user in Firebase Auth
        user = auth.create_user(email=email, password=password)
        
        # Store additional user data in Firestore
        fs.collection('students').document(user.uid).set({
            'email': email,
            'name': data.get('name'),
            'department_id': data.get('department_id'),
            'nim_id': data.get('nim_id'),
            'created_at': firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({'message': 'User created successfully', 'uid': user.uid}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── Get All Students ───────────────────────────────────
@app.route('/api/students', methods=['GET'])
def get_students():
    try:
        docs = fs.collection('students').stream()
        students = [{'id': doc.id, **doc.to_dict()} for doc in docs]
        return jsonify(students), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── Get Student by ID ───────────────────────────────────
@app.route('/api/students/<uid>', methods=['GET'])
def get_student(uid):
    try:
        doc = fs.collection('students').document(uid).get()
        if doc.exists:
            return jsonify({'id': doc.id, **doc.to_dict()}), 200
        return jsonify({'error': 'Student not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── Update Student ───────────────────────────────────
@app.route('/api/students/<uid>', methods=['PUT'])
def update_student(uid):
    try:
        data = request.json
        fs.collection('students').document(uid).update(data)
        return jsonify({'message': 'Student updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── Delete Student ───────────────────────────────────
@app.route('/api/students/<uid>', methods=['DELETE'])
def delete_student(uid):
    try:
        # Delete from Firestore
        fs.collection('students').document(uid).delete()
        # Delete from Firebase Auth
        auth.delete_user(uid)
        return jsonify({'message': 'Student deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── Create Task ───────────────────────────────────
@app.route('/api/tasks', methods=['POST'])
def create_task():
    try:
        data = request.json
        task_ref = fs.collection('tasks').document()
        task_ref.set({
            **data,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        return jsonify({'message': 'Task created', 'id': task_ref.id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
```

---

## **Migration Checklist**

- [ ] Create Firebase project
- [ ] Download service account key
- [ ] Update `requirements.txt`
- [ ] Update `.env` with Firebase credentials
- [ ] Replace Supabase initialization in `app.py`
- [ ] Update all database queries (find & replace)
- [ ] Update authentication logic
- [ ] Test all API endpoints
- [ ] Update frontend to use Firebase SDK (optional)
- [ ] Set up Firestore security rules
- [ ] Deploy to production

---

## **Recommended Approach for Your Project**

Given that you have a Flask backend with HTML templates and static JS:

1. **Backend**: Replace Supabase with Firebase Admin SDK (what this guide covers)
2. **Frontend**: Keep Flask templates as-is, they'll work fine with REST API calls
3. **Authentication**: Use Firebase Auth for better security
4. **Database**: Use Firestore for better query flexibility than Realtime DB

This keeps your current architecture while gaining Firebase's advantages!

---

## **Resources**

- Firebase Admin SDK for Python: https://firebase.google.com/docs/database/admin/start
- Firestore Python Guide: https://cloud.google.com/firestore/docs/client/libraries
- Firebase Security Rules: https://firebase.google.com/docs/database/security
- Flask Integration Best Practices: https://medium.com/@dev.ravi.2495/firebase-with-flask-a2da91aa81f7