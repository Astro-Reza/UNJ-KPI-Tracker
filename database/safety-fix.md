The system has several real vulnerabilities. Here's the full breakdown with fixes:

---

**Critical**

**1 — XSS (Cross-Site Scripting) in JavaScript templates**

Multiple JS files interpolate server data directly into `innerHTML` without sanitisation. For example in `home.js`:
```js
tbody.innerHTML = contribs.map(c => `<td>${c.name}</td><td>${c.nim_id}</td>`)
```
If a student's name or NIM contains `<script>alert(1)</script>`, it executes in any admin's browser. Fix: use `textContent` for plain values, or escape before inserting:
```js
function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}
// then: `<td>${esc(c.name)}</td>`
```

**2 — SQL injection in `export_sql()`**

The `export_sql` route hand-builds INSERT strings and only escapes single quotes:
```python
name = s['name_id'].replace("'", "''")  # insufficient
f"VALUES ('{name}', ..."
```
A student named `Robert"); DROP TABLE student_database;--` would produce broken or malicious SQL. Since this is just a download for backup purposes, the simplest fix is to use `csv.writer` to export as CSV instead, or use parameterised query generation via a library rather than string concatenation.

---

**High**

**3 — `/api/register` requires no authentication** — covered in the previous audit, still not fixed. Add `@login_required`.

**4 — No rate limiting on auth endpoints**

`/login`, `/api/student/auth`, and `/api/student/change_password` allow unlimited password attempts. An attacker can brute-force any account. Fix with `flask-limiter`:
```python
from flask_limiter import Limiter
limiter = Limiter(app, key_func=lambda: request.remote_addr)

@app.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login(): ...
```

**5 — No CSRF protection**

State-changing routes (`/api/students/save-all`, `/api/tasks`, etc.) accept POST requests with no CSRF token. A malicious page on another site could trigger these in an admin's browser. Fix with `flask-wtf`:
```python
from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect(app)
```
Then exempt the student-facing API endpoints that use their own auth (`/api/student/auth`, etc.) with `@csrf.exempt`.

**6 — NIM used as default password**

Student IDs are typically printed on ID cards, shared in class groups, and publicly guessable. Every newly registered student is immediately vulnerable until they change their password — and there's no mechanism forcing them to. At minimum, generate a random initial password and communicate it out-of-band.

---

**Medium**

**7 — No security headers** — add via an `after_request` hook:
```python
@app.after_request
def set_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response
```

**8 — Session cookies not hardened** — add to your app config:
```python
app.config.update(
    SESSION_COOKIE_SECURE=True,    # HTTPS only
    SESSION_COOKIE_HTTPONLY=True,  # no JS access
    SESSION_COOKIE_SAMESITE='Lax', # CSRF protection
)
```

**9 — `debug=True` in production** — change to `app.run(debug=False)` or better, use an environment variable: `debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'`.

**10 — Admin credentials in source code** — the hardcoded `ADMIN_USERNAME` and password hash are visible in your git history forever. Move them to `.env`:
```python
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH')
```

The two most urgent things to fix are the XSS (item 1) and the open registration endpoint (item 3) — those are exploitable by anyone who can reach your app right now.


# BELOW IS THE FIX REQUIRED TO BE DONE

Given the scope of all 10 fixes across `app.py`, `home.js`, `database.js`, and `task_database.js`, I couldn't complete all the changes in one turn. Here's the full actionable breakdown for each issue:

---

**Fix 1 — XSS in `home.js`, `database.js`, `task_database.js`**

Add this helper at the top of each JS file:
```js
function esc(str) {
    const d = document.createElement('div');
    d.textContent = str == null ? '' : String(str);
    return d.innerHTML;
}
```
Then replace every `${someValue}` inside template literals that go into `innerHTML` with `${esc(someValue)}`. The affected spots are: `buildJobCardHTML()` in `home.js` (task_name, start_date, etc.), the contributors `tbody.innerHTML` in `home.js`, the `projectsContainer.innerHTML` map in `home.js`, the `renderTable` tbody map in `database.js` (name_id, email_id, nim_id), and the `renderTable` tbody map in `task_database.js` (task_name, pic).

Note that `registration.js` already has an `escapeHtml()` function and uses it correctly — no change needed there.

**Fix 2 — SQL injection in `export_sql()`**

Replace the `password` column (which doesn't exist in `_read_students()` anyway since it's stripped) and use proper escaping:
```python
def q(v):
    return str(v).replace("\\", "\\\\").replace("'", "\\'").replace("\x00", "")
lines.append(
    f"INSERT INTO student_database (name_id, email_id, department_id, nim_id, score, job_id_list) "
    f"VALUES ('{q(s['name_id'])}', '{q(s.get('email_id',''))}', "
    f"{int(s['department_id'])}, '{q(s['nim_id'])}', "
    f"{float(s.get('score', 0))}, '{q(s.get('job_id_list',''))}');\n"
)
```

**Fix 3 — `/api/register` open to the public**

Add `@login_required` decorator. Note: `database.js` calls this endpoint from the admin panel's "Add Student" modal, so this is fine — it only needs to work when an admin is logged in.

**Fix 4 — Rate limiting**

Add to `requirements.txt`: `flask-limiter>=3.5.0`

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")
```
Then decorate:
```python
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login(): ...

@app.route('/api/student/auth', methods=['POST'])
@limiter.limit("10 per minute")
def student_auth(): ...

@app.route('/api/student/change_password', methods=['POST'])
@limiter.limit("5 per minute")
def change_password(): ...
```

**Fix 5 — CSRF**

Add `flask-wtf>=1.2.0` to `requirements.txt`. In `app.py`:
```python
from flask_wtf.csrf import CSRFProtect, CSRFError

csrf = CSRFProtect(app)

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'CSRF token missing or invalid'}), 400
    return redirect(url_for('login'))
```
Exempt the three student-facing endpoints (they use Supabase auth, not Flask session):
```python
@app.route('/api/student/auth', methods=['POST'])
@csrf.exempt
...
@app.route('/api/student/change_password', methods=['POST'])
@csrf.exempt
...
@app.route('/api/student/tasks', methods=['POST'])
@csrf.exempt
...
```
Add `{{ csrf_token() }}` meta tag in your base template (or add the header automatically via JS fetch interceptor for admin pages).

**Fix 6 — Default NIM password**

Generate a random password instead of using the NIM:
```python
import secrets
random_password = secrets.token_urlsafe(10)
supabase.auth.admin.create_user({
    "email": email_id,
    "password": random_password,
    ...
})
# Then email or display random_password to the admin who registered them
```

**Fix 7 & 8 — Security headers + hardened cookies**

```python
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

@app.after_request
def set_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:;"
    )
    return response
```

**Fix 9 — debug mode**

```python
if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(debug=debug_mode, port=5000)
```
In `.env`, only set `FLASK_DEBUG=true` on your local machine — never on the server.

**Fix 10 — Admin credentials out of source**

Move to `.env`:
```
ADMIN_USERNAME=admin-cis
ADMIN_PASSWORD_HASH=scrypt:32768:8:1$mfjM...
```
In `app.py`:
```python
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH')
if not ADMIN_USERNAME or not ADMIN_PASSWORD_HASH:
    raise RuntimeError("Admin credentials not set in environment.")
```
To generate a new hash: `python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('your_password'))"`.