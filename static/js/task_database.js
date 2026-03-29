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

const TASK_TYPES = { 1: 'Publication', 2: 'Event', 3: 'Camp' };
const TASK_STATUSES = { 1: 'Planning', 2: 'In-Progress', 3: 'Execution', 4: 'Documentation', 5: 'Lecturer Review', 6: 'Done', 7: 'Finished' };

let sortCol = 'start_date';
let sortAsc = false;

/* ════════════════════════════════════════════════
    TABLE RENDERING
    ════════════════════════════════════════════════ */
function renderTable(filter = '') {
    const tbody = document.getElementById('tableBody');
    const q = filter.toLowerCase();

    let filtered = tasks.filter(t =>
        String(t.task_name || '').toLowerCase().includes(q) ||
        String(t.pic || '').toLowerCase().includes(q) ||
        String(TASK_TYPES[t.type_id] || '').toLowerCase().includes(q) ||
        String(TASK_STATUSES[t.status_id] || '').toLowerCase().includes(q)
    );

    // Sort
    filtered.sort((a, b) => {
        let va, vb;
        if (sortCol === 'index') {
            va = tasks.indexOf(a);
            vb = tasks.indexOf(b);
        } else if (sortCol === 'type_name') {
            va = TASK_TYPES[a.type_id] || '';
            vb = TASK_TYPES[b.type_id] || '';
        } else if (sortCol === 'status_name') {
            va = TASK_STATUSES[a.status_id] || '';
            vb = TASK_STATUSES[b.status_id] || '';
        } else {
            va = a[sortCol] || '';
            vb = b[sortCol] || '';
        }

        if (typeof va === 'string') va = va.toLowerCase();
        if (typeof vb === 'string') vb = vb.toLowerCase();
        
        if (va < vb) return sortAsc ? -1 : 1;
        if (va > vb) return sortAsc ? 1 : -1;
        return 0;
    });

    tbody.innerHTML = filtered.map((t, i) => {
        const typeName = TASK_TYPES[t.type_id] || 'Unknown';
        const statusName = TASK_STATUSES[t.status_id] || 'Unknown';
        
        let typeBadgeClass = 'badge-dept';
        if (t.type_id === 1) typeBadgeClass = 'badge-publication';
        if (t.type_id === 2) typeBadgeClass = 'badge-event';
        if (t.type_id === 3) typeBadgeClass = 'badge-camp';

        return `<tr>
            <td style="color:#94a3b8; font-weight:600;">${i + 1}</td>
            <td style="font-weight:600;">${esc(t.task_name || '—')}</td>
            <td><span class="badge ${typeBadgeClass}">${esc(typeName)}</span></td>
            <td>${esc(statusName)}</td>
            <td>${esc(t.start_date || '—')}</td>
            <td>${esc(t.end_date || '—')}</td>
            <td>${esc(t.pic || '—')}</td>
            <td>
                <div class="action-group">
                    <button class="action-btn btn-detail" onclick="openDetail('${esc(t.task_id)}')" title="View tasks detail">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    </button>
                    <button class="action-btn btn-edit" onclick="openEdit('${esc(t.task_id)}')" title="Edit task">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    </button>
                    <button class="action-btn btn-delete" onclick="deleteTask('${esc(t.task_id)}', '${esc(t.task_name)}')" title="Delete task">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                    </button>
                </div>
            </td>
        </tr>`;
    }).join('');

    document.getElementById('footerInfo').textContent = `Showing ${filtered.length} of ${tasks.length} tasks`;
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
    EXPORT (Reusing same endpoints)
    ════════════════════════════════════════════════ */
document.getElementById('btnExportCSV')?.addEventListener('click', () => {
    window.location.href = '/api/export/csv';
});
document.getElementById('btnExportSQL')?.addEventListener('click', () => {
    window.location.href = '/api/export/sql';
});

document.getElementById('btnExportSheets')?.addEventListener('click', async () => {
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
    if(!el) return;
    el.textContent = msg;
    el.className = `toast toast-${type} show`;
    setTimeout(() => el.classList.remove('show'), 3000);
}

/* ════════════════════════════════════════════════
    INIT
    ════════════════════════════════════════════════ */
renderTable();


/* ════════════════════════════════════════════════
    DRAWER & LOGICS
    ════════════════════════════════════════════════ */
const drawer = document.getElementById('detailDrawer');
const overlay = document.getElementById('drawerOverlay');

function closeDrawer() {
    drawer?.classList.remove('open');
    overlay?.classList.remove('open');
}

document.getElementById('drawerClose')?.addEventListener('click', closeDrawer);
overlay?.addEventListener('click', closeDrawer);

window.openDetail = async function(taskId) {
    const t = tasks.find(x => x.task_id === taskId);
    if (!t) return;
    
    let contributorsHtml = '<p style="color:#64748b; font-size:13px;">Loading contributors...</p>';
    if (document.getElementById('drawerContent')) {
        document.getElementById('drawerContent').innerHTML = `
            <div style="margin-bottom: 20px;">
                <h3 style="margin: 0 0 8px 0; color:#1e293b;">${esc(t.task_name)}</h3>
                <div style="font-size: 13px; color:#64748b; display:grid; gap:8px; grid-template-columns: auto 1fr;">
                    <strong>Task ID:</strong> <span>${esc(t.task_id)}</span>
                    <strong>Status:</strong> <span>${TASK_STATUSES[t.status_id]}</span>
                    <strong>Type:</strong> <span>${TASK_TYPES[t.type_id]}</span>
                    <strong>PIC:</strong> <span>${esc(t.pic || '—')}</span>
                    <strong>Duration:</strong> <span>${esc(t.start_date || '—')} to ${esc(t.end_date || '—')}</span>
                    <strong>Links:</strong> <span>${esc(t.related_links || '—')}</span>
                    <strong>Desc:</strong> <span>${esc(t.description || '—')}</span>
                </div>
            </div>
            <h4 style="border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 12px; margin-top: 24px;">Contributors</h4>
            <div id="drawerContributors">${contributorsHtml}</div>
        `;
    }

    drawer?.classList.add('open');
    overlay?.classList.add('open');

    try {
        const res = await apiFetch(`/api/tasks/${taskId}/contributors`);
        if(res.ok) {
            const contribs = await res.json();
            const contribContainer = document.getElementById('drawerContributors');
            if (contribContainer) {
                if(contribs.length === 0) {
                    contribContainer.innerHTML = '<p style="color:#64748b; font-size:13px;">No contributors found.</p>';
                } else {
                    let html = '<ul style="list-style:none; padding:0; margin:0; font-size:13px;">';
                    for(let c of contribs) {
                        html += `<li style="padding: 8px 0; border-bottom:1px solid #f1f5f9; display:flex; justify-content:space-between;">
                            <span><strong>${esc(c.student_name)}</strong> (${esc(c.nim_id)})</span>
                            <span style="color:#00919A; font-weight:bold;">${c.points} pts</span>
                        </li>`;
                    }
                    html += '</ul>';
                    contribContainer.innerHTML = html;
                }
            }
        } else {
            if(document.getElementById('drawerContributors'))
                document.getElementById('drawerContributors').innerHTML = '<p style="color:#ef4444; font-size:13px;">Failed to load contributors.</p>';
        }
    } catch(e) {
        if(document.getElementById('drawerContributors'))
            document.getElementById('drawerContributors').innerHTML = '<p style="color:#ef4444; font-size:13px;">Error loading contributors.</p>';
    }
}

/* ════════════════════════════════════════════════
    EDIT MODAL
    ════════════════════════════════════════════════ */
const editModal = document.getElementById('editModal');

window.openEdit = function(taskId) {
    const t = tasks.find(x => x.task_id === taskId);
    if (!t) return;
    
    document.getElementById('editTaskId').value = t.task_id || '';
    document.getElementById('editTaskName').value = t.task_name || '';
    document.getElementById('editType').value = t.type_id || '1';
    document.getElementById('editStatus').value = t.status_id || '1';
    document.getElementById('editStartDate').value = t.start_date || '';
    document.getElementById('editEndDate').value = t.end_date || '';
    document.getElementById('editPic').value = t.pic || '';
    document.getElementById('editLinks').value = t.related_links || '';
    document.getElementById('editDesc').value = t.description || '';
    
    editModal?.classList.add('open');
};

function closeEditModal() {
    editModal?.classList.remove('open');
}

document.getElementById('cancelEdit')?.addEventListener('click', closeEditModal);

document.getElementById('editTaskForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const taskId = document.getElementById('editTaskId').value;
    const saveBtn = e.target.querySelector('button[type="submit"]');
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';

    const payload = {
        task_name: document.getElementById('editTaskName').value,
        type_id: parseInt(document.getElementById('editType').value),
        status_id: parseInt(document.getElementById('editStatus').value),
        start_date: document.getElementById('editStartDate').value,
        end_date: document.getElementById('editEndDate').value,
        pic: document.getElementById('editPic').value,
        related_links: document.getElementById('editLinks').value,
        description: document.getElementById('editDesc').value,
    };

    try {
        const res = await apiFetch(`/api/tasks/${taskId}`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        if (res.ok) {
            const idx = tasks.findIndex(x => x.task_id === taskId);
            if(idx !== -1) {
                tasks[idx] = { ...tasks[idx], ...payload, type_name: TASK_TYPES[payload.type_id], status_name: TASK_STATUSES[payload.status_id] };
            }
            renderTable(document.getElementById('searchInput').value);
            closeEditModal();
            if(typeof showToast === 'function') showToast('Task updated successfully');
            
            // Wait a brief moment to show success before refreshing contributors UI if it is open
            if(drawer?.classList.contains('open')) {
                // If it was editing the same task being viewed
                openDetail(taskId);
            }
        } else {
            if(typeof showToast === 'function') showToast(data.error || 'Update failed', 'error');
        }
    } catch (err) {
        if(typeof showToast === 'function') showToast('Network error', 'error');
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = 'Save Changes';
    }
});

/* ════════════════════════════════════════════════
    DELETE LOGIC
    ════════════════════════════════════════════════ */
window.deleteTask = async function(taskId, taskName) {
    if (!confirm(`Are you sure you want to permanently delete task "${taskName}"?\nThis will remove it and all related contributions!`)) return;

    try {
        const res = await apiFetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
        const data = await res.json();

        if (res.ok) {
            tasks = tasks.filter(t => t.task_id !== taskId);
            renderTable(document.getElementById('searchInput')?.value || '');
            if(typeof showToast === 'function') showToast(data.message || 'Task deleted successfully');
        } else {
            if(typeof showToast === 'function') showToast(data.error || 'Failed to delete task', 'error');
        }
    } catch (err) {
        if(typeof showToast === 'function') showToast('Network error: ' + err.message, 'error');
    }
};
