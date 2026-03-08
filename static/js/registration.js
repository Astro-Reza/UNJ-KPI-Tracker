/* ============================================
   Registration Page — Logic
   Posts to Flask backend, renders table from API
   ============================================ */

// Department mapping (for client-side display)
const DEPARTMENTS = {
    1: 'Head of International Office',
    2: 'Secretary',
    3: 'Administration',
    4: 'Media & Design',
    5: 'Hospitality',
    6: 'Community Impact'
};

// DOM references
const authTabs = document.getElementById('authTabs');
const tabRegister = document.getElementById('tabRegister');
const tabSelectTasks = document.getElementById('tabSelectTasks');

const form = document.getElementById('registrationForm');
const loginForm = document.getElementById('loginForm');
const taskSelectionContainer = document.getElementById('taskSelectionContainer');

// Register Form elements
const nameInput = document.getElementById('nameInput');
const emailInput = document.getElementById('emailInput');
const deptSelect = document.getElementById('departmentSelect');
const nimInput = document.getElementById('nimInput');

// Login Form elements
const loginNimInput = document.getElementById('loginNimInput');
const loginPasswordInput = document.getElementById('loginPasswordInput');

// Task Selection elements
const profileName = document.getElementById('profileName');
const profileNim = document.getElementById('profileNim');
const profileDept = document.getElementById('profileDept');
const tasksList = document.getElementById('tasksList');
const btnSaveTasks = document.getElementById('btnSaveTasks');
const btnBackToLogin = document.getElementById('btnBackToLogin');

// Change Password elements
const btnToggleChangePassword = document.getElementById('btnToggleChangePassword');
const changePasswordForm = document.getElementById('changePasswordForm');
const oldPasswordInput = document.getElementById('oldPasswordInput');
const newPasswordInput = document.getElementById('newPasswordInput');
const confirmPasswordInput = document.getElementById('confirmPasswordInput');
const btnCancelChangePassword = document.getElementById('btnCancelChangePassword');

const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toastMessage');

// State
let currentStudentId = null;

// ── Tab Switching ──
tabRegister.addEventListener('click', () => {
    tabRegister.classList.add('active');
    tabSelectTasks.classList.remove('active');
    form.classList.remove('hidden');
    loginForm.classList.add('hidden');
    taskSelectionContainer.classList.add('hidden');
    clearErrors();
});

tabSelectTasks.addEventListener('click', () => {
    tabSelectTasks.classList.add('active');
    tabRegister.classList.remove('active');
    loginForm.classList.remove('hidden');
    form.classList.add('hidden');
    taskSelectionContainer.classList.add('hidden');
    clearErrors();
});

// ── Form Submission → POST to backend ──
form.addEventListener('submit', async function (e) {
    e.preventDefault();
    clearErrors();

    const name = nameInput.value.trim();
    const email = emailInput.value.trim();
    const dept = parseInt(deptSelect.value);
    const nim = nimInput.value.trim();

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

    try {
        const res = await fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name_id: name,
                email_id: email,
                department_id: dept,
                nim_id: nim
            })
        });

        const data = await res.json();

        if (!res.ok) {
            // Server-side validation errors
            if (data.errors) {
                if (data.errors.name_id) showError('nameGroup', data.errors.name_id);
                if (data.errors.email_id) showError('emailGroup', data.errors.email_id);
                if (data.errors.department_id) showError('deptGroup', data.errors.department_id);
                if (data.errors.nim_id) showError('nimGroup', data.errors.nim_id);
            } else {
                showToast(data.error || 'Registration failed');
            }
            return;
        }

        // Success
        form.reset();
        nameInput.focus();
        showToast(`✓ ${name} registered successfully!`);

    } catch (err) {
        console.error('Registration error:', err);
        showToast('Network error — please try again');
    }
});

// ── Funnel 2: Login returning student ──
loginForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    clearErrors();

    const nim = loginNimInput.value.trim();
    const password = loginPasswordInput.value.trim();

    let valid = true;
    if (!nim) {
        showError('loginNimGroup', 'Student ID (NIM) is required');
        valid = false;
    }
    if (!password) {
        showError('loginPasswordGroup', 'Password is required');
        valid = false;
    }

    if (!valid) return;

    try {
        const res = await fetch('/api/student/auth', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nim_id: nim, password: password })
        });

        const data = await res.json();

        if (!res.ok) {
            showToast(data.error || 'Login failed');
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
        console.error('Login error:', err);
        showToast('Network error — please try again');
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

    try {
        const res = await fetch('/api/student/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
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

// ── Back to Login ──
btnBackToLogin.addEventListener('click', () => {
    taskSelectionContainer.classList.add('hidden');
    loginForm.classList.remove('hidden');
    authTabs.classList.remove('hidden');
    currentStudentId = null;
    loginNimInput.value = '';
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

    try {
        const res = await fetch('/api/student/change_password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nim_id: currentStudentId,
                old_password: oldPwd,
                new_password: newPwd
            })
        });

        const data = await res.json();

        if (!res.ok) {
            showToast(data.error || 'Failed to update password');
        } else {
            showToast('✓ Password updated successfully!');
            changePasswordForm.classList.add('hidden');
            changePasswordForm.reset();
        }
    } catch (err) {
        console.error('Change password error:', err);
        showToast('Network error — please try again');
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
