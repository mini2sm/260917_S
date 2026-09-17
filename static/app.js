// State management
let currentFilter = {
    status: 'all',
    priority: 'all',
    category: 'all',
    search: ''
};

let searchDebounceTimer = null;

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    initDateHeader();
    loadDbStatus();
    loadTodos();
    loadStats();
});

// Load and display database connection status
async function loadDbStatus() {
    const badge = document.getElementById('db-badge');
    const nameElem = document.getElementById('db-name');
    if (!badge || !nameElem) return;

    try {
        const res = await fetch('/api/db-status');
        if (!res.ok) return;
        const data = await res.json();
        if (data.is_supabase) {
            badge.classList.add('supabase');
            nameElem.textContent = 'Supabase 연결됨';
        } else {
            badge.classList.remove('supabase');
            nameElem.textContent = 'SQLite (로컬)';
        }
    } catch (e) {
        nameElem.textContent = 'DB 상태 확인 불가';
    }
}

// Format and set current date in header
function initDateHeader() {
    const options = { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' };
    const today = new Date().toLocaleDateString('ko-KR', options);
    const dateElem = document.getElementById('current-date-text');
    if (dateElem) {
        dateElem.textContent = `${today} • 생산적인 하루를 시작하세요`;
    }
}

// Fetch todos from backend
async function loadTodos() {
    const params = new URLSearchParams();
    if (currentFilter.status !== 'all') params.append('status', currentFilter.status);
    if (currentFilter.priority !== 'all') params.append('priority', currentFilter.priority);
    if (currentFilter.category !== 'all') params.append('category', currentFilter.category);
    if (currentFilter.search) params.append('search', currentFilter.search);

    try {
        const response = await fetch(`/api/todos?${params.toString()}`);
        if (!response.ok) throw new Error('할일 목록을 불러오지 못했습니다.');
        const todos = await response.json();
        renderTodoList(todos);
    } catch (err) {
        console.error(err);
        showToast('할일 목록을 불러오는데 실패했습니다.', 'error');
    }
}

// Fetch dashboard stats
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        if (!response.ok) return;
        const stats = await response.json();

        document.getElementById('stat-total').textContent = stats.total || 0;
        document.getElementById('stat-active').textContent = stats.active || 0;
        document.getElementById('stat-completed').textContent = stats.completed || 0;
        document.getElementById('stat-rate').textContent = `${stats.completion_rate || 0}%`;
        document.getElementById('progress-bar-fill').style.width = `${stats.completion_rate || 0}%`;

        // Update category filter dropdown if new categories exist
        updateCategoryOptions(stats.categories);
    } catch (err) {
        console.error(err);
    }
}

function updateCategoryOptions(categories) {
    if (!categories) return;
    const categorySelect = document.getElementById('filter-category');
    const existing = Array.from(categorySelect.options).map(o => o.value);
    
    categories.forEach(cat => {
        if (cat && !existing.includes(cat)) {
            const opt = document.createElement('option');
            opt.value = cat;
            opt.textContent = cat;
            categorySelect.appendChild(opt);
        }
    });
}

// Render Todo items to DOM
function renderTodoList(todos) {
    const listContainer = document.getElementById('todo-list');
    const emptyState = document.getElementById('empty-state');

    listContainer.innerHTML = '';

    if (!todos || todos.length === 0) {
        emptyState.classList.remove('hidden');
        return;
    }

    emptyState.classList.add('hidden');

    todos.forEach(todo => {
        const item = document.createElement('div');
        item.className = `todo-item ${todo.completed ? 'completed' : ''}`;
        item.id = `todo-${todo.id}`;

        const priorityLabel = todo.priority === 'high' ? '높음' : todo.priority === 'low' ? '낮음' : '보통';
        const priorityBadgeClass = `badge-priority-${todo.priority}`;

        item.innerHTML = `
            <div class="todo-checkbox-wrapper" onclick="toggleTodoStatus(${todo.id}, ${todo.completed})">
                <div class="todo-checkbox">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                        <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                </div>
            </div>

            <div class="todo-content" onclick="toggleTodoStatus(${todo.id}, ${todo.completed})">
                <div class="todo-title">${escapeHtml(todo.title)}</div>
                ${todo.description ? `<div class="todo-desc">${escapeHtml(todo.description)}</div>` : ''}
                <div class="todo-meta">
                    <span class="badge ${priorityBadgeClass}">${priorityLabel}</span>
                    ${todo.category ? `<span class="badge badge-category">📁 ${escapeHtml(todo.category)}</span>` : ''}
                    ${todo.due_date ? `<span class="badge badge-due">🗓️ ${todo.due_date}</span>` : ''}
                </div>
            </div>

            <div class="todo-actions">
                <button class="btn-icon" onclick="event.stopPropagation(); editTodo(${JSON.stringify(todo).replace(/"/g, '&quot;')})" title="수정">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"></path>
                        <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                </button>
                <button class="btn-icon delete" onclick="event.stopPropagation(); deleteTodo(${todo.id})" title="삭제">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"></path>
                    </svg>
                </button>
            </div>
        `;
        listContainer.appendChild(item);
    });
}

// Quick Add Handler
async function handleQuickAdd(event) {
    event.preventDefault();
    const input = document.getElementById('quick-add-input');
    const prioritySelect = document.getElementById('quick-add-priority');
    const title = input.value.trim();
    if (!title) return;

    try {
        const response = await fetch('/api/todos', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: title,
                priority: prioritySelect.value,
                category: '일반'
            })
        });

        if (!response.ok) throw new Error('할일 등록에 실패했습니다.');
        input.value = '';
        showToast('새 할일이 추가되었습니다.', 'success');
        await loadTodos();
        await loadStats();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Toggle Complete
async function toggleTodoStatus(id, currentCompleted) {
    try {
        const response = await fetch(`/api/todos/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ completed: currentCompleted ? 0 : 1 })
        });

        if (!response.ok) throw new Error('상태 변경 실패');
        await loadTodos();
        await loadStats();
    } catch (err) {
        showToast('상태 변경 중 오류가 발생했습니다.', 'error');
    }
}

// Delete Todo
async function deleteTodo(id) {
    if (!confirm('이 할일을 삭제하시겠습니까?')) return;

    try {
        const response = await fetch(`/api/todos/${id}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('삭제 실패');
        showToast('할일이 삭제되었습니다.', 'info');
        await loadTodos();
        await loadStats();
    } catch (err) {
        showToast('삭제 중 오류가 발생했습니다.', 'error');
    }
}

// Clear Completed
async function clearCompletedTodos() {
    if (!confirm('완료된 모든 할일을 목록에서 삭제하시겠습니까?')) return;

    try {
        const response = await fetch('/api/todos/clear-completed', { method: 'POST' });
        const result = await response.json();
        showToast(`${result.deleted || 0}개의 완료 항목이 삭제되었습니다.`, 'info');
        await loadTodos();
        await loadStats();
    } catch (err) {
        showToast('완료 항목 삭제 중 오류가 발생했습니다.', 'error');
    }
}

// Modal Handlers
function openTodoModal() {
    document.getElementById('modal-title').textContent = '새 할일 추가';
    document.getElementById('modal-todo-id').value = '';
    document.getElementById('modal-input-title').value = '';
    document.getElementById('modal-input-desc').value = '';
    document.getElementById('modal-input-priority').value = 'medium';
    document.getElementById('modal-input-category').value = '일반';
    document.getElementById('modal-input-due').value = '';
    document.getElementById('modal-submit-btn').textContent = '추가하기';
    document.getElementById('todo-modal').classList.remove('hidden');
    document.getElementById('modal-input-title').focus();
}

function editTodo(todo) {
    document.getElementById('modal-title').textContent = '할일 수정';
    document.getElementById('modal-todo-id').value = todo.id;
    document.getElementById('modal-input-title').value = todo.title;
    document.getElementById('modal-input-desc').value = todo.description || '';
    document.getElementById('modal-input-priority').value = todo.priority || 'medium';
    document.getElementById('modal-input-category').value = todo.category || '일반';
    document.getElementById('modal-input-due').value = todo.due_date || '';
    document.getElementById('modal-submit-btn').textContent = '수정 완료';
    document.getElementById('todo-modal').classList.remove('hidden');
}

function closeTodoModal() {
    document.getElementById('todo-modal').classList.add('hidden');
}

function handleModalBackdropClick(event) {
    if (event.target.id === 'todo-modal') {
        closeTodoModal();
    }
}

// Modal Form Submit
async function handleModalSubmit(event) {
    event.preventDefault();
    const id = document.getElementById('modal-todo-id').value;
    const title = document.getElementById('modal-input-title').value.trim();
    const description = document.getElementById('modal-input-desc').value.trim();
    const priority = document.getElementById('modal-input-priority').value;
    const category = document.getElementById('modal-input-category').value.trim() || '일반';
    const due_date = document.getElementById('modal-input-due').value;

    if (!title) {
        showToast('제목을 입력해주세요.', 'error');
        return;
    }

    const payload = { title, description, priority, category, due_date };

    try {
        let response;
        if (id) {
            response = await fetch(`/api/todos/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } else {
            response = await fetch('/api/todos', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        if (!response.ok) throw new Error('저장에 실패했습니다.');
        
        closeTodoModal();
        showToast(id ? '할일이 수정되었습니다.' : '새 할일이 추가되었습니다.', 'success');
        await loadTodos();
        await loadStats();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Filtering & Search
function filterByStatus(status, btnElement) {
    currentFilter.status = status;
    document.querySelectorAll('.pill-btn').forEach(btn => btn.classList.remove('active'));
    btnElement.classList.add('active');
    loadTodos();
}

function applyFilters() {
    currentFilter.priority = document.getElementById('filter-priority').value;
    currentFilter.category = document.getElementById('filter-category').value;
    loadTodos();
}

function handleSearch() {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        currentFilter.search = document.getElementById('search-input').value.trim();
        loadTodos();
    }, 250);
}

// Utilities
function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, m => map[m]);
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}
