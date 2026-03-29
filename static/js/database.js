/* ── Helpers ─────────────────────────────────────── */
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
const TASK_STATUSES = { 1: 'Planning', 2: 'In-Progress', 3: 'Execution', 4: 'Documentation', 5: 'Lecturer Review', 6: 'Done', 7: 'Finished' };
const TASK_TYPES = { 1: 'Publication', 2: 'Event', 3: 'Camp' };

let sortCol = 'name_id';
let sortAsc = true;
let selectedNIMs = new Set();

/* ── Toast ───────────────────────────────────────── */
function showToast(msg, type = 'success') {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = `toast toast-${type} show`;
    setTimeout(() => el.classList.remove('show'), 3500);
}

/* ── Table Rendering ─────────────────────────────── */
function renderTable(filter = '') {
    const tbody = document.getElementById('tableBody');
    const q = filter.toLowerCase();

    let filtered = students.filter(s =>
        (s.name_id || '').toLowerCase().includes(q) ||
        (s.email_id || '').toLowerCase().includes(q) ||
        (s.nim_id || '').toLowerCase().includes(q) ||
        (DEPARTMENTS[s.department_id] || '').toLowerCase().includes(q)
    );

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
        const taskCount = (s.job_id_list || '').split(';').filter(Boolean).length;
        const deptName = DEPARTMENTS[s.department_id] || '—';
        return `<tr class="${selClass}" data-nim="${esc(s.nim_id)}">
            <td><input type="checkbox" class="row-check" data-nim="${esc(s.nim_id)}" ${checked}></td>
            <td class="num-cell">${i + 1}</td>
            <td>
                <div class="name-cell">
                    <span class="name-text">${esc(s.name_id)}</span>
                    <span class="nim-tag">${esc(s.nim_id)}</span>
                </div>
            </td>
            <td>${esc(s.email_id)}</td>
            <td><span class="dept-badge">${esc(deptName)}</span></td>
            <td><span class="score-val">${parseFloat(s.score || 0).toFixed(1)}</span></td>
            <td><span class="task-count-badge ${taskCount > 0 ? 'has-tasks' : ''}">${taskCount} task${taskCount !== 1 ? 's' : ''}</span></td>
            <td>
                <div class="action-group">
                    <button class="action-btn btn-detail" onclick="openDetail('${esc(s.nim_id)}')" title="View details">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    </button>
                    <button class="action-btn btn-edit" onclick="openEdit('${esc(s.nim_id)}')" title="Edit student">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    </button>
                    <button class="action-btn btn-reset" onclick="resetPassword('${esc(s.nim_id)}', '${esc(s.name_id)}')" title="Reset password">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                    </button>
                    <button class="action-btn btn-delete" onclick="deleteStudent('${esc(s.nim_id)}', '${esc(s.name_id)}')" title="Delete student">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                    </button>
                </div>
            </td>
        </tr>`;
    }).join('');

    document.getElementById('footerInfo').textContent = `Showing ${filtered.length} of ${students.length} students`;
    updateStats();
    updateSelectionUI();
}

/* ── Stats ───────────────────────────────────────── */
function updateStats() {
    document.getElementById('statTotal').textContent = students.length;
    const depts = new Set(students.map(s => s.department_id)).size;
    document.getElementById('statDepts').textContent = depts;
    const scores = students.map(s => parseFloat(s.score || 0));
    const avg = scores.length ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1) : '0';
    const top = scores.length ? Math.max(...scores).toFixed(1) : '0';
    document.getElementById('statAvgScore').textContent = avg;
    document.getElementById('statTopScore').textContent = top;
}

/* ── Selection ───────────────────────────────────── */
document.getElementById('tableBody').addEventListener('change', (e) => {
    if (e.target.classList.contains('row-check')) {
        const nim = e.target.dataset.nim;
        if (e.target.checked) selectedNIMs.add(nim);
        else selectedNIMs.delete(nim);
        e.target.closest('tr').classList.toggle('selected', e.target.checked);
        updateSelectionUI();
    }
});

document.getElementById('selectAll').addEventListener('change', (e) => {
    document.querySelectorAll('.row-check').forEach(cb => {
        cb.checked = e.target.checked;
        cb.closest('tr').classList.toggle('selected', e.target.checked);
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

/* ── Sorting ─────────────────────────────────────── */
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

/* ── Search ──────────────────────────────────────── */
document.getElementById('searchInput').addEventListener('input', (e) => renderTable(e.target.value));

/* ── Detail Drawer ───────────────────────────────── */
async function openDetail(nimId) {
    const drawer = document.getElementById('detailDrawer');
    const content = document.getElementById('drawerContent');
    drawer.classList.add('open');
    content.innerHTML = `<div class="drawer-loading">Loading…</div>`;

    try {
        const res = await apiFetch(`/api/students/${encodeURIComponent(nimId)}`);
        const data = await res.json();
        if (!res.ok) { content.innerHTML = `<p style="color:#ef4444">${esc(data.error)}</p>`; return; }

        const s = data.student;
        const contribs = data.contributions || [];
        const earnedPts = contribs.filter(c => c.status_id === 7).reduce((a, c) => a + parseFloat(c.points || 0), 0);

        content.innerHTML = `
            <div class="drawer-header-info">
                <div class="drawer-avatar">${esc(s.name_id.charAt(0).toUpperCase())}</div>
                <div>
                    <div class="drawer-name">${esc(s.name_id)}</div>
                    <div class="drawer-sub">${esc(s.nim_id)}</div>
                    <div class="drawer-sub">${esc(DEPARTMENTS[s.department_id] || '—')}</div>
                    <div class="drawer-sub">${esc(s.email_id)}</div>
                </div>
            </div>
            <div class="drawer-score-row">
                <div class="drawer-score-card">
                    <div class="drawer-score-val">${parseFloat(s.score || 0).toFixed(1)}</div>
                    <div class="drawer-score-label">Total Score</div>
                </div>
                <div class="drawer-score-card">
                    <div class="drawer-score-val">${contribs.length}</div>
                    <div class="drawer-score-label">Tasks Joined</div>
                </div>
                <div class="drawer-score-card">
                    <div class="drawer-score-val">${earnedPts.toFixed(1)}</div>
                    <div class="drawer-score-label">Points Earned</div>
                </div>
            </div>
            <div class="drawer-section-title">Task Contributions</div>
            ${contribs.length === 0
                ? `<p class="drawer-empty">No task contributions yet.</p>`
                : contribs.map(c => `
                    <div class="contrib-row">
                        <div class="contrib-info">
                            <span class="contrib-name">${esc(c.task_name)}</span>
                            <span class="contrib-meta">${esc(TASK_TYPES[c.type_id] || '')} · ${esc(TASK_STATUSES[c.status_id] || '')}</span>
                        </div>
                        <span class="contrib-pts ${c.status_id === 7 ? 'pts-counted' : 'pts-pending'}">${parseFloat(c.points || 0).toFixed(1)} pts</span>
                    </div>`).join('')
            }
            <div class="drawer-actions">
                <button class="btn btn-outline" onclick="openEdit('${esc(s.nim_id)}')">Edit</button>
                <button class="btn btn-warning" onclick="resetPassword('${esc(s.nim_id)}', '${esc(s.name_id)}')">Reset Password</button>
                <button class="btn btn-danger" onclick="deleteStudent('${esc(s.nim_id)}', '${esc(s.name_id)}')">Delete</button>
            </div>`;
    } catch {
        content.innerHTML = `<p style="color:#ef4444">Failed to load student data.</p>`;
    }
}

document.getElementById('drawerClose').addEventListener('click', () => document.getElementById('detailDrawer').classList.remove('open'));
document.getElementById('drawerOverlay').addEventListener('click', () => document.getElementById('detailDrawer').classList.remove('open'));

/* ── Edit Modal ──────────────────────────────────── */
function openEdit(nimId) {
    const s = students.find(s => s.nim_id === nimId);
    if (!s) return;
    document.getElementById('editNim').value = s.nim_id;
    document.getElementById('editName').value = s.name_id;
    document.getElementById('editEmail').value = s.email_id;
    document.getElementById('editDept').value = s.department_id;
    document.getElementById('editScore').value = parseFloat(s.score || 0).toFixed(1);
    document.getElementById('editModal').style.display = 'flex';
}

document.getElementById('cancelEdit').addEventListener('click', () => { document.getElementById('editModal').style.display = 'none'; });
window.addEventListener('click', (e) => { if (e.target === document.getElementById('editModal')) document.getElementById('editModal').style.display = 'none'; });

document.getElementById('editStudentForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const nimId = document.getElementById('editNim').value;
    const payload = {
        name_id: document.getElementById('editName').value.trim(),
        email_id: document.getElementById('editEmail').value.trim(),
        department_id: parseInt(document.getElementById('editDept').value),
        score: parseFloat(document.getElementById('editScore').value) || 0,
    };
    try {
        const res = await apiFetch(`/api/students/${encodeURIComponent(nimId)}`, { method: 'PUT', body: JSON.stringify(payload) });
        const data = await res.json();
        if (!res.ok) { showToast(data.error || 'Update failed', 'error'); return; }
        const s = students.find(s => s.nim_id === nimId);
        if (s) Object.assign(s, payload);
        document.getElementById('editModal').style.display = 'none';
        renderTable(document.getElementById('searchInput').value);
        showToast('Student updated!');
    } catch { showToast('Network error', 'error'); }
});

/* ── Add Student Modal ───────────────────────────── */
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
        const res = await apiFetch('/api/register', { method: 'POST', body: JSON.stringify(payload) });
        const data = await res.json();
        if (res.ok) {
            students.push(data.student);
            addModal.style.display = 'none';
            e.target.reset();
            renderTable(document.getElementById('searchInput').value);
            showToast(`${data.student.name_id} added!`);
            if (data.initial_password) alert(`Student added!\n\nInitial password: ${data.initial_password}\n\nShare this securely — it won't be shown again.`);
        } else {
            showToast(Object.values(data.errors || {}).join(' · ') || data.error || 'Validation error', 'error');
        }
    } catch { showToast('Network error', 'error'); }
});

/* ── Delete Single ───────────────────────────────── */
async function deleteStudent(nimId, name) {
    document.getElementById('detailDrawer').classList.remove('open');
    document.getElementById('editModal').style.display = 'none';
    if (!confirm(`Permanently delete "${name}" (${nimId})?\n\nThis removes the student, their task contributions, and their login account. This cannot be undone.`)) return;
    try {
        const res = await apiFetch(`/api/students/${encodeURIComponent(nimId)}`, { method: 'DELETE' });
        const data = await res.json();
        if (!res.ok) { showToast(data.error || 'Delete failed', 'error'); return; }
        students = students.filter(s => s.nim_id !== nimId);
        selectedNIMs.delete(nimId);
        renderTable(document.getElementById('searchInput').value);
        showToast(`${name} deleted.`);
    } catch { showToast('Network error', 'error'); }
}

/* ── Bulk Delete ─────────────────────────────────── */
document.getElementById('btnDeleteSelected').addEventListener('click', async () => {
    if (selectedNIMs.size === 0) return;
    const names = students.filter(s => selectedNIMs.has(s.nim_id)).map(s => s.name_id).join(', ');
    if (!confirm(`Permanently delete ${selectedNIMs.size} student(s)?\n${names}\n\nThis cannot be undone.`)) return;
    const toDelete = [...selectedNIMs];
    let failed = 0;
    for (const nimId of toDelete) {
        try {
            const res = await apiFetch(`/api/students/${encodeURIComponent(nimId)}`, { method: 'DELETE' });
            if (res.ok) { students = students.filter(s => s.nim_id !== nimId); selectedNIMs.delete(nimId); }
            else failed++;
        } catch { failed++; }
    }
    document.getElementById('selectAll').checked = false;
    renderTable(document.getElementById('searchInput').value);
    showToast(failed > 0 ? `Deleted ${toDelete.length - failed}, failed ${failed}.` : `${toDelete.length} student(s) deleted.`, failed > 0 ? 'error' : 'success');
});

/* ── Reset Password ──────────────────────────────── */
async function resetPassword(nimId, name) {
    if (!confirm(`Reset password for "${name}"?\n\nA new random password will be generated.`)) return;
    try {
        const res = await apiFetch(`/api/students/${encodeURIComponent(nimId)}/reset-password`, { method: 'POST' });
        const data = await res.json();
        if (!res.ok) { showToast(data.error || 'Reset failed', 'error'); return; }
        alert(`Password reset for ${name}.\n\nNew password: ${data.new_password}\n\nShare this with the student securely.`);
        showToast('Password reset!');
    } catch { showToast('Network error', 'error'); }
}

/* ── Sync Scores ─────────────────────────────────── */
document.getElementById('btnSyncScores').addEventListener('click', async () => {
    const btn = document.getElementById('btnSyncScores');
    btn.disabled = true;
    const orig = btn.innerHTML;
    btn.innerHTML = `<svg style="animation:spin 1s linear infinite;width:15px;height:15px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10"/><path d="M20.49 15a9 9 0 0 1-14.85 3.36L1 14"/></svg> Syncing…`;
    try {
        const res = await apiFetch('/api/students/sync-scores', { method: 'POST' });
        const data = await res.json();
        if (!res.ok) { showToast(data.error || 'Sync failed', 'error'); return; }
        students = data.students;
        renderTable(document.getElementById('searchInput').value);
        showToast('Scores synced from task contributors!');
    } catch { showToast('Network error', 'error'); }
    finally { btn.disabled = false; btn.innerHTML = orig; }
});

/* ── CSV Import ──────────────────────────────────── */
document.getElementById('btnImportCSV').addEventListener('click', () => document.getElementById('csvFileInput').click());

document.getElementById('csvFileInput').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
        try {
            const lines = evt.target.result.split('\n').map(l => l.trim()).filter(Boolean);
            if (lines.length < 2) { showToast('CSV must have a header row and at least one data row', 'error'); return; }
            const headers = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/"/g, ''));
            const rows = [];
            for (let i = 1; i < lines.length; i++) {
                const vals = lines[i].split(',').map(v => v.trim().replace(/"/g, ''));
                const row = {};
                headers.forEach((h, idx) => { row[h] = vals[idx] || ''; });
                if (row.nim_id && row.name_id) rows.push(row);
            }
            if (rows.length === 0) { showToast('No valid rows found. CSV must have nim_id and name_id columns.', 'error'); return; }
            document.getElementById('importPreviewCount').textContent = `${rows.length} student(s) found in file`;
            document.getElementById('importSample').innerHTML = rows.slice(0, 3).map(r =>
                `<div class="import-sample-row">${esc(r.name_id)} · ${esc(r.nim_id)} · ${esc(r.email_id || '—')}</div>`
            ).join('') + (rows.length > 3 ? `<div class="import-sample-more">…and ${rows.length - 3} more</div>` : '');
            document.getElementById('importModal').style.display = 'flex';
            document.getElementById('importModal').dataset.rows = JSON.stringify(rows);
        } catch { showToast('Failed to parse CSV', 'error'); }
    };
    reader.readAsText(file);
    e.target.value = '';
});

document.getElementById('cancelImport').addEventListener('click', () => { document.getElementById('importModal').style.display = 'none'; });

document.getElementById('confirmImport').addEventListener('click', async () => {
    const rows = JSON.parse(document.getElementById('importModal').dataset.rows || '[]');
    document.getElementById('importModal').style.display = 'none';
    const btn = document.getElementById('confirmImport');
    btn.disabled = true;
    showToast(`Importing ${rows.length} students…`, 'success');
    let added = 0, failed = 0;
    for (const row of rows) {
        const payload = {
            name_id: row.name_id || '',
            email_id: row.email_id || '',
            department_id: parseInt(row.department_id) || 1,
            nim_id: row.nim_id || '',
        };
        try {
            const res = await apiFetch('/api/register', { method: 'POST', body: JSON.stringify(payload) });
            const data = await res.json();
            if (res.ok) { students.push(data.student); added++; }
            else failed++;
        } catch { failed++; }
    }
    renderTable(document.getElementById('searchInput').value);
    showToast(`Import done: ${added} added${failed > 0 ? `, ${failed} failed` : ''}.`, failed > 0 ? 'error' : 'success');
    btn.disabled = false;
});

/* ── Export ──────────────────────────────────────── */
document.getElementById('btnExportCSV').addEventListener('click', () => { window.location.href = '/api/export/csv'; });
document.getElementById('btnExportSQL').addEventListener('click', () => { window.location.href = '/api/export/sql'; });
document.getElementById('btnExportSheets').addEventListener('click', async () => {
    const btn = document.getElementById('btnExportSheets');
    const orig = btn.innerHTML;
    btn.innerHTML = 'Sending…'; btn.disabled = true;
    try {
        const res = await apiFetch('/api/export/sheets', { method: 'POST' });
        const data = await res.json();
        showToast(res.ok ? (data.message || 'Sent!') : (data.error || 'Failed'), res.ok ? 'success' : 'error');
    } catch { showToast('Network error', 'error'); }
    finally { btn.innerHTML = orig; btn.disabled = false; }
});

/* ── Init ────────────────────────────────────────── */
renderTable();