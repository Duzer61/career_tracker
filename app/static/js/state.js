// Global state
let currentUser = null;
let applications = [];
let editingApplicationId = null;
const savedSort = sessionStorage.getItem('sortAscending');
let sortAscending = savedSort !== null ? savedSort === 'true' : false;
let searchQuery = '';
let filterPeriod = '';
let customDateFrom = '';
let customDateTo = '';
let refreshInProgress = false;
let currentDeleteApplicationId = null;