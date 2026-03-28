function esc(str) {
    const d = document.createElement('div');
    d.textContent = str == null ? '' : String(str);
    return d.innerHTML;
}

const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]')?.content || '';
function apiFetch(url, options = {}) {
    const headers = { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN, ...(options.headers || {}) };
    return fetch(url, { ...options, headers });
}

const DEPARTMENTS = { 1: 'Head of International Office', 2: 'Secretary', 3: 'Administration', 4: 'Media & Design', 5: 'Hospitality', 6: 'Community Impact' };
let sortCol = 'name_id';
let sortAsc = true;
let selectedNIMs = new Set();

/* ════════════════════════════════════════════════
    TABLE RENDERING
    ════════════════════════════════════════════════ */
function renderTable(filter = '') {
    const tbody = document.getElementById('tableBody');
    const q = filter.toLowerCase();

    let filtered = students.filter(s =>
        s.name_id.toLowerCase().includes(q) ||
        s.email_id.toLowerCase().includes(q) ||
        s.nim_id.toLowerCase().includes(q) ||
        (DEPARTMENTS[s.department_id] || '').toLowerCase().includes(q)
    );

    // Sort
    filtered.sort((a, b) => {
        let va = a[sortCol], vb = b[sortCol];
        if (sortCol === 'score') { va = parseFloat(va); vb = parseFloat(vb); }
        if (sortCol === 'index') { va = students.indexOf(a); vb = students.indexOf(b); }
        if (typeof va === 'string') va = va.toLowerCase();
        if (typeof vb === 'string') vb = vb.toLowerCase();
        if (va < vb) return sortAsc ? -1 : 1;
        if (va > vb) return sortAsc ? 1 : -1;
        return 0;
    });

    tbody.innerHTML = filtered.map((s, i) => {
        const checked = selectedNIMs.has(s.nim_id) ? 'checked' : '';
        const selClass = selectedNIMs.has(s.nim_id) ? 'selected' : '';
        const deptName = DEPARTMENTS[s.department_id] || '';
        const tasks = (s.job_id_list || '').split(';').filter(Boolean).length;
        return `<tr class="${selClass}" data-nim="${esc(s.nim_id)}">
            <td><input type="checkbox" class="row-check" data-nim="${esc(s.nim_id)}" ${checked}></td>
            <td style="color:#94a3b8; font-weight:600;">${i + 1}</td>
            <td><div class="cell-editable" contenteditable="true" data-field="name_id">${esc(s.name_id)}</div></td>
            <td><div class="cell-editable" contenteditable="true" data-field="email_id">${esc(s.email_id)}</div></td>
            <td>
                <select class="cell-dept-select" data-field="department_id">
                    ${Object.entries(DEPARTMENTS).map(([k, v]) =>
            `<option value="${k}" ${parseInt(k) === s.department_id ? 'selected' : ''}>${v}</option>`
        ).join('')}
                </select>
            </td>
            <td style="font-weight:600;">${esc(s.nim_id)}</td>
            <td><div class="cell-editable" contenteditable="true" data-field="score">${parseInt(s.score)}</div></td>
            <td style="font-size:12px; color:#64748b; max-width:220px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${esc(s.job_id_list || '')}">${tasks ? tasks + ' task(s)' : '—'}</td>
        </tr>`;
    }).join('');

    document.getElementById('footerInfo').textContent = `Showing ${filtered.length} of ${students.length} students`;
    updateSelectionUI();
}

/* ════════════════════════════════════════════════
    INLINE EDITING
    ════════════════════════════════════════════════ */
document.getElementById('tableBody').addEventListener('blur', (e) => {
    if (e.target.classList.contains('cell-editable')) {
        const tr = e.target.closest('tr');
        const nim = tr.dataset.nim;
        const field = e.target.dataset.field;
        const value = e.target.innerText.trim();
        const student = students.find(s => s.nim_id === nim);
        if (student) {
            if (field === 'score') student[field] = parseFloat(value) || 0;
            else student[field] = value;
        }
    }
}, true);

document.getElementById('tableBody').addEventListener('change', (e) => {
    if (e.target.classList.contains('cell-dept-select')) {
        const tr = e.target.closest('tr');
        const nim = tr.dataset.nim;
        const student = students.find(s => s.nim_id === nim);
        if (student) {
            student.department_id = parseInt(e.target.value);
            student.department_name = DEPARTMENTS[student.department_id];
        }
    }
});

/* ════════════════════════════════════════════════
    SELECTION
    ════════════════════════════════════════════════ */
document.getElementById('tableBody').addEventListener('change', (e) => {
    if (e.target.classList.contains('row-check')) {
        const nim = e.target.dataset.nim;
        if (e.target.checked) selectedNIMs.add(nim);
        else selectedNIMs.delete(nim);
        updateSelectionUI();
    }
});

document.getElementById('selectAll').addEventListener('change', (e) => {
    const checks = document.querySelectorAll('.row-check');
    checks.forEach(cb => {
        cb.checked = e.target.checked;
        if (e.target.checked) selectedNIMs.add(cb.dataset.nim);
        else selectedNIMs.delete(cb.dataset.nim);
    });
    updateSelectionUI();
});

function updateSelectionUI() {
    const btn = document.getElementById('btnDeleteSelected');
    const info = document.getElementById('footerSelected');
    if (selectedNIMs.size > 0) {
        btn.style.display = 'inline-flex';
        info.textContent = `${selectedNIMs.size} selected`;
    } else {
        btn.style.display = 'none';
        info.textContent = '';
    }
}

/* ════════════════════════════════════════════════
    SORTING
    ════════════════════════════════════════════════ */
document.querySelectorAll('thead th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
        const col = th.dataset.sort;
        if (sortCol === col) sortAsc = !sortAsc;
        else { sortCol = col; sortAsc = true; }

        document.querySelectorAll('thead th').forEach(h => h.classList.remove('sorted'));
        th.classList.add('sorted');
        th.querySelector('.sort-icon').textContent = sortAsc ? '▲' : '▼';

        renderTable(document.getElementById('searchInput').value);
    });
});

/* ════════════════════════════════════════════════
    SEARCH
    ════════════════════════════════════════════════ */
document.getElementById('searchInput').addEventListener('input', (e) => {
    renderTable(e.target.value);
});

/* ════════════════════════════════════════════════
    SAVE CHANGES
    ════════════════════════════════════════════════ */
document.getElementById('btnSave').addEventListener('click', async () => {
    showToast('Syncing to database…', 'success');
    try {
        const res = await apiFetch('/api/students/save-all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ students })
        });
        const data = await res.json();
        if (res.ok) showToast('Changes saved successfully!', 'success');
        else showToast(data.error || 'Save failed', 'error');
    } catch (err) {
        showToast('Network error: ' + err.message, 'error');
    }
});

/* ════════════════════════════════════════════════
    DELETE SELECTED
    ════════════════════════════════════════════════ */
document.getElementById('btnDeleteSelected').addEventListener('click', () => {
    if (!confirm(`Delete ${selectedNIMs.size} student(s)? This takes effect when you click Save.`)) return;
    students = students.filter(s => !selectedNIMs.has(s.nim_id));
    selectedNIMs.clear();
    document.getElementById('selectAll').checked = false;
    renderTable(document.getElementById('searchInput').value);
    showToast('Rows removed. Click "Save Changes" to persist.', 'success');
});

/* ════════════════════════════════════════════════
    ADD STUDENT MODAL
    ════════════════════════════════════════════════ */
const addModal = document.getElementById('addModal');
document.getElementById('btnAddStudent').addEventListener('click', () => { addModal.style.display = 'flex'; });
document.getElementById('cancelAdd').addEventListener('click', () => { addModal.style.display = 'none'; });
window.addEventListener('click', (e) => { if (e.target === addModal) addModal.style.display = 'none'; });

document.getElementById('addStudentForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        name_id: document.getElementById('addName').value.trim(),
        email_id: document.getElementById('addEmail').value.trim(),
        department_id: parseInt(document.getElementById('addDept').value),
        nim_id: document.getElementById('addNIM').value.trim()
    };

    try {
        const res = await apiFetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
            students.push(data.student);
            addModal.style.display = 'none';
            e.target.reset();
            renderTable(document.getElementById('searchInput').value);
            showToast(`${data.student.name_id} added!`, 'success');
        } else {
            const msgs = Object.values(data.errors || {}).join('\n');
            showToast(msgs || 'Validation error', 'error');
        }
    } catch (err) {
        showToast('Network error: ' + err.message, 'error');
    }
});

/* ════════════════════════════════════════════════
    EXPORT
    ════════════════════════════════════════════════ */
document.getElementById('btnExportCSV').addEventListener('click', () => {
    window.location.href = '/api/export/csv';
});
document.getElementById('btnExportSQL').addEventListener('click', () => {
    window.location.href = '/api/export/sql';
});

document.getElementById('btnExportSheets').addEventListener('click', async () => {
    const btn = document.getElementById('btnExportSheets');
    const originalContent = btn.innerHTML;
    btn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="animation: spin 1s linear infinite;"><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/></svg> Sending...`;
    btn.disabled = true;
    btn.style.opacity = '0.7';

    try {
        const res = await apiFetch('/api/export/sheets', { method: 'POST' });
        const data = await res.json();
        if (res.ok) {
            showToast(data.message || 'Exported to Sheets!', 'success');
        } else {
            showToast(data.error || 'Failed to export to Sheets', 'error');
        }
    } catch (err) {
        showToast('Network error: ' + err.message, 'error');
    } finally {
        btn.innerHTML = originalContent;
        btn.disabled = false;
        btn.style.opacity = '1';
    }
});

/* ════════════════════════════════════════════════
    TOAST
    ════════════════════════════════════════════════ */
function showToast(msg, type = 'success') {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = `toast toast-${type} show`;
    setTimeout(() => el.classList.remove('show'), 3000);
}

/* ════════════════════════════════════════════════
    INIT
    ════════════════════════════════════════════════ */
renderTable();
