// ── Sync Toast ──────────────────────────────────────
const syncToast = document.getElementById('syncToast');
const syncSpinner = document.getElementById('syncSpinner');
const syncIcon = document.getElementById('syncIcon');
const syncText = document.getElementById('syncText');
let _toastTimer = null;

function showSyncToast(state, message) {
    clearTimeout(_toastTimer);
    syncToast.className = 'sync-toast show ' + state;
    syncText.textContent = message || { syncing: 'Syncing…', success: 'Saved ✓', error: 'Sync failed' }[state];
    syncSpinner.style.display = state === 'syncing' ? 'block' : 'none';
    syncIcon.style.display = state !== 'syncing' ? 'block' : 'none';
    if (state === 'success') {
        _toastTimer = setTimeout(() => { syncToast.classList.remove('show'); }, 2500);
    }
    if (state === 'error') {
        syncToast.onclick = () => { syncToast.classList.remove('show'); syncToast.onclick = null; };
    }
}

// ── Type/Status lookups ─────────────────────────────
const TASK_TYPES = { 1: 'Publication', 2: 'Event', 3: 'Camp' };
const TASK_STATUSES = { 1: 'Planning', 2: 'In-Progress', 3: 'Execution', 4: 'Documentation', 5: 'Lecturer Review', 6: 'Done', 7: 'Finished' };
const BADGE_CLASS = { 1: 'badge-publication', 2: 'badge-event', 3: 'badge-camp' };

// Map status_id to kanban column
function getColumnBody(statusId) {
    const sid = parseInt(statusId);
    if (sid === 1) return document.querySelector('.col-planning .column-body');
    if (sid === 2 || sid === 3) return document.querySelector('.col-doing .column-body');
    if (sid === 5) return document.querySelector('.col-review .column-body');
    if (sid === 6) return document.querySelector('.col-done .column-body');
    return document.querySelector('.col-planning .column-body');
}

function buildKanbanCard(t) {
    const typeName = TASK_TYPES[t.type_id] || '';
    const badgeCls = BADGE_CLASS[t.type_id] || 'badge-publication';
    return `<div class="kanban-card" data-task-id="${t.task_id}">
                <div class="card-title">${t.task_name}</div>
                <div class="card-meta">
                    <span>${t.start_date || ''} – ${t.end_date || ''}</span>
                    <span><span class="card-badge ${badgeCls}">${typeName}</span></span>
                </div>
                <div class="card-footer">
                    <span class="card-contributors">0 contributors</span>
                </div>
            </div>`;
}

// ── Modal logic ─────────────────────────────────────
const modal = document.getElementById('createTaskModal');
const openBtn = document.getElementById('openCreateModalBtn');
const closeBtn = document.getElementById('closeModalBtn');
const form = document.getElementById('createTaskForm');

openBtn.addEventListener('click', () => { modal.style.display = 'flex'; });
closeBtn.addEventListener('click', () => { modal.style.display = 'none'; form.reset(); });
window.addEventListener('click', (e) => { if (e.target === modal) { modal.style.display = 'none'; form.reset(); } });

// ── Create form submit (OPTIMISTIC) ─────────────────
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const inputs = form.querySelectorAll('.form-input, .form-select');
    const payload = {
        task_name: inputs[0].value,
        type_id: parseInt(inputs[1].value),
        start_date: inputs[2].value,
        end_date: inputs[3].value,
        status_id: parseInt(inputs[4].value)
    };

    // Optimistic: close modal, add temp card to proper column
    modal.style.display = 'none';
    const tempId = 'temp-' + Date.now();
    const tempTask = { ...payload, task_id: tempId };
    const targetColumn = getColumnBody(payload.status_id);

    // Remove "empty" placeholder if present
    const emptyPlaceholder = targetColumn.querySelector('.empty-col');
    if (emptyPlaceholder) emptyPlaceholder.remove();

    targetColumn.insertAdjacentHTML('afterbegin', buildKanbanCard(tempTask));

    // Update column count
    const columnHeader = targetColumn.previousElementSibling;
    const countEl = columnHeader.querySelector('.column-count');
    if (countEl) countEl.textContent = parseInt(countEl.textContent) + 1;

    form.reset();
    showSyncToast('syncing');

    try {
        const res = await fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (res.ok) {
            showSyncToast('success');
            // Update temp card with real task_id
            const tempCard = targetColumn.querySelector(`[data-task-id="${tempId}"]`);
            if (tempCard && data.task) {
                tempCard.dataset.taskId = data.task.task_id;
            }
        } else {
            // Remove temp card on error
            const tempCard = targetColumn.querySelector(`[data-task-id="${tempId}"]`);
            if (tempCard) tempCard.remove();
            if (countEl) countEl.textContent = parseInt(countEl.textContent) - 1;
            const msgs = Object.values(data.errors || {}).join('\n');
            showSyncToast('error', 'Error: ' + msgs);
        }
    } catch (err) {
        const tempCard = targetColumn.querySelector(`[data-task-id="${tempId}"]`);
        if (tempCard) tempCard.remove();
        showSyncToast('error', 'Network error');
    }
});
