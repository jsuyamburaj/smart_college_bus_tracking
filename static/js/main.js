// Main JavaScript file for Smart College Bus Tracking System

// Global variables
let currentUser = {};
let notifications = [];
let unreadCount = 0;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    initializeApplication();
    setupEventListeners();
    loadInitialData();
});

function checkNotificationPermission() {
    if (!("Notification" in window)) {
        console.log("This browser does not support notifications.");
        return;
    }

    if (Notification.permission === "default") {
        Notification.requestPermission().then(permission => {
            console.log("Notification permission:", permission);
        });
    } else {
        console.log("Notification permission already:", Notification.permission);
    }
}

// Application initialization
function initializeApplication() {
    // Load logged-in user data (if available)
    const userElement = document.getElementById('userData');
    if (userElement) {
        try {
            currentUser = JSON.parse(userElement.dataset.user);
        } catch (e) {
            currentUser = {};
        }
    }

    initializeTooltips();
    initializeModals();
    setupAutoLogout();
    checkNotificationPermission();
}

// ---------------------- EVENT LISTENERS ----------------------

function setupEventListeners() {
    // Confirmation dialogs
    document.addEventListener('click', function (e) {
        if (e.target.matches('[data-confirm]')) {
            e.preventDefault();
            if (confirm(e.target.dataset.confirm || 'Are you sure?')) {
                e.target.href ? window.location.href = e.target.href : e.target.form.submit();
            }
        }
    });

    // Form validation
    document.addEventListener('submit', function (e) {
        if (!e.target.matches('form[novalidate]') && !validateForm(e.target)) {
            e.preventDefault();
        }
    });

    // Online / Offline detection
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
}

// ---------------------- INITIAL DATA ----------------------

function loadInitialData() {
    if (currentUser?.id) {
        safeApiCall(loadUserNotifications);
        safeApiCall(loadUserPreferences);
        safeApiCall(updateLastActive);

        setInterval(() => safeApiCall(loadUserNotifications), 60000);
        setInterval(() => safeApiCall(updateLastActive), 300000);
    }

    safeApiCall(loadSystemStats);
}

// ---------------------- UI HELPERS ----------------------

function initializeTooltips() {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
    });
}

function initializeModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('shown.bs.modal', () => {
            modal.querySelector('input, textarea, select')?.focus();
        });
    });
}

// ---------------------- FORM VALIDATION ----------------------

function validateForm(form) {
    let valid = true;
    form.querySelectorAll('[required]').forEach(field => {
        if (!field.value.trim()) {
            markInvalid(field, 'This field is required');
            valid = false;
        } else {
            markValid(field);
        }
    });
    return valid;
}

function markInvalid(field, msg) {
    field.classList.add('is-invalid');
    let feedback = field.nextElementSibling;
    if (!feedback || !feedback.classList.contains('invalid-feedback')) {
        feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        field.after(feedback);
    }
    feedback.textContent = msg;
}

function markValid(field) {
    field.classList.remove('is-invalid');
    field.classList.add('is-valid');
}

// ---------------------- API SAFE WRAPPER ----------------------

function safeApiCall(fn) {
    try {
        fn();
    } catch (e) {
        console.warn('API skipped:', e.message);
    }
}

// ---------------------- API CALLS ----------------------

function loadUserNotifications() {
    fetch('/api/notifications/')
        .then(r => r.ok ? r.json() : null)
        .then(data => {
            if (!data) return;
            notifications = data.notifications || [];
            unreadCount = data.unread_count || 0;
            updateNotificationBadge();
        })
        .catch(() => {});
}

function updateNotificationBadge() {
    const badge = document.querySelector('.notification-badge');
    if (badge) {
        badge.textContent = unreadCount > 99 ? '99+' : unreadCount;
        badge.style.display = unreadCount ? 'flex' : 'none';
    }
}

function loadUserPreferences() {
    fetch('/api/preferences/')
        .then(r => r.ok ? r.json() : null)
        .then(data => {
            if (!data) return;
            if (data.theme === 'dark') document.body.classList.add('dark-mode');
        })
        .catch(() => {});
}

function updateLastActive() {
    fetch('/api/user/last-active/', {
        method: 'POST',
        headers: { 'X-CSRFToken': getCSRFToken() }
    }).catch(() => {});
}

function loadSystemStats() {
    fetch('/api/public/stats/')
        .then(r => r.ok ? r.json() : null)
        .then(data => data && updatePublicStats(data))
        .catch(() => {});
}

// ---------------------- STATS UI ----------------------

function updatePublicStats(stats) {
    setValue('activeBuses', stats.active_buses);
    setValue('totalStudents', stats.total_students);
    setValue('totalRoutes', stats.total_routes);
    setValue('onTimeRate', stats.on_time_rate + '%');
}

function setValue(id, value) {
    const el = document.getElementById(id);
    if (el && value !== undefined) el.textContent = value;
}

// ---------------------- AUTO LOGOUT ----------------------

function setupAutoLogout() {
    if (!currentUser?.id) return;
    let timer;
    const warningTime = 5 * 60 * 1000;

    function resetTimer() {
        clearTimeout(timer);
        timer = setTimeout(() => showToast('Session expiring soon', 'warning'), warningTime);
    }

    ['click', 'mousemove', 'keypress'].forEach(evt =>
        document.addEventListener(evt, resetTimer)
    );

    resetTimer();
}

// ---------------------- TOAST ----------------------

function showToast(msg, type = 'info') {
    alert(msg); // simple + safe (replace with Bootstrap later)
}

// ---------------------- ONLINE / OFFLINE ----------------------

function updateOnlineStatus() {
    showToast(navigator.onLine ? 'Online' : 'Offline', navigator.onLine ? 'success' : 'warning');
}

// ---------------------- CSRF ----------------------

function getCSRFToken() {
    return document.cookie.split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
}

// ---------------------- EXPORT ----------------------

window.BusTracking = {
    showToast,
    validateForm
};
