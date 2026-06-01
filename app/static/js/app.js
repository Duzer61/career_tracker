// Entry point — DOM initialization and event delegation

// DOM references — initialized in initDomRefs() after DOMContentLoaded
let addApplicationBtn, sortBtn, searchInput, searchClearBtn, filterToggleBtn, filterBar;
let logoutBtn, cancelBtn, closeViewBtn, cancelDeleteBtn, confirmDeleteBtn;
let cancelLogoutBtn, confirmLogoutBtn, applicationForm, loginForm, registerForm, applyRangeBtn;
let applicationModal, viewModal, deleteModal;
let kanbanBoard;

function initDomRefs() {
    addApplicationBtn = document.getElementById('add-application-btn');
    sortBtn = document.getElementById('sort-btn');
    searchInput = document.getElementById('search-input');
    searchClearBtn = document.getElementById('search-clear-btn');
    filterToggleBtn = document.getElementById('filter-toggle-btn');
    filterBar = document.getElementById('filter-bar');
    logoutBtn = document.getElementById('logout-btn');
    cancelBtn = document.getElementById('cancel-btn');
    closeViewBtn = document.getElementById('close-view-btn');
    cancelDeleteBtn = document.getElementById('cancel-delete-btn');
    confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    cancelLogoutBtn = document.getElementById('cancel-logout-btn');
    confirmLogoutBtn = document.getElementById('confirm-logout-btn');
    applicationForm = document.getElementById('application-form');
    loginForm = document.getElementById('login-form');
    registerForm = document.getElementById('register-form');
    applyRangeBtn = document.getElementById('apply-range-btn');

    applicationModal = document.getElementById('application-modal');
    viewModal = document.getElementById('view-modal');
    deleteModal = document.getElementById('delete-modal');
    kanbanBoard = document.getElementById('kanban-board');
}

function setupEventListeners() {
    // Auth forms
    if (loginForm) loginForm.addEventListener('submit', handleLogin);
    if (registerForm) registerForm.addEventListener('submit', handleRegister);

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Add application
    if (addApplicationBtn) addApplicationBtn.addEventListener('click', () => openApplicationModal());

    // Sort toggle
    if (sortBtn) sortBtn.addEventListener('click', toggleSort);

    // Search
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            searchQuery = searchInput.value.trim();
            if (searchClearBtn) searchClearBtn.classList.toggle('hidden', !searchQuery);
            renderKanbanBoard();
        });
    }

    if (searchClearBtn) {
        searchClearBtn.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            searchQuery = '';
            searchClearBtn.classList.add('hidden');
            renderKanbanBoard();
        });
    }

    // Filter toggle (mobile)
    if (filterToggleBtn) {
        filterToggleBtn.addEventListener('click', () => {
            if (filterBar) filterBar.classList.toggle('filter-bar-collapsed');
        });
    }

    // Filter period buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => setFilterPeriod(btn.dataset.period));
    });

    // Custom range apply
    if (applyRangeBtn) applyRangeBtn.addEventListener('click', applyCustomRange);

    // Logout
    if (logoutBtn) logoutBtn.addEventListener('click', showLogoutModal);
    if (cancelLogoutBtn) cancelLogoutBtn.addEventListener('click', closeLogoutModal);
    if (confirmLogoutBtn) confirmLogoutBtn.addEventListener('click', handleLogout);

    // Application form
    if (applicationForm) applicationForm.addEventListener('submit', handleApplicationSubmit);
    if (cancelBtn) cancelBtn.addEventListener('click', closeApplicationModal);

    // Close modals on X click
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', () => {
            closeApplicationModal();
            closeViewModal();
            closeDeleteModal();
            closeLogoutModal();
        });
    });

    // View modal close
    if (closeViewBtn) closeViewBtn.addEventListener('click', closeViewModal);

    // Delete modal
    if (cancelDeleteBtn) cancelDeleteBtn.addEventListener('click', closeDeleteModal);
    if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', handleConfirmDelete);

    // Wheel — горизонтальная прокрутка доски колёсиком мыши
    kanbanBoard.addEventListener('wheel', (e) => {
        if (e.target.closest('.cards-container')) {
            return;
        }
        e.preventDefault();
        kanbanBoard.scrollLeft += e.deltaY * 1.5;
    }, { passive: false });

    // Панорамирование доски через Пробел + перетаскивание мышью
    let spacePressed = false;
    let panStartX = 0;
    let panStartScrollLeft = 0;
    let isPanning = false;
    let panRafId = null;

    document.addEventListener('keydown', (e) => {
        if (e.code === 'Space') {
            const tag = e.target.tagName;
            if (tag === 'INPUT' || tag === 'TEXTAREA' || e.target.isContentEditable) {
                return;
            }
            spacePressed = true;
            e.preventDefault();
            kanbanBoard.classList.add('pan-active');
        }
    });

    document.addEventListener('keyup', (e) => {
        if (e.code === 'Space') {
            spacePressed = false;
            if (isPanning) {
                isPanning = false;
                kanbanBoard.classList.remove('pan-grabbing');
                document.body.style.userSelect = '';
                if (panRafId) {
                    cancelAnimationFrame(panRafId);
                    panRafId = null;
                }
            }
            kanbanBoard.classList.remove('pan-active', 'pan-grabbing');
        }
    });

    kanbanBoard.addEventListener('mousedown', (e) => {
        if (!spacePressed) return;
        if (e.target.closest('input, textarea, [contenteditable]')) return;
        e.preventDefault();
        isPanning = true;
        panStartX = e.clientX;
        panStartScrollLeft = kanbanBoard.scrollLeft;
        kanbanBoard.classList.add('pan-grabbing');
        document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', (e) => {
        if (!isPanning) return;
        e.preventDefault();
        if (panRafId) {
            cancelAnimationFrame(panRafId);
        }
        const clientX = e.clientX;
        panRafId = requestAnimationFrame(() => {
            kanbanBoard.scrollLeft = panStartScrollLeft - (clientX - panStartX);
            panRafId = null;
        });
    });

    document.addEventListener('mouseup', () => {
        if (isPanning) {
            isPanning = false;
            kanbanBoard.classList.remove('pan-grabbing');
            document.body.style.userSelect = '';
            if (panRafId) {
                cancelAnimationFrame(panRafId);
                panRafId = null;
            }
        }
    });

    document.addEventListener('mouseleave', () => {
        if (isPanning) {
            isPanning = false;
            kanbanBoard.classList.remove('pan-grabbing');
            document.body.style.userSelect = '';
            if (panRafId) {
                cancelAnimationFrame(panRafId);
                panRafId = null;
            }
        }
    });

    // Delegated events for cards (view, edit, delete)
    if (kanbanBoard) {
        kanbanBoard.addEventListener('click', (e) => {
            const viewBtn = e.target.closest('.card-btn.view');
            const editBtn = e.target.closest('.card-btn.edit');
            const deleteBtn = e.target.closest('.card-btn.delete');

            if (viewBtn) {
                const card = viewBtn.closest('.card');
                const app = applications.find(a => a.id === parseInt(card.dataset.applicationId));
                openViewModal(app);
            } else if (editBtn) {
                const card = editBtn.closest('.card');
                const app = applications.find(a => a.id === parseInt(card.dataset.applicationId));
                openApplicationModal(app);
            } else if (deleteBtn) {
                const card = deleteBtn.closest('.card');
                showDeleteModal(parseInt(card.dataset.applicationId));
            }
        });
    }

    // Drag and drop
    setupDragAndDrop();

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Close modals on Escape
        if (e.key === 'Escape') {
            closeApplicationModal();
            closeViewModal();
            closeDeleteModal();
            closeLogoutModal();
        }

        // Enter to confirm logout
        const logoutModal = document.getElementById('logout-modal');
        if (e.key === 'Enter' && logoutModal && !logoutModal.classList.contains('hidden')) {
            handleLogout();
        }
    });
}

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    initDomRefs();
    setupEventListeners();
    checkAuth();
});

// Expose for testing
window.CareerTracker = {
    loadApplications,
    deleteApplication,
    updateApplicationStatus
};