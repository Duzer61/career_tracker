// Filter and search logic

function isValidDateString(str) {
    if (!str || typeof str !== 'string') return false;
    // ISO 8601 date: YYYY-MM-DD
    if (/^\d{4}-\d{2}-\d{2}$/.test(str)) {
        const d = new Date(str + 'T00:00:00Z');
        return !isNaN(d.getTime());
    }
    return false;
}

function buildFilterQuery() {
    let query = `reverse=${sortAscending}`;

    if (filterPeriod) {
        query += `&period=${filterPeriod}`;
    } else if (customDateFrom || customDateTo) {
        if (customDateFrom) query += `&date_from=${customDateFrom}`;
        if (customDateTo) query += `&date_to=${customDateTo}`;
    }

    return query;
}

function matchesSearch(app) {
    if (!searchQuery) return true;

    const query = searchQuery.toLowerCase();
    return (
        (app.company_name && app.company_name.toLowerCase().includes(query)) ||
        (app.vacancy_name && app.vacancy_name.toLowerCase().includes(query)) ||
        (app.contacts && app.contacts.toLowerCase().includes(query)) ||
        (app.comments && app.comments.toLowerCase().includes(query))
    );
}

function setFilterPeriod(period) {
    filterPeriod = period;
    customDateFrom = '';
    customDateTo = '';

    // Update active button
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.period === period);
    });

    // Clear custom date inputs
    document.getElementById('date-from').value = '';
    document.getElementById('date-to').value = '';

    loadApplications();
}

function applyCustomRange() {
    const fromInput = document.getElementById('date-from');
    const toInput = document.getElementById('date-to');
    customDateFrom = fromInput.value;
    customDateTo = toInput.value;

    // Deactivate period buttons
    filterPeriod = '';
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));

    loadApplications();
}

function toggleSort() {
    sortAscending = !sortAscending;
    sessionStorage.setItem('sortAscending', sortAscending);
    updateSortButton();
    loadApplications();
}