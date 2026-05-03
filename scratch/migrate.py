import ast
import os

with open('app.py', 'r', encoding='utf-8') as f:
    code = f.read()

lines = code.split('\n')

def replace_func(func_name, new_body_lines):
    global lines
    # parse AST
    tree = ast.parse('\n'.join(lines))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            start = node.lineno - 1
            # find end by looking at the next statement at the same level, or end of file
            end = node.end_lineno
            
            # Extract decorators if any
            decorators_count = len(node.decorator_list)
            if decorators_count > 0:
                start = node.decorator_list[0].lineno - 1

            # Replace lines
            lines = lines[:start] + new_body_lines + lines[end:]
            return True
    return False

# NEW FUNCTION DEFINITIONS
new_funcs = {
    '_read_students': [
        "def _read_students():",
        "    \"\"\"Return list of student dicts from Firestore.\"\"\"",
        "    try:",
        "        docs = fs.collection('students').stream()",
        "        students = []",
        "        for doc in docs:",
        "            row = doc.to_dict()",
        "            row['nim_id'] = row.get('nim_id', '')",
        "            row['department_id'] = int(row.get('department_id', 0))",
        "            row['department_name'] = DEPARTMENTS.get(row['department_id'], '')",
        "            row['score'] = float(row.get('score', 0))",
        "            row['job_id_list'] = row.get('job_id_list', '')",
        "            if isinstance(row['job_id_list'], list): row['job_id_list'] = ';'.join(row['job_id_list'])",
        "            if 'password' in row: del row['password']",
        "            students.append(row)",
        "        return students",
        "    except Exception as e:",
        "        print(f\"[Firestore Error] _read_students failed: {e}\")",
        "        return []"
    ],
    '_write_students': [
        "def _write_students(students):",
        "    \"\"\"Save the entire student list to Firestore.\"\"\"",
        "    try:",
        "        batch = fs.batch()",
        "        for s in students:",
        "            nim = s.get('nim_id')",
        "            if not nim: continue",
        "            docs = list(fs.collection('students').where('nim_id', '==', nim).limit(1).stream())",
        "            doc_ref = docs[0].reference if docs else fs.collection('students').document()",
        "            batch.set(doc_ref, {",
        "                'name_id': s.get('name_id', ''),",
        "                'email_id': s.get('email_id', ''),",
        "                'department_id': int(s.get('department_id', 0)),",
        "                'nim_id': nim,",
        "                'score': float(s.get('score', 0)),",
        "                'job_id_list': s.get('job_id_list', '').split(';') if isinstance(s.get('job_id_list', ''), str) else s.get('job_id_list', [])",
        "            }, merge=True)",
        "        batch.commit()",
        "    except Exception as e:",
        "        print(f\"[Firestore Error] _write_students failed: {e}\")",
        "        raise"
    ],
    '_append_student': [
        "def _append_student(name_id, email_id, department_id, nim_id):",
        "    \"\"\"Add a new student to Firebase Auth and Firestore.\"\"\"",
        "    import secrets",
        "    random_password = secrets.token_urlsafe(10)",
        "    try:",
        "        user = auth.create_user(email=email_id, password=random_password)",
        "        fs.collection('students').document(user.uid).set({",
        "            'name_id': name_id,",
        "            'email_id': email_id,",
        "            'department_id': department_id,",
        "            'nim_id': nim_id,",
        "            'score': 0.0,",
        "            'job_id_list': []",
        "        })",
        "        return random_password",
        "    except Exception as e:",
        "        print(f\"[Firebase Error] _append_student failed: {e}\")",
        "        if 'email-already-exists' in str(e).lower():",
        "            return None",
        "        raise RuntimeError(f\"Failed to create auth user for {email_id}: {e}\") from e"
    ],
    '_nim_exists': [
        "def _nim_exists(nim_id):",
        "    \"\"\"Check if a NIM already exists.\"\"\"",
        "    try:",
        "        docs = fs.collection('students').where('nim_id', '==', nim_id).limit(1).stream()",
        "        return len(list(docs)) > 0",
        "    except Exception as e:",
        "        print(f\"[Firestore Error] _nim_exists failed: {e}\")",
        "        return False"
    ],
    '_read_tasks': [
        "def _read_tasks():",
        "    \"\"\"Return list of task dicts from Firestore.\"\"\"",
        "    try:",
        "        docs = fs.collection('tasks').stream()",
        "        tasks = []",
        "        for doc in docs:",
        "            row = doc.to_dict()",
        "            row['type_id'] = int(row.get('type_id', 0))",
        "            row['status_id'] = int(row.get('status_id', 0))",
        "            row['start_date'] = row.get('start_date', '')",
        "            row['end_date'] = row.get('end_date', '')",
        "            row['type_name'] = TASK_TYPES.get(row['type_id'], '')",
        "            row['status_name'] = TASK_STATUSES.get(row['status_id'], '')",
        "            row['task_id'] = row.get('task_id', doc.id)",
        "            tasks.append(row)",
        "        return tasks",
        "    except Exception as e:",
        "        print(f\"[Firestore Error] _read_tasks failed: {e}\")",
        "        return []"
    ],
    '_write_tasks': [
        "def _write_tasks(tasks):",
        "    \"\"\"Save the entire task list to Firestore.\"\"\"",
        "    try:",
        "        batch = fs.batch()",
        "        for t in tasks:",
        "            tid = t.get('task_id')",
        "            if not tid: continue",
        "            docs = list(fs.collection('tasks').where('task_id', '==', tid).limit(1).stream())",
        "            doc_ref = docs[0].reference if docs else fs.collection('tasks').document()",
        "            batch.set(doc_ref, {",
        "                'task_id': tid,",
        "                'task_name': str(t.get('task_name', '')),",
        "                'type_id': int(t.get('type_id', 0)),",
        "                'start_date': _parse_date(t.get('start_date', '')),",
        "                'end_date': _parse_date(t.get('end_date', '')),",
        "                'status_id': int(t.get('status_id', 0)),",
        "                'pic': str(t.get('pic', '')),",
        "                'related_links': str(t.get('related_links', '')),",
        "                'description': str(t.get('description', ''))",
        "            }, merge=True)",
        "        batch.commit()",
        "    except Exception as e:",
        "        print(f\"[Firestore Error] _write_tasks failed: {e}\")",
        "        raise"
    ],
    '_append_task': [
        "def _append_task(task_id, task_name, type_id, start_date, end_date, status_id, pic, related_links, description):",
        "    \"\"\"Add a new task to Firestore.\"\"\"",
        "    try:",
        "        fs.collection('tasks').document().set({",
        "            'task_id': task_id,",
        "            'task_name': task_name,",
        "            'type_id': int(type_id),",
        "            'start_date': _parse_date(start_date),",
        "            'end_date': _parse_date(end_date),",
        "            'status_id': int(status_id),",
        "            'pic': pic,",
        "            'related_links': related_links,",
        "            'description': description",
        "        })",
        "    except Exception as e:",
        "        print(f\"[Firestore Error] _append_task failed: {e}\")",
        "        raise"
    ],
    '_read_all_contributors': [
        "def _read_all_contributors():",
        "    \"\"\"Return all contributor rows from Firestore.\"\"\"",
        "    try:",
        "        docs = fs.collection('contributions').stream()",
        "        rows = []",
        "        for doc in docs:",
        "            row = doc.to_dict()",
        "            row['points'] = float(row.get('points', 0))",
        "            rows.append(row)",
        "        return rows",
        "    except Exception as e:",
        "        print(f\"[Firestore Error] _read_all_contributors failed: {e}\")",
        "        return []"
    ],
    '_write_all_contributors': [
        "def _write_all_contributors(rows):",
        "    \"\"\"Save all contributor rows to Firestore (destructive clear).\"\"\"",
        "    try:",
        "        # Delete all",
        "        docs = fs.collection('contributions').stream()",
        "        batch = fs.batch()",
        "        for doc in docs: batch.delete(doc.reference)",
        "        batch.commit()",
        "        # Insert new",
        "        for i in range(0, len(rows), 500):",
        "            batch = fs.batch()",
        "            for r in rows[i:i+500]:",
        "                doc_ref = fs.collection('contributions').document()",
        "                batch.set(doc_ref, {",
        "                    'task_id': str(r.get('task_id', '')),",
        "                    'nim_id': str(r.get('nim_id', '')),",
        "                    'points': float(r.get('points', 0))",
        "                })",
        "            batch.commit()",
        "    except Exception as e:",
        "        print(f\"[Firestore Error] _write_all_contributors failed: {e}\")",
        "        raise"
    ],
    '_read_task_contributors': [
        "def _read_task_contributors(task_id):",
        "    \"\"\"Return list of contributor dicts for a given task.\"\"\"",
        "    try:",
        "        docs = fs.collection('contributions').where('task_id', '==', task_id).stream()",
        "        return [doc.to_dict() for doc in docs]",
        "    except Exception as e:",
        "        print(f\"[Firestore Error] _read_task_contributors failed: {e}\")",
        "        return []"
    ],
    '_write_task_contributors': [
        "def _write_task_contributors(task_id, rows):",
        "    \"\"\"Rewrite contributors for a specific task.\"\"\"",
        "    try:",
        "        # Delete existing",
        "        docs = fs.collection('contributions').where('task_id', '==', task_id).stream()",
        "        batch = fs.batch()",
        "        for doc in docs: batch.delete(doc.reference)",
        "        batch.commit()",
        "        # Insert new",
        "        batch = fs.batch()",
        "        for r in rows:",
        "            doc_ref = fs.collection('contributions').document()",
        "            batch.set(doc_ref, {",
        "                'task_id': task_id,",
        "                'nim_id': r['nim_id'],",
        "                'points': float(r.get('points', 0))",
        "            })",
        "        batch.commit()",
        "    except Exception as e:",
        "        print(f\"[Firestore Error] _write_task_contributors failed: {e}\")",
        "        raise"
    ],
    '_sync_student_stats': [
        "def _sync_student_stats():",
        "    \"\"\"Recalculate both 'score' and 'job_id_list' for all students.\"\"\"",
        "    try:",
        "        # Fetch tasks",
        "        tasks = fs.collection('tasks').stream()",
        "        finished_task_ids = {t.to_dict().get('task_id') for t in tasks if t.to_dict().get('status_id') == 7}",
        "        # Fetch contribs",
        "        contribs = fs.collection('contributions').stream()",
        "        student_stats = {}",
        "        for c in contribs:",
        "            data = c.to_dict()",
        "            nim = data.get('nim_id')",
        "            tid = data.get('task_id')",
        "            pts = float(data.get('points', 0.0))",
        "            if not nim: continue",
        "            if nim not in student_stats: student_stats[nim] = {'score': 0.0, 'job_list': []}",
        "            student_stats[nim]['job_list'].append(tid)",
        "            if tid in finished_task_ids: student_stats[nim]['score'] += pts",
        "        # Update students",
        "        students = fs.collection('students').stream()",
        "        batch = fs.batch()",
        "        for s in students:",
        "            nim = s.to_dict().get('nim_id')",
        "            stats = student_stats.get(nim, {'score': 0.0, 'job_list': []})",
        "            new_score = float(stats['score'])",
        "            new_jobs = ';'.join(filter(None, stats['job_list']))",
        "            batch.update(s.reference, {'score': new_score, 'job_id_list': new_jobs})",
        "        batch.commit()",
        "    except Exception as e:",
        "        print(f\"[Firestore Error] _sync_student_stats failed: {e}\")"
    ],
    '_update_student_selection': [
        "def _update_student_selection(nim_id, selected_task_ids):",
        "    \"\"\"Update the student's task list in both students and contributions.\"\"\"",
        "    try:",
        "        docs = list(fs.collection('students').where('nim_id', '==', nim_id).limit(1).stream())",
        "        if not docs: return False",
        "        student_ref = docs[0].reference",
        "        student = docs[0].to_dict()",
        "        old_task_ids = set(student.get('job_id_list', '').split(';')) if isinstance(student.get('job_id_list'), str) else set(student.get('job_id_list', []))",
        "        old_task_ids = {t for t in old_task_ids if t.strip()}",
        "        new_task_ids = set(selected_task_ids)",
        "        student_ref.update({'job_id_list': ';'.join(new_task_ids)})",
        "        added_tasks = new_task_ids - old_task_ids",
        "        removed_tasks = old_task_ids - new_task_ids",
        "        if removed_tasks:",
        "            for tid in removed_tasks:",
        "                cdocs = fs.collection('contributions').where('nim_id', '==', nim_id).where('task_id', '==', tid).stream()",
        "                for c in cdocs: c.reference.delete()",
        "        if added_tasks:",
        "            for tid in added_tasks:",
        "                fs.collection('contributions').document().set({'task_id': tid, 'nim_id': nim_id, 'points': 0.0})",
        "        _sync_student_stats()",
        "        return True",
        "    except Exception as e:",
        "        print(f\"[Firestore Error] _update_student_selection failed: {e}\")",
        "        raise"
    ]
}

for name, body in new_funcs.items():
    replace_func(name, body)

# Inline replacements for endpoints that use supabase directly
import re
new_code = '\n'.join(lines)

# Replace supabase auth stuff
new_code = re.sub(r"supabase\.table\('student_database'\)\.select\('\*'\)\.eq\('nim_id', nim_id\)\.execute\(\)", "type('obj', (object,), {'data': [doc.to_dict() for doc in fs.collection('students').where('nim_id', '==', nim_id).limit(1).stream()]})()", new_code)
new_code = re.sub(r"supabase\.table\('task_data'\)\.select\('\*'\)\.eq\('task_id', task_id\)\.execute\(\)", "type('obj', (object,), {'data': [doc.to_dict() for doc in fs.collection('tasks').where('task_id', '==', task_id).limit(1).stream()]})()", new_code)
new_code = re.sub(r"supabase\.table\('task_contributors'\)\.delete\(\)\.eq\('task_id', task_id\)\.execute\(\)", "[doc.reference.delete() for doc in fs.collection('contributions').where('task_id', '==', task_id).stream()]", new_code)
new_code = re.sub(r"supabase\.table\('task_data'\)\.delete\(\)\.eq\('task_id', task_id\)\.execute\(\)", "[doc.reference.delete() for doc in fs.collection('tasks').where('task_id', '==', task_id).stream()]", new_code)
new_code = re.sub(r"supabase\.table\('task_data'\)\.update\((.*?)\)\.eq\('task_id', task_id\)\.execute\(\)", r"[doc.reference.update(\1) for doc in fs.collection('tasks').where('task_id', '==', task_id).stream()]", new_code)
new_code = re.sub(r"supabase\.table\('student_database'\)\.update\((.*?)\)\.eq\('nim_id', nim_id\)\.execute\(\)", r"[doc.reference.update(\1) for doc in fs.collection('students').where('nim_id', '==', nim_id).stream()]", new_code)
new_code = re.sub(r"supabase\.table\('student_database'\)\.delete\(\)\.eq\('nim_id', nim_id\)\.execute\(\)", r"[doc.reference.delete() for doc in fs.collection('students').where('nim_id', '==', nim_id).stream()]", new_code)
new_code = re.sub(r"supabase\.table\('task_contributors'\)\.delete\(\)\.eq\('nim_id', nim_id\)\.execute\(\)", r"[doc.reference.delete() for doc in fs.collection('contributions').where('nim_id', '==', nim_id).stream()]", new_code)

new_code = re.sub(r"supabase\.table\('student_database'\)\.select\('user_id'\)\.eq\('nim_id', nim_id\)\.execute\(\)", r"type('obj', (object,), {'data': [{'user_id': doc.id} for doc in fs.collection('students').where('nim_id', '==', nim_id).limit(1).stream()]})()", new_code)
new_code = re.sub(r"supabase\.table\('task_contributors'\)\.select\('task_id, points, contribution_detail'\)\.eq\('nim_id', nim_id\)\.execute\(\)", r"type('obj', (object,), {'data': [doc.to_dict() for doc in fs.collection('contributions').where('nim_id', '==', nim_id).stream()]})()", new_code)
new_code = re.sub(r"supabase\.table\('task_data'\)\.select\('task_id, task_name, status_id, type_id'\)\.in_\('task_id', task_ids\)\.execute\(\)", r"type('obj', (object,), {'data': [doc.to_dict() for doc in fs.collection('tasks').where('task_id', 'in', task_ids).stream()]})() if task_ids else type('obj', (object,), {'data': []})()", new_code)

new_code = re.sub(r"supabase\.auth\.admin\.delete_user\(user_id\)", "auth.delete_user(user_id)", new_code)
new_code = re.sub(r"supabase\.auth\.admin\.update_user_by_id\(user_id, \{'password': new_password\}\)", "auth.update_user(user_id, password=new_password)", new_code)

# Replace sign in with password manually because Firebase admin SDK doesn't do sign_in
new_code = new_code.replace("temp_client = create_client(url, key)", "")
new_code = new_code.replace("auth_res = temp_client.auth.sign_in_with_password({\"email\": email, \"password\": password})", "import requests\n        payload = {'email': email, 'password': password, 'returnSecureToken': True}\n        api_key = os.environ.get('FIREBASE_API_KEY')\n        r = requests.post(f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}', json=payload)\n        if r.status_code != 200: raise Exception('Invalid password')")
new_code = new_code.replace("auth_res = temp_client.auth.sign_in_with_password({\"email\": email, \"password\": old_password})", "import requests\n        payload = {'email': email, 'password': old_password, 'returnSecureToken': True}\n        api_key = os.environ.get('FIREBASE_API_KEY')\n        r = requests.post(f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}', json=payload)\n        if r.status_code != 200: raise Exception('Invalid password')")
new_code = new_code.replace("if not auth_res or not getattr(auth_res, 'session', None) or not auth_res.session.access_token:", "if False:")
new_code = new_code.replace("temp_client.auth.update_user({'password': new_password})", "auth.update_user(user.uid, password=new_password)") # uid from earlier

new_code = new_code.replace("if not supabase:", "if False:")
new_code = new_code.replace("supabase =", "fs = firestore.client() # ")
new_code = new_code.replace("firebase_db = db.reference()", "from firebase_admin import firestore\nfs = firestore.client()")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_code)
