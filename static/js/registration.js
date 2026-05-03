/* ============================================
   Registration Page — Logic
   ============================================ */

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-app.js";
import { getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, sendEmailVerification, updatePassword, EmailAuthProvider, reauthenticateWithCredential, signOut } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-auth.js";

// 1. DOM references (Keep these at the top)
const authTabs = document.getElementById('authTabs');
const tabRegister = document.getElementById('tabRegister');
const tabSelectTasks = document.getElementById('tabSelectTasks');
const form = document.getElementById('registrationForm');
const loginForm = document.getElementById('loginForm');
const taskSelectionContainer = document.getElementById('taskSelectionContainer');
const nameInput = document.getElementById('nameInput');
const emailInput = document.getElementById('emailInput');
const deptSelect = document.getElementById('departmentSelect');
const nimInput = document.getElementById('nimInput');
const loginEmailInput = document.getElementById('loginEmailInput');
const loginPasswordInput = document.getElementById('loginPasswordInput');
const profileName = document.getElementById('profileName');
const profileNim = document.getElementById('profileNim');
const profileDept = document.getElementById('profileDept');
const tasksList = document.getElementById('tasksList');
const btnSaveTasks = document.getElementById('btnSaveTasks');
const btnBackToLogin = document.getElementById('btnBackToLogin');
const btnToggleChangePassword = document.getElementById('btnToggleChangePassword');
const changePasswordForm = document.getElementById('changePasswordForm');
const oldPasswordInput = document.getElementById('oldPasswordInput');
const newPasswordInput = document.getElementById('newPasswordInput');
const confirmPasswordInput = document.getElementById('confirmPasswordInput');
const btnCancelChangePassword = document.getElementById('btnCancelChangePassword');
const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toastMessage');

// 3. Firebase Initialization

// 3. Firebase Initialization

let firebaseAuth;
try {
    if (!window.firebaseConfig || !window.firebaseConfig.apiKey) {
        throw new Error("Firebase configuration is missing. Check your .env file.");
    }
    const app = initializeApp(window.firebaseConfig);
    firebaseAuth = getAuth(app);
    console.log("Firebase initialized successfully");
} catch (err) {
    console.error("Firebase Initialization Error:", err);
    // We don't showToast here yet because it might be too early, 
    // but the error will be in the F12 console.
}

// State
let currentStudentId = null;

// Department mapping
const DEPARTMENTS = {
    1: 'Head of International Office',
    2: 'Secretary',
    3: 'Administration',
    4: 'Media & Design',
    5: 'Hospitality',
    6: 'Community Impact'
};

// ── Form Submission → POST to backend ──
form.addEventListener('submit', async function (e) {
    e.preventDefault();
    console.log("Register button clicked!");
    
    if (!firebaseAuth) { 
        console.error("Firebase Auth is not initialized!");
        showToast("Authentication system not ready. Check console for errors."); 
        return; 
    }
    
    const btn = document.getElementById('btnSubmit');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = "Processing...";

    clearErrors();

    const name = nameInput.value.trim();
    const email = emailInput.value.trim();
    const dept = parseInt(deptSelect.value);
    const nim = nimInput.value.trim();

    console.log("Inputs gathered:", { name, email, dept, nim });

    // Client-side validation
    let valid = true;

    if (!name) {
        showError('nameGroup', 'Student name is required');
        valid = false;
    }
    if (!email) {
        showError('emailGroup', 'Email address is required');
        valid = false;
    }
    if (!dept) {
        showError('deptGroup', 'Please select a department');
        valid = false;
    }
    if (!nim) {
        showError('nimGroup', 'Student ID (NIM) is required');
        valid = false;
    }

    if (!valid) return;

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    try {
        console.log("Attempting to create Firebase account...");
        // 1. Create user in Firebase Auth using client SDK
        const userCredential = await createUserWithEmailAndPassword(firebaseAuth, email, nim);
        const user = userCredential.user;
        console.log("Firebase account created:", user.uid);
        
        console.log("Attempting to send verification email...");
        // 2. Send verification email
        await sendEmailVerification(user);
        console.log("Verification email sent successfully!");
        
        // 3. Get the ID token
        const idToken = await user.getIdToken();
        console.log("ID Token retrieved.");

        console.log("Saving student data to backend Firestore (Pre-verification allowed)...");
        const res = await fetch('/api/student/register', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${idToken}`,
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                name_id: name,
                department_id: dept,
                nim_id: nim
            })
        });

        const data = await res.json();
        console.log("Backend response:", data);

        if (!res.ok) {
            // Special case: ignore 'email not verified' error during INITIAL registration
            // because we WANT to save their data now, but they can't login yet.
            if (data.code !== 'email_not_verified') {
                if (data.errors) {
                    if (data.errors.name_id) showError('nameGroup', data.errors.name_id);
                    if (data.errors.department_id) showError('deptGroup', data.errors.department_id);
                    if (data.errors.nim_id) showError('nimGroup', data.errors.nim_id);
                } else {
                    showToast(data.error || 'Registration failed');
                }
                return;
            }
        }

        // Success
        form.reset();
        nameInput.focus();
        showToast(`✓ ${name} registered! Check your email for a verification link.`);

    } catch (err) {
        console.error('Registration Error Detail:', err);
        let msg = 'Network error — please try again';
        if (err.code === 'auth/email-already-in-use') msg = 'Email is already registered.';
        if (err.code === 'auth/weak-password') msg = 'Password (NIM) must be at least 6 characters.';
        if (err.code === 'auth/network-request-failed') msg = 'Firebase connection failed. Check your internet.';
        showToast(`${msg} (${err.code || err.message})`);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
});

// ── Funnel 2: Login returning student ──
loginForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    if (!firebaseAuth) { showToast("Authentication system not ready."); return; }
    clearErrors();

    const email = loginEmailInput.value.trim();
    const password = loginPasswordInput.value.trim();

    let valid = true;
    if (!email) {
        showError('loginEmailGroup', 'Email Address is required');
        valid = false;
    }
    if (!password) {
        showError('loginPasswordGroup', 'Password is required');
        valid = false;
    }

    if (!valid) return;

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    try {
        // 1. Authenticate with Firebase Client SDK
        const userCredential = await signInWithEmailAndPassword(firebaseAuth, email, password);
        const user = userCredential.user;

        // 2. CHECK EMAIL VERIFICATION
        if (!user.emailVerified) {
            console.warn("User attempted login without verification.");
            showToast("Please verify your email before logging in. Check your inbox!");
            
            // Optionally resend email automatically if they keep trying
            await sendEmailVerification(user);
            
            // Force sign out so they don't stay in a half-logged-in state
            await signOut(firebaseAuth);
            return;
        }

        const idToken = await user.getIdToken();
        console.log("Login successful, token retrieved.");
        const res = await fetch('/api/student/me', {
            method: 'GET',
            headers: { 
                'Authorization': `Bearer ${idToken}`,
                'X-CSRFToken': csrfToken
            }
        });

        const data = await res.json();

        if (!res.ok) {
            showToast(data.error || 'Failed to fetch student data');
            return;
        }

        // Setup Task Selection View
        loginForm.classList.add('hidden');
        authTabs.classList.add('hidden');
        taskSelectionContainer.classList.remove('hidden');

        const student = data.student;
        currentStudentId = student.nim_id;

        profileName.textContent = student.name_id;
        profileNim.textContent = `NIM: ${student.nim_id}`;
        profileDept.textContent = `Dept: ${DEPARTMENTS[student.department_id] || student.department_id}`;

        const studentTaskIds = student.job_id_list ? student.job_id_list.split(';').filter(x => x) : [];
        renderTasks(data.tasks, studentTaskIds);

    } catch (err) {
        console.error('Login error detail:', err);
        let msg = 'Network error — please try again';
        if (err.code === 'auth/invalid-credential') msg = 'Invalid email or password.';
        if (err.code === 'auth/user-not-found') msg = 'No account found with this email.';
        if (err.code === 'auth/network-request-failed') msg = 'Firebase connection failed. Check your internet.';
        showToast(`${msg} (${err.code || err.message})`);
    }
});

// ── Render Tasks ──
function renderTasks(tasks, selectedIds) {
    tasksList.innerHTML = '';

    if (!tasks || tasks.length === 0) {
        tasksList.innerHTML = '<p style="color:rgba(255,255,255,0.6); padding:10px;">No available tasks at the moment.</p>';
        return;
    }

    tasks.forEach(task => {
        const isChecked = selectedIds.includes(task.task_id);
        const label = document.createElement('label');
        label.className = 'task-checkbox-item';
        
        label.innerHTML = `
            <input type="checkbox" value="${task.task_id}" ${isChecked ? 'checked' : ''}>
            <div class="task-details">
                <span class="task-name">${escapeHtml(task.task_name)}</span>
                <span class="task-meta">${task.type_name} | ${task.start_date}</span>
            </div>
        `;
        tasksList.appendChild(label);
    });
}

// ── Save Selected Tasks ──
btnSaveTasks.addEventListener('click', async () => {
    if (!currentStudentId) return;

    const checkboxes = tasksList.querySelectorAll('input[type="checkbox"]');
    const selectedTaskIds = Array.from(checkboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value);

    // Disable button to prevent double-click
    btnSaveTasks.disabled = true;
    btnSaveTasks.textContent = 'Saving...';

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    try {
        const idToken = await firebaseAuth.currentUser.getIdToken();
        const res = await fetch('/api/student/tasks', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${idToken}`,
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                nim_id: currentStudentId,
                task_ids: selectedTaskIds
            })
        });

        const data = await res.json();

        if (!res.ok) {
            showToast(data.error || 'Failed to save tasks');
        } else {
            showToast('✓ Tasks saved successfully!');
        }
    } catch (err) {
        console.error('Save error:', err);
        showToast('Network error — please try again');
    } finally {
        btnSaveTasks.disabled = false;
        btnSaveTasks.textContent = 'Save Tasks';
    }
});

btnBackToLogin.addEventListener('click', () => {
    if (firebaseAuth.currentUser) {
        signOut(firebaseAuth);
    }
    taskSelectionContainer.classList.add('hidden');
    loginForm.classList.remove('hidden');
    authTabs.classList.remove('hidden');
    currentStudentId = null;
    loginEmailInput.value = '';
    loginPasswordInput.value = '';
    
    // reset change password UI
    changePasswordForm.classList.add('hidden');
    changePasswordForm.reset();
});

// ── Change Password Logic ──
btnToggleChangePassword.addEventListener('click', () => {
    changePasswordForm.classList.toggle('hidden');
});

btnCancelChangePassword.addEventListener('click', () => {
    changePasswordForm.classList.add('hidden');
    changePasswordForm.reset();
    clearErrors();
});

changePasswordForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    clearErrors();

    if (!currentStudentId) return;

    const oldPwd = oldPasswordInput.value;
    const newPwd = newPasswordInput.value;
    const confirmPwd = confirmPasswordInput.value;

    let valid = true;
    if (!oldPwd) {
        showError('oldPasswordGroup', 'Current password is required');
        valid = false;
    }
    if (!newPwd) {
        showError('newPasswordGroup', 'New password is required');
        valid = false;
    } else if (newPwd.length < 4) {
        showError('newPasswordGroup', 'Password must be at least 4 characters');
        valid = false;
    }
    if (newPwd !== confirmPwd) {
        showError('confirmPasswordGroup', 'Passwords do not match');
        valid = false;
    }

    if (!valid) return;

    const btnSubmit = document.getElementById('btnChangePasswordSubmit');
    btnSubmit.disabled = true;
    btnSubmit.textContent = 'Updating...';

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

    try {
        const user = firebaseAuth.currentUser;
        const credential = EmailAuthProvider.credential(user.email, oldPwd);
        
        await reauthenticateWithCredential(user, credential);
        await updatePassword(user, newPwd);

        showToast('✓ Password updated successfully!');
        changePasswordForm.classList.add('hidden');
        changePasswordForm.reset();
    } catch (err) {
        console.error('Change password error:', err);
        let msg = 'Network error — please try again';
        if (err.code === 'auth/invalid-credential') msg = 'Incorrect current password.';
        showToast(msg);
    } finally {
        btnSubmit.disabled = false;
        btnSubmit.textContent = 'Update Password';
    }
});

// ── Helpers ──

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function showError(groupId, message) {
    const group = document.getElementById(groupId);
    group.classList.add('error');
    group.querySelector('.error-msg').textContent = message;
}

function clearErrors() {
    document.querySelectorAll('.form-group').forEach(g => {
        g.classList.remove('error');
    });
}

let toastTimeout;
function showToast(message) {
    toastMessage.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}
