// Statistics page — load data, render counters, charts, time table

let funnelChartInstance = null;
let timeChartInstance = null;

// Default date range: last 6 months
function getDefaultDateRange() {
    const now = new Date();
    const sixMonthsAgo = new Date(now);
    sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
    return {
        from: formatDateInput(sixMonthsAgo),
        to: formatDateInput(now),
    };
}

function formatDateInput(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
}

// DOM references
let dateFromInput, dateToInput, applyBtn, resetBtn;
let statLoading, statError, statEmpty, statContent;
let totalEl, activeEl, rejectedEl, ignoredEl, offerEl;

function initStatDomRefs() {
    dateFromInput = document.getElementById('date-from');
    dateToInput = document.getElementById('date-to');
    applyBtn = document.getElementById('apply-date-btn');
    resetBtn = document.getElementById('reset-date-btn');
    statLoading = document.getElementById('stat-loading');
    statError = document.getElementById('stat-error');
    statEmpty = document.getElementById('stat-empty');
    statContent = document.getElementById('stat-content');
    totalEl = document.getElementById('stat-total');
    activeEl = document.getElementById('stat-active');
    rejectedEl = document.getElementById('stat-rejected');
    ignoredEl = document.getElementById('stat-ignored');
    offerEl = document.getElementById('stat-offer');
}

function showLoading() {
    if (statLoading) statLoading.classList.remove('hidden');
    if (statError) statError.classList.add('hidden');
    if (statEmpty) statEmpty.classList.add('hidden');
    if (statContent) statContent.classList.add('hidden');
}

function showError(msg) {
    if (statLoading) statLoading.classList.add('hidden');
    if (statError) {
        statError.classList.remove('hidden');
        statError.textContent = msg;
    }
    if (statEmpty) statEmpty.classList.add('hidden');
    if (statContent) statContent.classList.add('hidden');
}

function showEmpty() {
    if (statLoading) statLoading.classList.add('hidden');
    if (statError) statError.classList.add('hidden');
    if (statEmpty) statEmpty.classList.remove('hidden');
    if (statContent) statContent.classList.add('hidden');
}

function showContent() {
    if (statLoading) statLoading.classList.add('hidden');
    if (statError) statError.classList.add('hidden');
    if (statEmpty) statEmpty.classList.add('hidden');
    if (statContent) statContent.classList.remove('hidden');
}

function renderCounters(data) {
    if (totalEl) totalEl.textContent = data.total_applications;
    if (activeEl) activeEl.textContent = data.active_applications;
    if (rejectedEl) rejectedEl.textContent = data.rejected_applications;
    if (ignoredEl) ignoredEl.textContent = data.ignored_applications;
    if (offerEl) offerEl.textContent = data.offer_applications;
}

function renderFunnelChart(funnelData) {
    if (!funnelData || funnelData.length === 0) return;

    const ctx = document.getElementById('funnelChart');
    if (!ctx) return;

    if (funnelChartInstance) {
        funnelChartInstance.destroy();
        funnelChartInstance = null;
    }

    const labels = funnelData.map(d => d.status_label);
    const counts = funnelData.map(d => d.count);
    const pcts = funnelData.map(d => d.pct_of_previous);

    // Color gradient from light to dark purple
    const baseColor = '#667eea';
    const colors = funnelData.map((_, i) => {
        const alpha = 0.3 + (i / Math.max(funnelData.length - 1, 1)) * 0.5;
        return `rgba(102, 126, 234, ${alpha})`;
    });
    const borderColors = funnelData.map((_, i) => {
        const alpha = 0.6 + (i / Math.max(funnelData.length - 1, 1)) * 0.4;
        return `rgba(102, 126, 234, ${alpha})`;
    });

    funnelChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Количество',
                data: counts,
                backgroundColor: colors,
                borderColor: borderColors,
                borderWidth: 1,
                borderRadius: 4,
            }],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: true,
            layout: {
                padding: {
                    right: 80,
                },
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        afterLabel: function(context) {
                            const idx = context.dataIndex;
                            const pctTotal = funnelData[idx].pct_of_total;
                            const pctPrev = funnelData[idx].pct_of_previous;
                            const lines = [];
                            if (pctTotal !== null) lines.push(`% от общего: ${pctTotal}%`);
                            if (pctPrev !== null) lines.push(`% от предыдущего: ${pctPrev}%`);
                            return lines;
                        },
                        label: function(context) {
                            return ` ${context.parsed.x}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Количество откликов',
                        color: '#555',
                    },
                    grid: {
                        color: 'rgba(0,0,0,0.06)',
                    }
                },
                y: {
                    grid: { display: false },
                }
            },
        },
        plugins: [{
            id: 'funnelLabels',
            afterDatasetsDraw(chart) {
                const { ctx, data, chartArea: { top, bottom, left, right } } = chart;
                const meta = chart.getDatasetMeta(0);
                ctx.save();
                ctx.font = '12px -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif';
                ctx.fillStyle = '#555';
                ctx.textAlign = 'left';
                ctx.textBaseline = 'middle';

                meta.data.forEach((bar, i) => {
                    const value = data.datasets[0].data[i];
                    const pctTotal = funnelData[i].pct_of_total;
                    const pctPrev = funnelData[i].pct_of_previous;
                    let label = `${value}`;
                    if (pctTotal !== null) label += ` (${pctTotal}%)`;
                    const x = bar.x + 6;
                    const y = bar.y;
                    ctx.fillText(label, x, y);
                });
                ctx.restore();
            }
        }],
    });
}

function renderTimeChart(timeData) {
    if (!timeData || timeData.length === 0) return;

    const ctx = document.getElementById('timeChart');
    if (!ctx) return;

    if (timeChartInstance) {
        timeChartInstance.destroy();
        timeChartInstance = null;
    }

    const labels = timeData.map(d => `${d.from_label} → ${d.to_label}`);
    const avg = timeData.map(d => Math.round((d.avg_hours / 24) * 10) / 10);
    const median = timeData.map(d => Math.round((d.median_hours / 24) * 10) / 10);
    const min = timeData.map(d => Math.round((d.min_hours / 24) * 10) / 10);
    const max = timeData.map(d => Math.round((d.max_hours / 24) * 10) / 10);

    timeChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Мин.',
                    data: min,
                    backgroundColor: 'rgba(153, 153, 153, 0.6)',
                    borderColor: 'rgba(153, 153, 153, 0.8)',
                    borderWidth: 1,
                    borderRadius: 2,
                },
                {
                    label: 'Медиана',
                    data: median,
                    backgroundColor: 'rgba(102, 126, 234, 0.6)',
                    borderColor: 'rgba(102, 126, 234, 0.8)',
                    borderWidth: 1,
                    borderRadius: 2,
                },
                {
                    label: 'Среднее',
                    data: avg,
                    backgroundColor: 'rgba(102, 126, 234, 0.85)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 1,
                    borderRadius: 2,
                },
                {
                    label: 'Макс.',
                    data: max,
                    backgroundColor: 'rgba(231, 76, 60, 0.6)',
                    borderColor: 'rgba(231, 76, 60, 0.8)',
                    borderWidth: 1,
                    borderRadius: 2,
                },
            ],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        boxWidth: 12,
                        padding: 16,
                        font: { size: 12 },
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return ` ${context.dataset.label}: ${context.parsed.x} д`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Дни',
                        color: '#555',
                    },
                    grid: {
                        color: 'rgba(0,0,0,0.06)',
                    }
                },
                y: {
                    grid: { display: false },
                }
            },
        },
    });
}

function renderTimeTable(timeData) {
    const tbody = document.getElementById('time-table-body');
    if (!tbody) return;

    if (!timeData || timeData.length === 0) {
        document.getElementById('time-table-card').classList.add('hidden');
        return;
    }

    document.getElementById('time-table-card').classList.remove('hidden');
    tbody.innerHTML = '';

    timeData.forEach(d => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${escapeHtml(d.from_label)}</td>
            <td>${escapeHtml(d.to_label)}</td>
            <td>${formatDays(d.avg_hours)}</td>
            <td>${formatDays(d.median_hours)}</td>
            <td>${formatDays(d.min_hours)}</td>
            <td>${formatDays(d.max_hours)}</td>
        `;
        tbody.appendChild(tr);
    });
}

function formatDays(hours) {
    if (hours === null || hours === undefined) return '—';
    const days = Math.round((hours / 24) * 10) / 10;
    return `${days} <span class="hours-unit">д</span>`;
}

async function loadStatistics(dateFrom, dateTo) {
    showLoading();

    try {
        const params = new URLSearchParams();
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);

        const query = params.toString();
        const url = `/api/statistics${query ? '?' + query : ''}`;

        const response = await authenticatedFetch(url, { method: 'GET' });

        if (!response.ok) {
            let errMsg = 'Ошибка загрузки статистики';
            try {
                const errData = await response.json();
                errMsg = errData.detail || errMsg;
            } catch (_) {}
            showError(errMsg);
            return;
        }

        const data = await response.json();

        // Check if there's any data
        if (!data.total_applications && (!data.funnel || data.funnel.length === 0)) {
            showEmpty();
            return;
        }

        // Render everything
        renderCounters(data);
        renderFunnelChart(data.funnel || []);
        renderTimeChart(data.time_to_stage || []);
        renderTimeTable(data.time_to_stage || []);

        showContent();
    } catch (err) {
        console.error('Statistics load error:', err);
        showError('Ошибка подключения к серверу');
    }
}

function setDefaultDates() {
    const range = getDefaultDateRange();
    if (dateFromInput) dateFromInput.value = range.from;
    if (dateToInput) dateToInput.value = range.to;
}

function handleApplyFilter() {
    const dateFrom = dateFromInput ? dateFromInput.value : '';
    const dateTo = dateToInput ? dateToInput.value : '';
    loadStatistics(dateFrom || undefined, dateTo || undefined);
}

function handleResetFilter() {
    setDefaultDates();
    handleApplyFilter();
}

function initStatistics() {
    initStatDomRefs();
    setDefaultDates();

    // Set username in header
    const usernameDisplay = document.getElementById('username-display');
    const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
    if (token && usernameDisplay) {
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            if (payload.sub) {
                usernameDisplay.textContent = payload.sub;
            }
        } catch (_) {}
    }

    // Event listeners
    if (applyBtn) applyBtn.addEventListener('click', handleApplyFilter);
    if (resetBtn) resetBtn.addEventListener('click', handleResetFilter);

    // Enter key in date inputs
    [dateFromInput, dateToInput].forEach(input => {
        if (input) {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') handleApplyFilter();
            });
        }
    });

    // Logout
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) logoutBtn.addEventListener('click', () => {
        sessionStorage.removeItem('access_token');
        localStorage.removeItem('access_token');
        window.location.href = '/';
    });

    // Load initial data
    handleApplyFilter();
}

document.addEventListener('DOMContentLoaded', initStatistics);