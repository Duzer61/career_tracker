// Drag and Drop — HTML5 DnD + Touch long-press
function setupDragAndDrop() {
    let draggedCard = null;
    let sourceContainer = null;
    let touchGhost = null;
    let touchOffsetX = 0;
    let touchOffsetY = 0;
    let isTouchDragging = false;
    let longPressTimer = null;
    let touchStartTime = 0;
    let touchStartX = 0;
    let touchStartY = 0;
    const LONG_PRESS_DELAY = 400; // ms
    const MOVE_THRESHOLD = 10; // px

    // ========== MOUSE / HTML5 DnD ==========
    document.addEventListener('dragstart', (e) => {
        if (!e.target.classList.contains('card')) return;

        draggedCard = e.target;
        sourceContainer = e.target.parentElement;
        e.target.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
    });

    document.addEventListener('dragend', (e) => {
        if (draggedCard) {
            draggedCard.classList.remove('dragging');
            draggedCard = null;
        }
        if (sourceContainer) {
            sourceContainer.classList.remove('drag-over');
            sourceContainer = null;
        }
    });

    document.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        const container = e.target.closest('.cards-container');
        if (container && container !== sourceContainer && !container.classList.contains('drag-over')) {
            container.classList.add('drag-over');
        }
    });

    document.addEventListener('dragleave', (e) => {
        const container = e.target.closest('.cards-container');
        if (container) {
            container.classList.remove('drag-over');
        }
    });

    document.addEventListener('drop', async (e) => {
        e.preventDefault();
        const container = e.target.closest('.cards-container');
        if (!container || !draggedCard) return;

        container.classList.remove('drag-over');
        await handleDrop(container, draggedCard);
    });

    // ========== TOUCH ==========
    document.addEventListener('touchstart', (e) => {
        const card = e.target.closest('.card');
        if (!card) return;

        const touch = e.touches[0];
        touchStartX = touch.clientX;
        touchStartY = touch.clientY;
        touchStartTime = Date.now();

        // Запускаем таймер долгого нажатия
        longPressTimer = setTimeout(() => {
            isTouchDragging = true;
            draggedCard = card;
            sourceContainer = card.parentElement;
            card.classList.add('dragging');
            createTouchGhost(card, touch);
            // Виброотклик если доступен
            if (navigator.vibrate) navigator.vibrate(50);
        }, LONG_PRESS_DELAY);
    }, { passive: false });

    document.addEventListener('touchmove', (e) => {
        if (!isTouchDragging) {
            // Если двигаем палец до срабатывания long press — отменяем
            const touch = e.touches[0];
            const dx = Math.abs(touch.clientX - touchStartX);
            const dy = Math.abs(touch.clientY - touchStartY);
            if (dx > MOVE_THRESHOLD || dy > MOVE_THRESHOLD) {
                clearTimeout(longPressTimer);
                longPressTimer = null;
            }
            return;
        }

        e.preventDefault(); // Предотвращаем скролл страницы
        const touch = e.touches[0];
        updateTouchGhostPosition(touch);

        // Подсвечиваем колонку под пальцем
        const elementBelow = document.elementFromPoint(touch.clientX, touch.clientY);
        if (elementBelow) {
            document.querySelectorAll('.cards-container').forEach(c => c.classList.remove('drag-over'));
            const container = elementBelow.closest('.cards-container');
            if (container && container !== sourceContainer) {
                container.classList.add('drag-over');
            }
        }
    }, { passive: false });

    document.addEventListener('touchend', async (e) => {
        clearTimeout(longPressTimer);
        longPressTimer = null;

        if (!isTouchDragging) return;

        const touch = e.changedTouches[0];
        const elementBelow = document.elementFromPoint(touch.clientX, touch.clientY);

        removeTouchGhost();

        if (draggedCard) {
            draggedCard.classList.remove('dragging');
        }
        document.querySelectorAll('.cards-container').forEach(c => c.classList.remove('drag-over'));

        if (elementBelow) {
            const container = elementBelow.closest('.cards-container');
            if (container && draggedCard) {
                await handleDrop(container, draggedCard);
            }
        }

        draggedCard = null;
        sourceContainer = null;
        isTouchDragging = false;
    });

    document.addEventListener('touchcancel', () => {
        clearTimeout(longPressTimer);
        longPressTimer = null;
        removeTouchGhost();
        if (draggedCard) {
            draggedCard.classList.remove('dragging');
        }
        document.querySelectorAll('.cards-container').forEach(c => c.classList.remove('drag-over'));
        draggedCard = null;
        sourceContainer = null;
        isTouchDragging = false;
    });

    // ========== HELPERS ==========
    function createTouchGhost(card, touch) {
        touchGhost = card.cloneNode(true);
        touchGhost.classList.add('touch-ghost');
        touchGhost.style.width = card.offsetWidth + 'px';
        touchGhost.style.height = card.offsetHeight + 'px';

        const rect = card.getBoundingClientRect();
        touchOffsetX = touch.clientX - rect.left;
        touchOffsetY = touch.clientY - rect.top;

        updateTouchGhostPosition(touch);
        document.body.appendChild(touchGhost);
    }

    function updateTouchGhostPosition(touch) {
        if (!touchGhost) return;
        touchGhost.style.left = (touch.clientX - touchOffsetX) + 'px';
        touchGhost.style.top = (touch.clientY - touchOffsetY) + 'px';
    }

    function removeTouchGhost() {
        if (touchGhost) {
            touchGhost.remove();
            touchGhost = null;
        }
    }

    async function handleDrop(container, card) {
        const column = container.closest('.column');
        const newStatus = column.dataset.status;
        const applicationId = parseInt(card.dataset.applicationId);

        const app = applications.find(a => a.id === applicationId);
        if (!app || app.status === newStatus) return;

        const oldContainer = card.parentElement;
        const oldStatus = app.status;

        // 1. Мгновенно перемещаем карточку в новый столбец
        container.appendChild(card);

        // 2. Обновляем локальное состояние и счётчики колонок
        app.status = newStatus;
        updateColumnCounts();

        // 3. Отправляем запрос на сервер в фоне
        try {
            const response = await authenticatedFetch(`${API_BASE}/applications/${applicationId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus })
            });

            if (!response.ok) throw new Error('Server error');
        } catch (error) {
            // Откат при ошибке сети или сервера
            oldContainer.appendChild(card);
            app.status = oldStatus;
            updateColumnCounts();
            alert('Не удалось обновить статус заявки');
        }
    }
}