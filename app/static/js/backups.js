// Backup management for the admin page
// Depends on: utils.js (formatDateTime), api.js (authenticatedFetch),
//             admin.js (global showToast)

// State
let backupDeleteName = null;

// DOM references
const backupsTbody = document.getElementById('backups-tbody');
const backupsEmpty = document.getElementById('backups-empty');
const backupCount = document.getElementById('backup-count');
const createBackupBtn = document.getElementById('create-backup-btn');
const backupDeleteModal = document.getElementById('backup-delete-modal');
const backupDeleteNameEl = document.getElementById('backup-delete-name');
const confirmBackupDeleteBtn = document.getElementById('confirm-backup-delete-btn');
const cancelBackupDeleteBtn = document.getElementById('cancel-backup-delete-btn');

const BACKUPS_API = `${API_BASE}/admin/backups`;

// Wire backup panel events. Called from admin.js once the admin guard passes.
function initBackups() {
    createBackupBtn.addEventListener('click', createBackup);

    // Download / delete via event delegation on tbody
    backupsTbody.addEventListener('click', (e) => {
        const downloadBtn = e.target.closest('.btn-backup-download');
        if (downloadBtn) {
            downloadBackup(downloadBtn.dataset.filename);
            return;
        }
        const deleteBtn = e.target.closest('.btn-backup-delete');
        if (deleteBtn) {
            openBackupDeleteModal(deleteBtn.dataset.filename);
        }
    });

    confirmBackupDeleteBtn.addEventListener('click', confirmBackupDelete);
    cancelBackupDeleteBtn.addEventListener('click', closeBackupDeleteModal);
    backupDeleteModal.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', closeBackupDeleteModal);
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeBackupDeleteModal();
    });
}

async function loadBackups() {
    try {
        const response = await authenticatedFetch(BACKUPS_API);
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'Ошибка загрузки резервных копий');
        }
        const data = await response.json();
        renderBackups(data.backups || []);
    } catch (error) {
        showToast('Ошибка загрузки резервных копий: ' + error.message, 'error');
    }
}

function renderBackups(backups) {
    const hasBackups = backups.length > 0;

    backupCount.textContent = backups.length;
    backupsEmpty.classList.toggle('hidden', hasBackups);
    backupsTbody.innerHTML = '';

    if (!hasBackups) return;

    for (const backup of backups) {
        const tr = document.createElement('tr');

        const dateTd = document.createElement('td');
        dateTd.dataset.label = 'Дата создания';
        dateTd.textContent = formatDateTime(backup.created_at);

        const nameTd = document.createElement('td');
        nameTd.dataset.label = 'Имя файла';
        nameTd.textContent = backup.filename;

        const sizeTd = document.createElement('td');
        sizeTd.dataset.label = 'Размер';
        sizeTd.textContent = backup.size_human;

        const actionsTd = document.createElement('td');
        actionsTd.dataset.label = 'Действия';

        const downloadBtn = document.createElement('button');
        downloadBtn.type = 'button';
        downloadBtn.className = 'btn-backup-download';
        downloadBtn.dataset.filename = backup.filename;
        downloadBtn.textContent = '⬇ Скачать';

        const deleteBtn = document.createElement('button');
        deleteBtn.type = 'button';
        deleteBtn.className = 'btn-backup-delete';
        deleteBtn.dataset.filename = backup.filename;
        deleteBtn.textContent = '🗑 Удалить';

        actionsTd.appendChild(downloadBtn);
        actionsTd.appendChild(deleteBtn);

        tr.appendChild(dateTd);
        tr.appendChild(nameTd);
        tr.appendChild(sizeTd);
        tr.appendChild(actionsTd);
        backupsTbody.appendChild(tr);
    }
}

async function createBackup() {
    // pg_dump may take a while (up to BACKUP_TIMEOUT_SECONDS): lock the button.
    createBackupBtn.disabled = true;
    createBackupBtn.textContent = 'Создание копии...';

    try {
        const response = await authenticatedFetch(BACKUPS_API, {
            method: 'POST',
        });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'Ошибка создания резервной копии');
        }
        const backup = await response.json();
        showToast(`Копия создана: ${backup.filename} (${backup.size_human})`, 'success');
        await loadBackups();
    } catch (error) {
        showToast('Ошибка: ' + error.message, 'error');
    } finally {
        createBackupBtn.disabled = false;
        createBackupBtn.textContent = '+ Создать копию';
    }
}

async function downloadBackup(filename) {
    try {
        const url = `${BACKUPS_API}/${encodeURIComponent(filename)}/download`;
        const response = await authenticatedFetch(url);
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'Ошибка скачивания копии');
        }
        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = objectUrl;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(objectUrl);
    } catch (error) {
        showToast('Ошибка скачивания: ' + error.message, 'error');
    }
}

// Delete modal
function openBackupDeleteModal(filename) {
    backupDeleteName = filename;
    backupDeleteNameEl.textContent = filename;
    backupDeleteModal.classList.remove('hidden');
}

function closeBackupDeleteModal() {
    backupDeleteName = null;
    backupDeleteModal.classList.add('hidden');
    confirmBackupDeleteBtn.disabled = false;
    confirmBackupDeleteBtn.textContent = 'Удалить';
}

async function confirmBackupDelete() {
    if (backupDeleteName === null) return;
    const filename = backupDeleteName;

    confirmBackupDeleteBtn.disabled = true;
    confirmBackupDeleteBtn.textContent = 'Удаление...';

    try {
        const url = `${BACKUPS_API}/${encodeURIComponent(filename)}`;
        const response = await authenticatedFetch(url, { method: 'DELETE' });
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'Ошибка удаления резервной копии');
        }
        showToast('Резервная копия удалена', 'success');
        closeBackupDeleteModal();
        await loadBackups();
    } catch (error) {
        showToast('Ошибка: ' + error.message, 'error');
        closeBackupDeleteModal();
    } finally {
        confirmBackupDeleteBtn.disabled = false;
        confirmBackupDeleteBtn.textContent = 'Удалить';
    }
}

