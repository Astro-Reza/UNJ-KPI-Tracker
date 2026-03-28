function esc(str) {
    const d = document.createElement('div');
    d.textContent = str == null ? '' : String(str);
    return d.innerHTML;
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
        (t.task_name || '').toLowerCase().includes(q) ||
        (t.pic || '').toLowerCase().includes(q) ||
        (TASK_TYPES[t.type_id] || '').toLowerCase().includes(q) ||
        (TASK_STATUSES[t.status_id] || '').toLowerCase().includes(q)
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
        const res = await fetch('/api/export/sheets', { method: 'POST' });
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
