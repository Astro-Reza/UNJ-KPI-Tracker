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

// ── Create form submit ──────────────────────────────
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

    try {
        const res = await fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (res.ok) {
            modal.style.display = 'none';
            form.reset();
            window.location.reload();
        } else {
            const msgs = Object.values(data.errors || {}).join('\n');
            alert('Validation error:\n' + msgs);
        }
    } catch (err) {
        alert('Network error: ' + err.message);
    }
});

// ── Formatters ──────────────────────────────────────
const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const opts = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Asia/Jakarta' };
    return date.toLocaleDateString('en-GB', opts);
};

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
                    <tr data-nim="${c.nim_id}">
                        <td><input type="checkbox" class="student-cb"></td>
                        <td>${c.name}</td>
                        <td>${c.nim_id}</td>
                        <td>${c.department}</td>
                        <td><input type="number" class="cell-editable" value="${c.points}"></td>
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
                            <td>${name}</td>
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

// ── Update Logic ────────────────────────────────────
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
            alert('Validation error:\n' + msgs);
            return;
        }
        
        // 2. Save contributor points
        const rows = document.querySelectorAll('#tm-contributors-tbody tr[data-nim]');
        if (rows.length > 0) {
            const contribPayload = Array.from(rows).map(tr => ({
                nim_id: tr.dataset.nim,
                points: parseFloat(tr.querySelector('.cell-editable').value) || 0
            }));
            await fetch(`/api/tasks/${taskId}/contributors`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(contribPayload)
            });
        }

        closeApp();
        window.location.reload();
    } catch (err) {
        alert('Network error: ' + err.message);
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
