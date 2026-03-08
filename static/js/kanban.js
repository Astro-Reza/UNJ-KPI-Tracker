const modal = document.getElementById('createTaskModal');
const openBtn = document.getElementById('openCreateModalBtn');
const closeBtn = document.getElementById('closeModalBtn');
const form = document.getElementById('createTaskForm');

openBtn.addEventListener('click', () => { modal.style.display = 'flex'; });
closeBtn.addEventListener('click', () => { modal.style.display = 'none'; form.reset(); });
window.addEventListener('click', (e) => { if (e.target === modal) { modal.style.display = 'none'; form.reset(); } });

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
        if (res.ok) { modal.style.display = 'none'; form.reset(); window.location.reload(); }
        else { alert('Validation error:\n' + Object.values(data.errors || {}).join('\n')); }
    } catch (err) { alert('Network error: ' + err.message); }
});
