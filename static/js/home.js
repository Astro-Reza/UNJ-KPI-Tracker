// ── HTML Escaping ───────────────────────────────────
function esc(str) {
    const d = document.createElement('div');
    d.textContent = str == null ? '' : String(str);
    return d.innerHTML;
}

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
    // Auto-dismiss success after 2.5s
    if (state === 'success') {
        _toastTimer = setTimeout(() => { syncToast.classList.remove('show'); }, 2500);
    }
    // Error: click to dismiss
    if (state === 'error') {
        syncToast.onclick = () => { syncToast.classList.remove('show'); syncToast.onclick = null; };
    }
}

// ── Type/Status lookups ─────────────────────────────
const TASK_TYPES = { 1: 'Publication', 2: 'Event', 3: 'Camp' };
const TASK_STATUSES = { 1: 'Planning', 2: 'In-Progress', 3: 'Execution', 4: 'Documentation', 5: 'Lecturer Review', 6: 'Done', 7: 'Finished' };

// ── Create Modal logic ──────────────────────────────
const modal = document.getElementById('createTaskModal');
const openBtn = document.getElementById('openCreateModalBtn');
const closeBtn = document.getElementById('closeModalBtn');
const form = document.getElementById('createTaskForm');

// ── Edit Modal logic (Advanced Task Modal) ──────────
const editModal = document.getElementById('taskModal');
const bottomBar = document.getElementById('bottomBar');
const bottomTabsContainer = document.getElementById('bottomTabsContainer');
let minimizedTasks = new Map(); // Store state of minimized tasks

openBtn.addEventListener('click', () => {
    modal.style.display = 'flex';
});

closeBtn.addEventListener('click', () => {
    modal.style.display = 'none';
    form.reset();
});

window.addEventListener('click', (e) => {
    if (e.target === modal) {
        modal.style.display = 'none';
        form.reset();
    }
});

// ── Formatters ──────────────────────────────────────
const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const opts = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Asia/Jakarta' };
    return date.toLocaleDateString('en-GB', opts);
};

// ── Build a job-card HTML from task data ─────────────
function buildJobCardHTML(t) {
    const typeName = TASK_TYPES[t.type_id] || t.type_name || '';
    const statusName = TASK_STATUSES[t.status_id] || t.status_name || '';
    const contribCount = t.contributor_count || 0;
    const contribList = JSON.stringify(t.contributors_list || []);
    return `<div class="job-card"
                 style="cursor: pointer;"
                 data-task-id="${esc(t.task_id)}"
                 data-task-name="${esc(t.task_name)}"
                 data-type-id="${t.type_id}"
                 data-start-date="${esc(t.start_date || '')}"
                 data-end-date="${esc(t.end_date || '')}"
                 data-status-id="${t.status_id}"
                 data-contributor-count="${contribCount}"
                 data-contributors='${esc(contribList.replace(/'/g, '&#39;'))}'
                 data-pic="${esc(t.pic || '')}"
                 data-related-links="${esc(t.related_links || '')}"
                 data-description="${esc(t.description || '')}"
                 onclick="openEditModal(this)">
                <div class="job-title">${esc(t.task_name)}</div>
                <div class="card-divider"></div>
                <div class="job-info">
                    <div class="job-timeline">${esc(t.start_date || '')} – ${esc(t.end_date || '')}</div>
                    <div class="job-type">${esc(typeName)}</div>
                    <div class="job-contributors">${esc(statusName)} · ${contribCount} Contributors</div>
                </div>
            </div>`;
}

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

    // Optimistic: close modal, add temp card, show toast
    modal.style.display = 'none';
    const tempId = 'temp-' + Date.now();
    const tempTask = { ...payload, task_id: tempId, contributor_count: 0, contributors_list: [], pic: '', related_links: '', description: '' };
    const jobList = document.querySelector('.job-list');
    const placeholder = jobList.querySelector('.job-card:not([data-task-id])');
    if (placeholder) placeholder.remove();
    jobList.insertAdjacentHTML('afterbegin', buildJobCardHTML(tempTask));
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
            // Replace temp card with real data
            const tempCard = jobList.querySelector(`[data-task-id="${tempId}"]`);
            if (tempCard) {
                tempCard.outerHTML = buildJobCardHTML(data.task);
            }
            // Silently refresh dashboard sections
            refreshDashboard();
        } else {
            // Remove temp card on validation error
            const tempCard = jobList.querySelector(`[data-task-id="${tempId}"]`);
            if (tempCard) tempCard.remove();
            const msgs = Object.values(data.errors || {}).join('\n');
            showSyncToast('error', 'Error: ' + msgs);
        }
    } catch (err) {
        const tempCard = jobList.querySelector(`[data-task-id="${tempId}"]`);
        if (tempCard) tempCard.remove();
        showSyncToast('error', 'Network error');
    }
});

// ── Edit Modal open ─────────────────────────────────
function openEditModal(cardElement) {
    const ds = cardElement.dataset;
    
    // Check if task exists in minimized state. If so, maximize it directly.
    if (minimizedTasks.has(ds.taskId)) {
        maximizeApp();
        activateTab(ds.taskId);
        return; // already loaded in the modal
    }
    
    // Store core attributes on the modal div
    editModal.dataset.taskId = ds.taskId;
    editModal.dataset.taskName = ds.taskName;
    editModal.dataset.typeId = ds.typeId;
    editModal.dataset.startDate = ds.startDate;
    editModal.dataset.endDate = ds.endDate;
    editModal.dataset.statusId = ds.statusId;
        
    // 1. Text elements (Inputs)
    document.getElementById('tm-title-input').value = ds.taskName;
    document.getElementById('tm-start-date').value = ds.startDate ? ds.startDate.split(' ')[0] : '';
    document.getElementById('tm-end-date').value = ds.endDate ? ds.endDate.split(' ')[0] : '';
    document.getElementById('tm-contributor-count').textContent = ds.contributorCount;
    
    // Type and Status selects
    document.getElementById('tm-type-select').value = ds.typeId;
    document.getElementById('tm-status-select').value = ds.statusId;
    
    // Try mapping PIC directly from data and set input value
    document.getElementById('tm-pic-input').value = ds.pic || "";
    
    // Default related links
    document.getElementById('tm-links-input').value = ds.relatedLinks || "";
    
    // Description
    document.getElementById('tm-desc-input').value = ds.description || "";

    // Progress bar calculations
    const pct = parseInt(ds.statusId) * 20; // 5 statuses = 20% each
    document.getElementById('tm-progress').style.width = pct + '%';
    
    // Fetch real contributors from API
    const tbody = document.getElementById('tm-contributors-tbody');
    document.getElementById('tm-contributor-count').textContent = ds.contributorCount || '0';
    document.getElementById('tm-assigned-count').textContent = '...';
    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; opacity: 0.5;">Loading...</td></tr>`;
    
    fetch(`/api/tasks/${ds.taskId}/contributors`)
        .then(res => res.json())
        .then(contribs => {
            document.getElementById('tm-assigned-count').textContent = contribs.length;
            if (contribs.length > 0) {
                tbody.innerHTML = contribs.map(c => `
                    <tr data-nim="${esc(c.nim_id)}">
                        <td><input type="checkbox" class="student-cb"></td>
                        <td>${esc(c.name)}</td>
                        <td>${esc(c.nim_id)}</td>
                        <td>${esc(c.department)}</td>
                        <td><input type="number" class="cell-editable" value="${esc(c.points)}"></td>
                    </tr>
                `).join('');
            } else {
                // Fall back to contributor names from dataset (no points yet)
                let contributorsList = [];
                try {
                    contributorsList = JSON.parse(ds.contributors || '[]');
                } catch (e) {
                    console.error("Failed to parse contributors", ds.contributors);
                }
                if (contributorsList.length > 0) {
                    tbody.innerHTML = contributorsList.map(name => `
                        <tr>
                            <td><input type="checkbox" class="student-cb"></td>
                            <td>${esc(name)}</td>
                            <td>—</td>
                            <td>—</td>
                            <td><input type="number" class="cell-editable" value="0"></td>
                        </tr>
                    `).join('');
                    document.getElementById('tm-assigned-count').textContent = contributorsList.length;
                } else {
                    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; opacity: 0.7;">No contributors assigned yet.</td></tr>`;
                    document.getElementById('tm-assigned-count').textContent = '0';
                }
            }
        })
        .catch(err => {
            console.error('Failed to load contributors', err);
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: red;">Failed to load contributors</td></tr>`;
        });
    
    // Display Modal
    editModal.classList.remove('hidden-modal');
    bottomBar.classList.remove('show-bar');
    editModal.classList.add('show-modal');
}

// ── Modal Actions (Minimize/Maximize) ───────────────
function toggleFullscreen() {
    editModal.classList.toggle('fullscreen-mode');
}

function minimizeApp() {
    const taskId = editModal.dataset.taskId;
    const taskName = editModal.dataset.taskName;
    
    if (!taskId) return;
    
    // Add to minimized state array
    if (!minimizedTasks.has(taskId)) {
        minimizedTasks.set(taskId, { id: taskId, name: taskName });
        renderTabs();
    }
    
    editModal.classList.remove('show-modal');
    editModal.classList.add('hidden-modal');
    bottomBar.classList.add('show-bar');
    activateTab(taskId);
}

function maximizeApp() {
    bottomBar.classList.remove('show-bar');
    editModal.classList.remove('hidden-modal');
    editModal.classList.add('show-modal');
}

function closeApp() {
    const taskId = editModal.dataset.taskId;
    if (taskId) {
        minimizedTasks.delete(taskId);
        renderTabs();
    }
    
    editModal.classList.remove('show-modal');
    editModal.classList.add('hidden-modal');
    
    if (minimizedTasks.size === 0) {
        bottomBar.classList.remove('show-bar');
    }
    
    setTimeout(() => {
        editModal.classList.remove('fullscreen-mode');
    }, 400);
}

function renderTabs() {
    bottomTabsContainer.innerHTML = '';
    minimizedTasks.forEach((task, id) => {
        const div = document.createElement('div');
        div.className = id === editModal.dataset.taskId ? 'minimized-tab active' : 'minimized-tab inactive';
        div.textContent = task.name.length > 20 ? task.name.substring(0, 18) + '...' : task.name;
        div.title = `Restore ${task.name}`;
        
        div.onclick = () => {
            // Locate the card in the DOM to reload data
            const card = document.querySelector(`.job-card[data-task-id="${id}"]`);
            if (card) {
                openEditModal(card);
            }
            activateTab(id);
            maximizeApp();
        };
        bottomTabsContainer.appendChild(div);
    });
}

function activateTab(taskId) {
    const tabs = bottomTabsContainer.querySelectorAll('.minimized-tab');
    let idx = 0;
    minimizedTasks.forEach((t, id) => {
        if (id === taskId) {
            tabs[idx].classList.remove('inactive');
            tabs[idx].classList.add('active');
        } else {
            tabs[idx].classList.remove('active');
            tabs[idx].classList.add('inactive');
        }
        idx++;
    });
}

// ── Update & Delete Actions ─────────────────────────
async function deleteTask() {
    const taskId = editModal.dataset.taskId;
    if (!taskId) return;
    
    if (!confirm('Are you sure you want to completely delete this task? This cannot be undone.')) {
        return;
    }

    closeApp();
    showSyncToast('syncing');

    // Optimistically remove card
    const card = document.querySelector(`.job-card[data-task-id="${taskId}"]`);
    if (card) card.remove();

    try {
        const res = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
        if (res.ok) {
            showSyncToast('success', 'Deleted ✓');
            refreshDashboard();
        } else {
            showSyncToast('error', 'Delete failed');
        }
    } catch (err) {
        showSyncToast('error', 'Network error');
    }
}

async function finishTask() {
    const taskId = editModal.dataset.taskId;
    if (!taskId) return;
    
    // Set status to 7 (Finished) in the DOM
    document.getElementById('tm-status-select').value = "7";
    
    // Optimistically remove from home list
    const card = document.querySelector(`.job-card[data-task-id="${taskId}"]`);
    if (card) card.remove();
    
    saveTaskUpdates(); 
}

// ── Update Logic (OPTIMISTIC) ───────────────────────
async function saveTaskUpdates() {
    const taskId = editModal.dataset.taskId;
    
    // Read directly from the input fields
    const payload = {
        task_name: document.getElementById('tm-title-input').value,
        type_id: parseInt(document.getElementById('tm-type-select').value),
        start_date: document.getElementById('tm-start-date').value,
        end_date: document.getElementById('tm-end-date').value,
        status_id: parseInt(document.getElementById('tm-status-select').value),
        pic: document.getElementById('tm-pic-input').value,
        related_links: document.getElementById('tm-links-input').value,
        description: document.getElementById('tm-desc-input').value
    };

    // Optimistic: close modal immediately and update the card in the DOM
    closeApp();
    showSyncToast('syncing');

    // Update the card in the DOM optimistically
    const card = document.querySelector(`.job-card[data-task-id="${taskId}"]`);
    if (card) {
        card.dataset.taskName = payload.task_name;
        card.dataset.typeId = payload.type_id;
        card.dataset.startDate = payload.start_date;
        card.dataset.endDate = payload.end_date;
        card.dataset.statusId = payload.status_id;
        card.dataset.pic = payload.pic;
        card.dataset.relatedLinks = payload.related_links;
        card.dataset.description = payload.description;
        const titleEl = card.querySelector('.job-title');
        if (titleEl) titleEl.textContent = payload.task_name;
        const timelineEl = card.querySelector('.job-timeline');
        if (timelineEl) timelineEl.textContent = `${payload.start_date} – ${payload.end_date}`;
        const typeEl = card.querySelector('.job-type');
        if (typeEl) typeEl.textContent = TASK_TYPES[payload.type_id] || '';
        const contribEl = card.querySelector('.job-contributors');
        if (contribEl) {
            const statusName = TASK_STATUSES[payload.status_id] || '';
            contribEl.textContent = `${statusName} · ${card.dataset.contributorCount} Contributors`;
        }
    }

    // Collect contributor points data
    const rows = document.querySelectorAll('#tm-contributors-tbody tr[data-nim]');
    let contribPayload = [];
    if (rows.length > 0) {
        contribPayload = Array.from(rows).map(tr => ({
            nim_id: tr.dataset.nim,
            points: parseFloat(tr.querySelector('.cell-editable').value) || 0
        }));
    }

    try {
        // 1. Save main task fields
        const res = await fetch(`/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (!res.ok) {
            const msgs = Object.values(data.errors || {}).join('\n');
            showSyncToast('error', 'Error: ' + msgs);
            return;
        }
        
        // 2. Save contributor points (fire and forget-ish)
        if (contribPayload.length > 0) {
            await fetch(`/api/tasks/${taskId}/contributors`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(contribPayload)
            });
        }

        showSyncToast('success');
        // Silently refresh all dashboard sections with server data
        refreshDashboard();
    } catch (err) {
        showSyncToast('error', 'Sync failed');
    }
}

// ── AJAX Dashboard Partial Refresh ──────────────────
async function refreshDashboard() {
    try {
        const res = await fetch('/api/dashboard');
        if (!res.ok) return;
        const data = await res.json();
        
        // 1. Re-render job list (recently added tasks)
        const jobList = document.querySelector('.job-list');
        if (jobList && data.recent_tasks) {
            if (data.recent_tasks.length > 0) {
                jobList.innerHTML = data.recent_tasks.map(t => buildJobCardHTML(t)).join('');
            } else {
                jobList.innerHTML = '<div class="job-card"><div class="job-title" style="opacity:0.6;">No tasks created yet</div></div>';
            }
            // Re-apply search/sort if active
            updateTasksList();
        }

        // 2. Re-render leaderboard (top card)
        const overallWinner = document.querySelector('.overall-winner');
        if (overallWinner && data.top_overall) {
            overallWinner.querySelector('.name').textContent = data.top_overall.name_id.toUpperCase();
            overallWinner.querySelector('.score').textContent = data.top_overall.score;
        }

        // 3. Re-render department leaders
        const deptItems = document.querySelectorAll('.department-item');
        if (data.dept_leaders) {
            data.dept_leaders.forEach((leader, i) => {
                if (deptItems[i]) {
                    deptItems[i].querySelector('.department-name').textContent = leader.department_name.toUpperCase();
                    const winner = deptItems[i].querySelector('.department-winner');
                    if (winner) {
                        winner.children[0].textContent = leader.name;
                        winner.children[1].textContent = leader.score;
                    }
                }
            });
        }

        // 4. Re-render on-going projects
        const projectsContainer = document.querySelector('.bottom-card');
        if (projectsContainer && data.ongoing_projects !== undefined) {
            const projectsHeader = '<div class="projects-header">ON-GOING PROJECTS</div>';
            if (data.ongoing_projects.length > 0) {
                projectsContainer.innerHTML = projectsHeader + data.ongoing_projects.map(t => `
                    <div class="project-item">
                        <div class="project-title">${esc(t.task_name)}</div>
                        <div class="progress-track">
                            <div class="progress-fill" style="width: ${t.status_id * 25}%;"></div>
                        </div>
                        <div class="project-dates">
                            <div class="date-block">
                                <span class="date-label">Project Start</span>
                                <span class="date-value">${esc(t.start_date)}</span>
                            </div>
                            <div class="date-block right">
                                <span class="date-label">Project Ends</span>
                                <span class="date-value">${esc(t.end_date)}</span>
                            </div>
                        </div>
                    </div>
                `).join('');
            } else {
                projectsContainer.innerHTML = projectsHeader + '<div class="project-item"><div class="project-title" style="opacity:0.6;">No on-going projects yet</div></div>';
            }
        }

        // 5. Re-render upcoming projects and media log (the two task-widgets)
        const taskWidgets = document.querySelectorAll('.task-widget');
        if (taskWidgets.length >= 2) {
            // Upcoming projects (first widget)
            renderTaskWidget(taskWidgets[0], 'UPCOMING PROJECTS', data.upcoming_projects, 'No upcoming projects');
            // Media & design log (second widget)
            renderTaskWidget(taskWidgets[1], 'MEDIA & DESIGN LOG', data.media_log, 'No publications yet');
        }

    } catch (err) {
        console.error('Dashboard refresh failed', err);
    }
}

function renderTaskWidget(widget, label, tasks, emptyTitle) {
    const topTask = widget.querySelector('.top-task');
    if (topTask) {
        const labelEl = topTask.querySelector('.upcoming-label');
        if (labelEl) labelEl.textContent = label;
        const titleEl = topTask.querySelector('.top-task-title');
        const dateEl = topTask.querySelector('.top-task-date');
        if (tasks && tasks.length > 0) {
            if (titleEl) titleEl.textContent = tasks[0].task_name;
            if (dateEl) dateEl.textContent = tasks[0].start_date;
        } else {
            if (titleEl) titleEl.textContent = emptyTitle;
            if (dateEl) dateEl.textContent = '—';
        }
    }
    const taskList = widget.querySelector('.task-list');
    if (taskList) {
        if (tasks && tasks.length > 0) {
            taskList.innerHTML = tasks.map(t => `
                <div class="task-item">
                    <div class="task-title">${esc(t.task_name)}</div>
                    <div class="task-date">${esc(t.start_date)} – ${esc(t.end_date)}</div>
                </div>
            `).join('');
        } else {
            taskList.innerHTML = '<div class="task-item"><div class="task-title" style="opacity:0.6;">Nothing here yet</div></div>';
        }
    }
}

// ── Search and Sort functionality ───────────────────
const searchInput = document.getElementById('taskSearchInput');
const jobListContainer = document.querySelector('.job-list');

// Custom Dropdown logic
const dropdown = document.querySelector('.dropdown-container');
const header = dropdown.querySelector('.sort-header');
const headerText = dropdown.querySelector('.sort-header-text');
const mainIcon = document.getElementById('main-sort-icon');
const body = dropdown.querySelector('.dropdown-body');
const items = dropdown.querySelectorAll('.dropdown-item');

let currentSortOption = "End Date"; 
let isSortUp = false; 

function toggleDropdown() {
    body.classList.toggle('show');
}

header.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleDropdown();
});

items.forEach(item => {
    item.addEventListener('click', (e) => {
        e.stopPropagation();

        const selectedText = item.querySelector('.dropdown-item-text').textContent;

        if (selectedText === "No Sort") {
            currentSortOption = null;
            isSortUp = false;
            headerText.textContent = "Sort";
            mainIcon.src = "/static/sources/icon/sort.svg";
        } else {
            if (currentSortOption === selectedText) {
                isSortUp = !isSortUp;
            } else {
                currentSortOption = selectedText;
                isSortUp = false;
            }
            headerText.textContent = selectedText;
            mainIcon.src = isSortUp ? "/static/sources/icon/sort-up.svg" : "/static/sources/icon/sort-down.svg";
        }

        items.forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        body.classList.remove('show');

        updateTasksList();
    });
});

document.addEventListener('click', (e) => {
    if (!dropdown.contains(e.target)) {
        body.classList.remove('show');
    }
});

function updateTasksList() {
    const searchTerm = searchInput.value.toLowerCase();
    
    // Get all job cards inside the job-list container specifically
    let cards = Array.from(jobListContainer.querySelectorAll('.job-card'));
    
    // 1. Filter
    cards.forEach(card => {
        const titleElement = card.querySelector('.job-title');
        if (!titleElement) return; // Skip if it's the "No tasks" placeholder
        
        // Only act on cards that have the data attribute mapped
        if (card.dataset.taskName) {
            const taskName = card.dataset.taskName.toLowerCase();
            if (taskName.includes(searchTerm)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        }
    });

    // 2. Sort visible cards
    if (currentSortOption) {
        cards.sort((a, b) => {
            const dsA = a.dataset;
            const dsB = b.dataset;
            
            if (!dsA.taskName || !dsB.taskName) return 0; // Skip placeholders

            let result = 0;
            switch(currentSortOption) {
                case 'Letters':
                    result = dsA.taskName.localeCompare(dsB.taskName);
                    break;
                case 'Contributor':
                    result = parseInt(dsB.contributorCount) - parseInt(dsA.contributorCount); 
                    break;
                case 'Starting Date':
                    result = new Date(dsA.startDate) - new Date(dsB.startDate);
                    break;
                case 'End Date':
                    result = new Date(dsA.endDate) - new Date(dsB.endDate);
                    break;
                case 'Type':
                    result = parseInt(dsA.typeId) - parseInt(dsB.typeId);
                    break;
                case 'Status':
                    result = parseInt(dsA.statusId) - parseInt(dsB.statusId);
                    break;
            }

            // Invert logic if isSortUp is true (ascending instead of descending, etc.)
            return isSortUp ? result * -1 : result;
        });
        
        // Re-append to container in sorted order
        cards.forEach(card => jobListContainer.appendChild(card));
    }
}

searchInput.addEventListener('input', updateTasksList);
