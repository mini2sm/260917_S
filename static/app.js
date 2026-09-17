// Static option lists (kept in sync with app.py REGIONS / CATEGORIES)
const REGIONS = ['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
    '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주'];
const CATEGORIES = ['문화예술', '음식', '전통', '음악', '자연/생태', '불빛/조명', '기타'];

const STATUS_LABEL = { ongoing: '진행중', upcoming: '예정', ended: '종료' };

// State management
let currentFilter = {
    status: 'all',
    region: 'all',
    category: 'all',
    search: ''
};

let searchDebounceTimer = null;

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    initDateHeader();
    populateStaticOptions();
    loadDbStatus();
    loadFestivals();
    loadStats();
});

// Fill region/category selects with the static option lists
function populateStaticOptions() {
    const fill = (id, placeholder) => {
        const el = document.getElementById(id);
        if (!el) return;
        if (placeholder) {
            const opt = document.createElement('option');
            opt.value = 'all';
            opt.textContent = placeholder;
            el.appendChild(opt);
        }
        REGIONS_OR_CATEGORIES_FOR(id).forEach(v => {
            const opt = document.createElement('option');
            opt.value = v;
            opt.textContent = v;
            el.appendChild(opt);
        });
    };

    function REGIONS_OR_CATEGORIES_FOR(id) {
        return id.includes('category') ? CATEGORIES : REGIONS;
    }

    fill('filter-region', '모든 지역');
    fill('filter-category', '모든 테마');
    fill('quick-add-region', null);
    fill('modal-input-region', null);
    fill('modal-input-category', null);
}

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
        dateElem.textContent = `${today} • 오늘 떠나기 좋은 축제를 찾아보세요`;
    }
}

// Fetch festivals from backend
async function loadFestivals() {
    const params = new URLSearchParams();
    if (currentFilter.status !== 'all') params.append('status', currentFilter.status);
    if (currentFilter.region !== 'all') params.append('region', currentFilter.region);
    if (currentFilter.category !== 'all') params.append('category', currentFilter.category);
    if (currentFilter.search) params.append('search', currentFilter.search);

    try {
        const response = await fetch(`/api/festivals?${params.toString()}`);
        if (!response.ok) throw new Error('축제 목록을 불러오지 못했습니다.');
        const festivals = await response.json();
        renderFestivalList(festivals);
    } catch (err) {
        console.error(err);
        showToast('축제 목록을 불러오는데 실패했습니다.', 'error');
    }
}

// Fetch dashboard stats
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        if (!response.ok) return;
        const stats = await response.json();

        document.getElementById('stat-total').textContent = stats.total || 0;
        document.getElementById('stat-ongoing').textContent = stats.ongoing || 0;
        document.getElementById('stat-upcoming').textContent = stats.upcoming || 0;
        document.getElementById('stat-rate').textContent = `${stats.ongoing_rate || 0}%`;
        document.getElementById('progress-bar-fill').style.width = `${stats.ongoing_rate || 0}%`;
    } catch (err) {
        console.error(err);
    }
}

// Render Festival cards to DOM
function renderFestivalList(festivals) {
    const listContainer = document.getElementById('festival-list');
    const emptyState = document.getElementById('empty-state');

    listContainer.innerHTML = '';

    if (!festivals || festivals.length === 0) {
        emptyState.classList.remove('hidden');
        return;
    }

    emptyState.classList.add('hidden');

    festivals.forEach(festival => {
        const item = document.createElement('div');
        item.className = `todo-item ${festival.status === 'ended' ? 'ended' : ''}`;
        item.id = `festival-${festival.id}`;

        const statusLabel = STATUS_LABEL[festival.status] || festival.status;
        const statusBadgeClass = `badge-status-${festival.status}`;
        const dDayText = festival.status === 'upcoming' ? `D-${festival.d_day}`
            : festival.status === 'ongoing' ? '진행중'
            : `종료 D+${festival.d_day}`;

        const period = festival.start_date === festival.end_date
            ? festival.start_date
            : `${festival.start_date} ~ ${festival.end_date}`;
        const placeText = [festival.region, festival.city, festival.location].filter(Boolean).join(' · ');

        item.innerHTML = `
            <div class="festival-status-wrapper">
                <span class="badge ${statusBadgeClass}">${statusLabel}</span>
                <span class="d-day-text">${dDayText}</span>
            </div>

            <div class="todo-content">
                <div class="todo-title">${escapeHtml(festival.name)}</div>
                ${festival.description ? `<div class="todo-desc">${escapeHtml(festival.description)}</div>` : ''}
                <div class="todo-meta">
                    ${festival.category ? `<span class="badge badge-category">🏷️ ${escapeHtml(festival.category)}</span>` : ''}
                    ${placeText ? `<span class="badge badge-due">📍 ${escapeHtml(placeText)}</span>` : ''}
                    <span class="badge badge-due">🗓️ ${period}</span>
                </div>
            </div>

            <div class="todo-actions">
                <button class="btn-icon" onclick="event.stopPropagation(); editFestival(${JSON.stringify(festival).replace(/"/g, '&quot;')})" title="수정">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"></path>
                        <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                </button>
                <button class="btn-icon delete" onclick="event.stopPropagation(); deleteFestival(${festival.id})" title="삭제">
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

// Quick Add Handler — creates a 3-day festival starting today
async function handleQuickAdd(event) {
    event.preventDefault();
    const input = document.getElementById('quick-add-input');
    const regionSelect = document.getElementById('quick-add-region');
    const name = input.value.trim();
    if (!name) return;

    const today = new Date();
    const end = new Date();
    end.setDate(today.getDate() + 3);
    const toIso = d => d.toISOString().split('T')[0];

    try {
        const response = await fetch('/api/festivals', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                region: regionSelect.value,
                category: '기타',
                start_date: toIso(today),
                end_date: toIso(end)
            })
        });

        if (!response.ok) throw new Error('축제 등록에 실패했습니다.');
        input.value = '';
        showToast('새 축제가 추가되었습니다.', 'success');
        await loadFestivals();
        await loadStats();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// Delete Festival
async function deleteFestival(id) {
    if (!confirm('이 축제 정보를 삭제하시겠습니까?')) return;

    try {
        const response = await fetch(`/api/festivals/${id}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('삭제 실패');
        showToast('축제 정보가 삭제되었습니다.', 'info');
        await loadFestivals();
        await loadStats();
    } catch (err) {
        showToast('삭제 중 오류가 발생했습니다.', 'error');
    }
}

// Clear Ended
async function clearEndedFestivals() {
    if (!confirm('종료된 모든 축제를 목록에서 삭제하시겠습니까?')) return;

    try {
        const response = await fetch('/api/festivals/clear-ended', { method: 'POST' });
        const result = await response.json();
        showToast(`${result.deleted || 0}개의 종료 항목이 삭제되었습니다.`, 'info');
        await loadFestivals();
        await loadStats();
    } catch (err) {
        showToast('종료 항목 삭제 중 오류가 발생했습니다.', 'error');
    }
}

// Modal Handlers
function openFestivalModal() {
    document.getElementById('modal-title').textContent = '새 축제 등록';
    document.getElementById('modal-festival-id').value = '';
    document.getElementById('modal-input-name').value = '';
    document.getElementById('modal-input-region').value = REGIONS[0];
    document.getElementById('modal-input-city').value = '';
    document.getElementById('modal-input-category').value = CATEGORIES[CATEGORIES.length - 1];
    document.getElementById('modal-input-start').value = '';
    document.getElementById('modal-input-end').value = '';
    document.getElementById('modal-input-location').value = '';
    document.getElementById('modal-input-desc').value = '';
    document.getElementById('modal-submit-btn').textContent = '등록하기';
    document.getElementById('festival-modal').classList.remove('hidden');
    document.getElementById('modal-input-name').focus();
}

function editFestival(festival) {
    document.getElementById('modal-title').textContent = '축제 정보 수정';
    document.getElementById('modal-festival-id').value = festival.id;
    document.getElementById('modal-input-name').value = festival.name;
    document.getElementById('modal-input-region').value = festival.region || REGIONS[0];
    document.getElementById('modal-input-city').value = festival.city || '';
    document.getElementById('modal-input-category').value = festival.category || CATEGORIES[CATEGORIES.length - 1];
    document.getElementById('modal-input-start').value = festival.start_date || '';
    document.getElementById('modal-input-end').value = festival.end_date || '';
    document.getElementById('modal-input-location').value = festival.location || '';
    document.getElementById('modal-input-desc').value = festival.description || '';
    document.getElementById('modal-submit-btn').textContent = '수정 완료';
    document.getElementById('festival-modal').classList.remove('hidden');
}

function closeFestivalModal() {
    document.getElementById('festival-modal').classList.add('hidden');
}

function handleModalBackdropClick(event) {
    if (event.target.id === 'festival-modal') {
        closeFestivalModal();
    }
}

// Modal Form Submit
async function handleModalSubmit(event) {
    event.preventDefault();
    const id = document.getElementById('modal-festival-id').value;
    const name = document.getElementById('modal-input-name').value.trim();
    const region = document.getElementById('modal-input-region').value;
    const city = document.getElementById('modal-input-city').value.trim();
    const category = document.getElementById('modal-input-category').value;
    const start_date = document.getElementById('modal-input-start').value;
    const end_date = document.getElementById('modal-input-end').value;
    const location = document.getElementById('modal-input-location').value.trim();
    const description = document.getElementById('modal-input-desc').value.trim();

    if (!name) {
        showToast('축제명을 입력해주세요.', 'error');
        return;
    }
    if (!start_date) {
        showToast('시작일을 입력해주세요.', 'error');
        return;
    }

    const payload = { name, region, city, category, start_date, end_date, location, description };

    try {
        let response;
        if (id) {
            response = await fetch(`/api/festivals/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } else {
            response = await fetch('/api/festivals', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        if (!response.ok) throw new Error('저장에 실패했습니다.');

        closeFestivalModal();
        showToast(id ? '축제 정보가 수정되었습니다.' : '새 축제가 추가되었습니다.', 'success');
        await loadFestivals();
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
    loadFestivals();
}

function applyFilters() {
    currentFilter.region = document.getElementById('filter-region').value;
    currentFilter.category = document.getElementById('filter-category').value;
    loadFestivals();
}

function handleSearch() {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        currentFilter.search = document.getElementById('search-input').value.trim();
        loadFestivals();
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
