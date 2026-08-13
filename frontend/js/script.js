(function () {

  const API_BASE = "http://zainab:8000";

  // Safe HTML escape — prevents XSS when inserting API data into innerHTML
  function esc(s) {
    const d = document.createElement('div');
    d.textContent = (s === null || s === undefined) ? '' : String(s);
    return d.innerHTML;
  }

  // =========================
  // ROUTE PROTECTION GUARD
  // runs synchronously before any API call or function
  // =========================
  const _path = window.location.pathname;
  if (_path.includes('/authorized/') || _path.includes('/unauthorized/')) {
    const _token = localStorage.getItem('token');
    const _role  = localStorage.getItem('userRole');

    if (!_token || !_role) {
      window.location.href = '../index.html';
      return;
    }
    if (_path.includes('/authorized/') && _role === 'citizen') {
      window.location.href = '../unauthorized/dashboard.html';
      return;
    }
    if (_path.includes('/unauthorized/') && (_role === 'admin' || _role === 'officer')) {
      window.location.href = '../authorized/dashboard.html';
      return;
    }
  }

  const $ = (s, ctx = document) => ctx.querySelector(s);
  const $$ = (s, ctx = document) =>
    Array.from(ctx.querySelectorAll(s));

  // =========================
  // LOGIN FUNCTION
  // =========================
async function officerLogin(event) {

  event.preventDefault();

  const username =
    document.getElementById("officerUsername").value.trim();

  const password =
    document.getElementById("officerPassword").value.trim();

  const officerCode =
    document.getElementById("officerCode").value.trim();

  const role =
    document.getElementById("loginRole").value;

  const error =
    document.getElementById("officerError");

  error.innerHTML = "";

  try {

    const response = await fetch(
      API_BASE + "/api/auth/login",
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json"
        },

        body: JSON.stringify({

          username: username,
          password: password,
          role: role,
          officer_code: officerCode

        })
      }
    );

    const data = await response.json();

    if (!response.ok) {

      error.innerHTML =
        data.detail || "Invalid credentials.";

      return;
    }

    localStorage.setItem(
      "token",
      data.access_token
    );

    localStorage.setItem(
      "userRole",
      data.user.role
    );

    localStorage.setItem("userName", data.user.full_name);
    localStorage.setItem("userId", data.user.id);

    window.location.href =
      "authorized/dashboard.html";

  }

  catch (err) {

    error.innerHTML =
      "Backend connection failed.";
  }

}

  // =========================
  // DOM LOADED
  // =========================

  document.addEventListener('DOMContentLoaded', () => {

    // Active Sidebar Link
    const path =
      location.pathname.split('/').pop() || 'index.html';

    $$('.nav-link').forEach(a => {

      if (a.getAttribute('href') === path) {
        a.classList.add('active');
      }

    });

    // Mobile Menu
    const menu = $('.mobile-menu');
    const side = $('.sidebar');

    if (menu && side) {

      menu.addEventListener('click', () => {
        side.classList.toggle('open');
      });

    }

    // Logout: clear session before redirect
    const logoutLink = $$('.nav-link').find(a => (a.getAttribute('href') || '').includes('index.html'));
    if (logoutLink) {
      logoutLink.addEventListener('click', e => {
        e.preventDefault();
        localStorage.removeItem('token');
        localStorage.removeItem('userRole');
        localStorage.removeItem('userName');
        localStorage.removeItem('userId');
        window.location.href = logoutLink.getAttribute('href');
      });
    }

    // Avatar initials
    const userName = localStorage.getItem("userName");
    if (userName) {
      const parts = userName.trim().split(/\s+/);
      const initials = parts.length >= 2
        ? parts[0][0] + parts[parts.length - 1][0]
        : parts[0].slice(0, 2);
      $$('.avatar').forEach(el => { el.textContent = initials.toUpperCase(); });
    }

    // Topbar buttons — global wiring for all pages
    const isAuth = window.location.pathname.includes('/authorized/');
    const topActions = document.querySelector('.top-actions');
    if (topActions) {
      const softBtns = Array.from(topActions.querySelectorAll('button.btn-soft'));
      if (softBtns[0]) {
        softBtns[0].style.cursor = 'pointer';
        softBtns[0].addEventListener('click', () => {
          window.location.href = isAuth ? 'reports.html' : 'alerts.html';
        });
      }
      if (softBtns[1]) {
        softBtns[1].style.cursor = 'pointer';
        softBtns[1].addEventListener('click', () => {
          window.location.href = isAuth ? 'notifications.html' : 'alerts.html';
        });
      }
      const avatarEl = topActions.querySelector('.avatar');
      if (avatarEl) {
        avatarEl.style.cursor = 'pointer';
        avatarEl.addEventListener('click', () => {
          window.location.href = 'profile.html';
        });
      }
    }

    // Table Search Filter
    $$('[data-filter-table]').forEach(input => {

      input.addEventListener('input', () => {

        const q = input.value.toLowerCase();

        const table = $(input.dataset.filterTable);

        if (!table) return;

        $$('tbody tr', table).forEach(r => {

          r.style.display =
            r.innerText.toLowerCase().includes(q)
              ? ''
              : 'none';

        });

      });

    });

    // Status Filter Select
    $$('.filter-select').forEach(select => {
      select.addEventListener('change', () => {
        const val = select.value.toLowerCase();
        const section = select.closest('section');
        if (!section) return;
        const tbody = section.querySelector('tbody');
        if (!tbody) return;
        $$('tr', tbody).forEach(row => {
          if (!val || val.startsWith('all')) {
            row.style.display = '';
          } else {
            row.style.display = row.innerText.toLowerCase().includes(val) ? '' : 'none';
          }
        });
      });
    });

    // Column Sort
    $$('table thead th').forEach((th, idx) => {
      th.style.cursor = 'pointer';
      let asc = true;
      th.addEventListener('click', () => {
        const table = th.closest('table');
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        rows.sort((a, b) => {
          const aText = (a.cells[idx] ? a.cells[idx].innerText : '').toLowerCase();
          const bText = (b.cells[idx] ? b.cells[idx].innerText : '').toLowerCase();
          return asc ? aText.localeCompare(bText) : bText.localeCompare(aText);
        });
        asc = !asc;
        rows.forEach(r => tbody.appendChild(r));
      });
    });

    // Status Badges
    $$('[data-status]').forEach(el => {

      const s = el.dataset.status.toLowerCase();

      el.className =
        'badge ' +

        (
          s.includes('high') ||
          s.includes('urgent') ||
          s.includes('open')

            ? 'high'

            : s.includes('progress') ||
              s.includes('pending')

            ? 'progress'

            : s.includes('closed') ||
              s.includes('safe') ||
              s.includes('approved')

            ? 'closed'

            : 'info'
        );

    });

    // Demo Forms
    $$('form[data-demo-form]').forEach(f => {

      f.addEventListener('submit', ev => {

        ev.preventDefault();

        toast(
          'Saved successfully. Demo frontend updated.'
        );

        f.reset();

      });

    });

    // Charts
    if (typeof Chart !== 'undefined') {
      initCharts();
    }

  });

  // =========================
  // TOAST MESSAGE
  // =========================

  window.toast = function (msg) {

    let t = document.createElement('div');

    t.textContent = msg;

    t.style.cssText = `
      position: fixed;
      right: 22px;
      bottom: 22px;
      background: #111827;
      color: white;
      padding: 14px 18px;
      border-radius: 14px;
      box-shadow: 0 20px 45px rgba(0,0,0,.25);
      z-index: 9999;
      font-weight: 800;
    `;

    document.body.appendChild(t);

    setTimeout(() => t.remove(), 2800);

  };

  // =========================
  // API HELPERS
  // =========================

  function statusBadge(status) {
    const s = (status || '').toLowerCase();
    if (s === 'open' || s === 'high' || s === 'urgent' || s === 'rejected') return 'high';
    if (s === 'in_progress' || s === 'in progress' || s === 'pending' || s === 'under review') return 'progress';
    if (s === 'closed' || s === 'resolved' || s === 'verified' || s === 'approved' || s === 'stored') return 'closed';
    return 'info';
  }

  function checkAuth(response) {
    if (response.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('userRole');
      const base = (window.location.pathname.includes('/authorized/') || window.location.pathname.includes('/unauthorized/')) ? '../' : './';
      window.location.href = base + 'index.html';
      return false;
    }
    return true;
  }

  // =========================
  // DATE FORMATTER (PKT / UTC+5)
  // =========================

  function formatPKT(dateStr) {
    if (!dateStr) return '—';
    // Append Z so JavaScript treats the naive UTC string as UTC, not local
    const utcStr = dateStr.endsWith('Z') ? dateStr : dateStr + 'Z';
    const d = new Date(utcStr);
    if (isNaN(d)) return dateStr;

    const todayUTC = new Date(new Date().toLocaleDateString('en-US', { timeZone: 'Asia/Karachi' }));
    const logUTC  = new Date(d.toLocaleDateString('en-US', { timeZone: 'Asia/Karachi' }));
    const isToday = todayUTC.getTime() === logUTC.getTime();

    const timeStr = d.toLocaleTimeString('en-PK', {
      timeZone: 'Asia/Karachi',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });

    if (isToday) return 'Today, ' + timeStr;

    const dateLabel = d.toLocaleDateString('en-PK', {
      timeZone: 'Asia/Karachi',
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
    return dateLabel + ', ' + timeStr;
  }

  // =========================
  // CHART FUNCTION
  // =========================

  function chart(id, type, labels, data) {

    const c = document.getElementById(id);

    if (!c) return;

    new Chart(c, {

      type,

      data: {

        labels,

        datasets: [
          {
            label: 'Records',
            data,
            borderWidth: 2,
            tension: 0.35,
            fill: type === 'line'
          }
        ]

      },

      options: {

        responsive: true,
        maintainAspectRatio: false,

        plugins: {
          legend: {
            display: false
          }
        },

        scales: {
          y: {
            beginAtZero: true
          }
        }

      }

    });

  }

  // =========================
  // INIT CHARTS
  // =========================

  function initCharts() {
    const onDashboard = window.location.pathname.includes('dashboard.html');
    const onAnalytics = window.location.pathname.includes('analytics.html');

    // Crime trend chart — load real 7-day data if token available
    const _tToken = localStorage.getItem('token');
    if (_tToken && document.getElementById('crimeTrendChart')) {
      fetch(API_BASE + '/api/dashboard/trends', {
        headers: { 'Authorization': 'Bearer ' + _tToken }
      }).then(r => r.ok ? r.json() : null).then(trends => {
        if (trends && trends.length) {
          chart('crimeTrendChart', 'line', trends.map(t => t.day), trends.map(t => t.count));
        } else {
          chart('crimeTrendChart', 'line', ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'], [0,0,0,0,0,0,0]);
        }
      }).catch(() => {
        chart('crimeTrendChart', 'line', ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'], [0,0,0,0,0,0,0]);
      });
    }

    // skipped on dashboard — loadCategoryChart() uses real data instead
    if (!onDashboard) {
      chart(
        'categoryChart',
        'doughnut',
        ['Theft', 'Fraud', 'Assault', 'Cyber', 'Other'],
        [32, 18, 14, 20, 16]
      );
    }

    // skipped on analytics — loadAnalyticsCharts() uses real data instead
    if (!onAnalytics) {
      chart(
        'monthlyChart',
        'bar',
        ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        [88, 74, 91, 105, 96, 112]
      );

      chart(
        'riskChart',
        'line',
        ['Zone A', 'Zone B', 'Zone C', 'Zone D'],
        [76, 48, 61, 35]
      );
    }
  }
   function selectRole(role, event) {

  const username =
    document.getElementById("username");

  const password =
    document.getElementById("password");

  document
    .querySelectorAll(".role-btn")
    .forEach(btn => btn.classList.remove("active"));

  event.target.classList.add("active");

  if (role === "admin") {

    username.value = "admin";
    password.value = "admin123";

  } else {

    username.value = "public";
    password.value = "user123";

  }

}

function switchTab(type){

  const citizenForm = document.getElementById("citizenForm");
  const officerForm = document.getElementById("officerForm");
  const citizenTab = document.getElementById("citizenTab");
  const officerTab = document.getElementById("officerTab");

  if(type === "citizen"){
    citizenForm.classList.remove("hidden");
    officerForm.classList.add("hidden");

    citizenTab.classList.add("active");
    officerTab.classList.remove("active");
  } 
  else {
    officerForm.classList.remove("hidden");
    citizenForm.classList.add("hidden");

    officerTab.classList.add("active");
    citizenTab.classList.remove("active");
  }
};

async function citizenLogin(event) {

  event.preventDefault();

  const username = document.getElementById("citizenUsername").value.trim();
  const password = document.getElementById("citizenPassword").value.trim();
  const error = document.getElementById("citizenError");

  error.textContent = "";

  try {

    const response = await fetch(API_BASE + "/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: username,
        password: password,
        role: "citizen"
      })
    });

    const data = await response.json();

    if (!response.ok) {
      error.textContent = data.detail || "Invalid username or password.";
      return;
    }

    localStorage.setItem("token", data.access_token);
    localStorage.setItem("userRole", data.user.role);
    localStorage.setItem("userName", data.user.full_name);
    localStorage.setItem("userId", data.user.id);

    window.location.href = "unauthorized/dashboard.html";

  } catch (err) {

    error.textContent = "Backend connection failed.";

  }

}

window.switchTab = switchTab;
window.citizenLogin = citizenLogin;
window.officerLogin = officerLogin; 
async function loadDashboardData() {

try {

  const token =
    localStorage.getItem("token");

  const response = await fetch(
    API_BASE + "/api/dashboard/stats",
    {
      headers: {
        "Authorization":
          "Bearer " + token
      }
    }
  );

  if (!checkAuth(response) || !response.ok) return;

  const data = await response.json();
    document.getElementById("totalCases").innerText =
      data.open_cases || data.cases || 0;

    document.getElementById("totalReports").innerText =
      data.reports || 0;

    document.getElementById("totalEvidence").innerText =
      data.evidence || 0;

    document.getElementById("totalUsers").innerText =
      data.users || 0;

    const casesNote = document.getElementById("casesNote");
    if (casesNote) casesNote.innerText = (data.pending_reports || 0) + " pending reports";

  }

  catch(error){

    console.error('Dashboard load failed:', error);
  }

}

if(
  window.location.pathname.includes("/authorized/") &&
  window.location.pathname.includes("dashboard.html") &&
  localStorage.getItem('userRole') !== 'citizen'
){

  loadDashboardData();

}

async function loadReports() {
  const tableBody = document.getElementById("reportsTableBody");
  if (!tableBody) return;

  const token = localStorage.getItem("token");

  try {
    const response = await fetch(API_BASE + "/api/reports/", {
      headers: { "Authorization": "Bearer " + token }
    });

    if (!checkAuth(response)) return;
    if (!response.ok) {
      tableBody.innerHTML = '<tr><td colspan="7">Failed to load reports.</td></tr>';
      return;
    }

    const reports = await response.json();

    // Stat counts
    const counts = { pending: 0, verified: 0, resolved: 0, converted: 0 };
    reports.forEach(r => {
      const s = (r.status || '').toLowerCase();
      if      (s === 'pending')   counts.pending++;
      else if (s === 'verified')  counts.verified++;
      else if (s === 'resolved')  counts.resolved++;
      else if (s === 'converted') counts.converted++;
    });
    const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
    setEl('rptStatPending',   counts.pending);
    setEl('rptStatVerified',  counts.verified);
    setEl('rptStatResolved',  counts.resolved);
    setEl('rptStatConverted', counts.converted);

    tableBody.innerHTML = "";

    if (!reports.length) {
      tableBody.innerHTML = '<tr><td colspan="7">No reports found.</td></tr>';
      return;
    }

    const statusLabel   = { pending: 'Pending', verified: 'Verified', resolved: 'Resolved', rejected: 'Rejected', converted: 'Converted' };
    const priorityLabel = { normal: 'Normal', high: 'High', urgent: 'Urgent' };

    reports.forEach(report => {
      const s       = (report.status   || 'pending').toLowerCase();
      const p       = (report.priority || 'normal').toLowerCase();
      const sCls    = statusBadge(s);
      const sLabel  = statusLabel[s]   || report.status   || 'Pending';
      const pCls    = p === 'urgent' ? 'high' : p === 'high' ? 'progress' : 'info';
      const pLabel  = priorityLabel[p] || report.priority || 'Normal';
      const created = formatPKT(report.created_at);
      const desc     = (report.description || "").replace(/'/g, "\\'").replace(/\n/g, " ");
      const title    = (report.title    || "").replace(/'/g, "\\'");
      const category = (report.category || "General").replace(/'/g, "\\'");
      const location = (report.location || "—").replace(/'/g, "\\'");
      const createdAt = (report.created_at || "").replace(/'/g, "\\'");
      tableBody.innerHTML += `
        <tr>
          <td>#${report.id}</td>
          <td>${esc(report.title)}</td>
          <td>${esc(report.category || "General")}</td>
          <td><span class="badge ${pCls}">${pLabel}</span></td>
          <td><span class="badge ${sCls}">${sLabel}</span></td>
          <td>${created}</td>
          <td><button class="btn btn-sm btn-soft" onclick="openReport(${report.id},'${title}','${category}','${desc}','${location}','${s}','${p}','${createdAt}')">Open</button></td>
        </tr>
      `;
    });
  } catch (err) {
    tableBody.innerHTML = '<tr><td colspan="7">Connection error. Is the backend running?</td></tr>';
  }
}

async function createCase(event) {

  event.preventDefault();

  const token =
    localStorage.getItem("token");

  try {

    const response = await fetch(
      API_BASE + "/api/cases/",
      {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer " + token
        },

        body: JSON.stringify({
        
  case_no:
    "CASE-" + Date.now(),

  title:
    document.getElementById("caseTitle").value,

  crime_type:
    document.getElementById("crimeType").value,

  location:
    document.getElementById("caseLocation").value,

  description:
    document.getElementById("caseDescription").value,

  assigned_officer_id: parseInt(document.getElementById("caseOfficer").value) || null
        })
      }
    );

    const data = await response.json();

    if (!response.ok) {
      toast("Case creation failed: " + (data.detail || "Unknown error"));
      return;
    }

    toast("Case created: " + data.case_no);
    event.target.reset();

  }

  catch(error){

    toast("Case creation failed. Is the backend running?");
  }

}

window.createCase = createCase;

async function loadCases() {
  const tableBody = document.getElementById("casesTableBody");
  if (!tableBody) return;

  const token = localStorage.getItem("token");

  try {
    const [casesRes, officersRes] = await Promise.all([
      fetch(API_BASE + "/api/cases/",         { headers: { "Authorization": "Bearer " + token } }),
      fetch(API_BASE + "/api/users/officers",  { headers: { "Authorization": "Bearer " + token } })
    ]);

    if (!checkAuth(casesRes)) return;
    if (!casesRes.ok) {
      tableBody.innerHTML = '<tr><td colspan="7">Failed to load cases.</td></tr>';
      return;
    }

    const cases   = await casesRes.json();
    const officers = officersRes.ok ? await officersRes.json() : [];

    const officerMap = {};
    officers.forEach(o => {
      officerMap[o.id] = o.officer_code ? `${o.full_name} (${o.officer_code})` : o.full_name;
    });

    const counts = { open: 0, in_progress: 0, closed: 0 };
    cases.forEach(c => {
      const s = (c.status || '').toLowerCase();
      if (s === 'open')             counts.open++;
      else if (s === 'in_progress') counts.in_progress++;
      else if (s === 'closed')      counts.closed++;
    });

    const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
    setEl('caseStatOpen',     counts.open);
    setEl('caseStatProgress', counts.in_progress);
    setEl('caseStatClosed',   counts.closed);
    setEl('caseStatTotal',    cases.length);

    tableBody.innerHTML = "";
    if (!cases.length) {
      tableBody.innerHTML = '<tr><td colspan="7">No cases found.</td></tr>';
      return;
    }

    const statusLabel = { open: 'Open', in_progress: 'In Progress', closed: 'Closed' };

    cases.forEach(item => {
      const s       = (item.status || 'open').toLowerCase();
      const cls     = statusBadge(s);
      const label   = statusLabel[s] || item.status || 'Open';
      const officer = item.assigned_officer_id
        ? (officerMap[item.assigned_officer_id] || 'Officer #' + item.assigned_officer_id)
        : 'Unassigned';
      const created    = formatPKT(item.created_at);
      const safeCaseNo = String(item.case_no || '').replace(/'/g, "\\'");
      tableBody.innerHTML += `
        <tr>
          <td>${esc(item.case_no || '#' + item.id)}</td>
          <td>${esc(item.title)}</td>
          <td>${esc(item.crime_type || '—')}</td>
          <td><span class="badge ${cls}">${label}</span></td>
          <td>${esc(officer)}</td>
          <td>${created}</td>
          <td style="display:flex; gap:6px;">
            <button class="btn btn-sm btn-soft" onclick="window.location.href='case-details.html?id=${item.id}'">View</button>
            <button class="btn btn-sm btn-danger" onclick="openDeleteModal(${item.id},'${safeCaseNo}')">Delete</button>
          </td>
        </tr>
      `;
    });
  } catch (err) {
    tableBody.innerHTML = '<tr><td colspan="7">Connection error. Is the backend running?</td></tr>';
  }
}

if (window.location.pathname.includes("cases.html")) {
  loadCases();
}

let _deleteCaseId = null;
let _deleteCaseNo = null;

function openDeleteModal(id, caseNo) {
  _deleteCaseId = id;
  _deleteCaseNo = caseNo;
  const modal = document.getElementById("deleteCaseModal");
  if (!modal) return;
  document.getElementById("deleteCaseNoDisplay").value = caseNo;
  document.getElementById("deleteCaseNoConfirm").value = caseNo;
  document.getElementById("deleteCasePassword").value  = "";
  const errEl = document.getElementById("deleteModalError");
  if (errEl) { errEl.style.display = "none"; errEl.textContent = ""; }
  modal.style.display = "flex";
  setTimeout(() => {
    const pwField = document.getElementById("deleteCasePassword");
    if (pwField) pwField.focus();
  }, 100);
}

function closeDeleteModal() {
  const modal = document.getElementById("deleteCaseModal");
  if (modal) modal.style.display = "none";
  _deleteCaseId = null;
  _deleteCaseNo = null;
}

async function confirmDeleteCase() {
  const confirmInput = document.getElementById("deleteCaseNoConfirm").value.trim();
  const password     = document.getElementById("deleteCasePassword").value;
  const errEl        = document.getElementById("deleteModalError");

  const showErr = (msg) => {
    if (errEl) { errEl.textContent = msg; errEl.style.display = "block"; }
  };

  if (confirmInput !== _deleteCaseNo) {
    showErr("Case number does not match. Type exactly: " + _deleteCaseNo);
    return;
  }
  if (!password) {
    showErr("Password is required.");
    return;
  }

  const token = localStorage.getItem("token");
  try {
    const res  = await fetch(API_BASE + "/api/cases/" + _deleteCaseId + "/delete", {
      method:  "POST",
      headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token },
      body:    JSON.stringify({ password })
    });
    let data = {};
    try { data = await res.json(); } catch (e) {}
    if (res.status === 401) { showErr("Incorrect password. Try again."); return; }
    if (res.status === 403) { showErr("Permission denied. Only officers and admins can delete cases."); return; }
    if (res.status === 404) { showErr("Case not found."); return; }
    if (!res.ok)            { showErr(data.detail || "Delete failed (server error " + res.status + ")."); return; }
    closeDeleteModal();
    toast("Case " + (data.case_no || _deleteCaseNo) + " deleted.");
    loadCases();
  } catch (err) {
    showErr("Connection error. Is the backend running?");
  }
}

window.openDeleteModal   = openDeleteModal;
window.closeDeleteModal  = closeDeleteModal;
window.confirmDeleteCase = confirmDeleteCase;

async function loadCaseDetails() {
  const params  = new URLSearchParams(window.location.search);
  const caseId  = params.get('id');
  const infoList = document.getElementById('cdInfoList');
  const evList   = document.getElementById('cdEvidenceList');

  if (!caseId) {
    if (infoList) infoList.innerHTML = '<div class="list-item"><div class="item-title">No case selected.</div><div class="item-meta"><a href="cases.html">← Back to Cases</a></div></div>';
    if (evList)   evList.innerHTML   = '<div class="list-item"><div class="item-title">—</div></div>';
    return;
  }

  const token = localStorage.getItem('token');

  try {
    const res = await fetch(API_BASE + `/api/cases/${caseId}`, {
      headers: { 'Authorization': 'Bearer ' + token }
    });

    if (!checkAuth(res)) return;

    if (res.status === 404) {
      if (infoList) infoList.innerHTML = '<div class="list-item"><div class="item-title">Case not found.</div><div class="item-meta"><a href="cases.html">← Back to Cases</a></div></div>';
      if (evList)   evList.innerHTML   = '<div class="list-item"><div class="item-title">—</div></div>';
      return;
    }

    if (!res.ok) {
      if (infoList) infoList.innerHTML = '<div class="list-item"><div class="item-title">Failed to load case.</div></div>';
      return;
    }

    const c = await res.json();

    // Update page title
    const titleEl = document.querySelector('.page-title');
    if (titleEl) titleEl.innerText = c.title || 'Case Details';

    // Stat cards
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
    set('cdCaseNo',      c.case_no || '#' + c.id);
    set('cdCaseNoNote',  c.title);
    set('cdStatus',      c.status  ? c.status.charAt(0).toUpperCase() + c.status.slice(1) : '—');
    set('cdStatusNote',  c.crime_type || '—');
    set('cdCreated',     c.created_at ? formatPKT(c.created_at) : '—');
    set('cdCreatedNote', 'Case opened');

    // Case info list
    if (infoList) {
      infoList.innerHTML = `
        <div class="list-item">
          <div><div class="item-title">Crime Type</div><div class="item-meta">${esc(c.crime_type || '—')}</div></div>
        </div>
        <div class="list-item">
          <div><div class="item-title">Location</div><div class="item-meta">${esc(c.location || '—')}</div></div>
        </div>
        <div class="list-item">
          <div><div class="item-title">Assigned Officer</div><div class="item-meta">${c.assigned_officer_id ? 'Officer #' + c.assigned_officer_id : 'Unassigned'}</div></div>
        </div>
        ${c.description ? `<div class="list-item"><div><div class="item-title">Description</div><div class="item-meta">${esc(c.description)}</div></div></div>` : ''}
      `;
    }

    // Fetch evidence linked to this case
    const evRes = await fetch(API_BASE + `/api/evidence/case/${caseId}`, {
      headers: { 'Authorization': 'Bearer ' + token }
    });

    if (evRes.ok) {
      const evidence = await evRes.json();
      set('cdEvidenceCount', evidence.length);

      if (evList) {
        if (!evidence.length) {
          evList.innerHTML = '<div class="list-item"><div class="item-title">No evidence attached yet.</div></div>';
        } else {
          evList.innerHTML = '';
          evidence.forEach(ev => {
            const safePath = esc(ev.file_path || '');
            const btn = ev.file_path
              ? `<button class="btn btn-sm btn-soft" onclick="window.open(API_BASE+'/${safePath}','_blank')">Open</button>`
              : `<span class="badge info">No File</span>`;
            evList.innerHTML += `
              <div class="list-item">
                <div>
                  <div class="item-title">${esc(ev.title)}</div>
                  <div class="item-meta">${esc(ev.evidence_type)} • ${esc(ev.status)}</div>
                </div>
                ${btn}
              </div>`;
          });
        }
      }
    } else {
      set('cdEvidenceCount', '—');
      if (evList) evList.innerHTML = '<div class="list-item"><div class="item-title">Could not load evidence.</div></div>';
    }

  } catch (err) {
    if (infoList) infoList.innerHTML = '<div class="list-item"><div class="item-title">Connection error. Is the backend running?</div></div>';
  }
}

if (window.location.pathname.includes('case-details.html')) {
  loadCaseDetails();
}

async function loadEvidence() {
  const tableBody = document.getElementById("evidenceTableBody");
  if (!tableBody) return;

  const token = localStorage.getItem("token");

  try {
    const response = await fetch(API_BASE + "/api/evidence/", {
      headers: { "Authorization": "Bearer " + token }
    });

    if (!checkAuth(response)) return;
    if (!response.ok) {
      tableBody.innerHTML = '<tr><td colspan="5">Failed to load evidence.</td></tr>';
      return;
    }

    const evidence = await response.json();
    tableBody.innerHTML = "";

    if (!evidence.length) {
      tableBody.innerHTML = '<tr><td colspan="5">No evidence found.</td></tr>';
      return;
    }

    evidence.forEach(item => {
      const cls = statusBadge(item.status);
      const linked = item.case_id ? "Case #" + item.case_id
        : (item.report_id ? "Report #" + item.report_id : "—");
      const fileUrl = item.file_path
        ? API_BASE + "/" + item.file_path.replace(/\\/g, '/')
        : null;
      const safeUrl = fileUrl ? esc(fileUrl) : '';
      const viewBtn = fileUrl
        ? `<button class="btn btn-sm btn-soft" onclick="window.open('${safeUrl}','_blank')">Open</button>`
        : `<button class="btn btn-sm btn-soft" disabled style="opacity:0.4;">No File</button>`;
      const role = localStorage.getItem('userRole');
      const delBtn = (role === 'admin' || role === 'officer')
        ? `<button class="btn btn-sm btn-danger" onclick="deleteEvidence(${item.id},this)" style="margin-left:4px;">Delete</button>`
        : '';
      tableBody.innerHTML += `
        <tr>
          <td>#${item.id}</td>
          <td>${esc(item.title || "Evidence Item")}</td>
          <td>${esc(linked)}</td>
          <td><span class="badge ${cls}">${esc(item.status || "Stored")}</span></td>
          <td style="display:flex;gap:4px;">${viewBtn}${delBtn}</td>
        </tr>
      `;
    });
  } catch (err) {
    tableBody.innerHTML = '<tr><td colspan="5">Connection error. Is the backend running?</td></tr>';
  }
}

if (window.location.pathname.includes("evidence.html")) {
  loadEvidence();
}

async function deleteEvidence(id, btn) {
  if (!confirm("Delete this evidence item? This cannot be undone.")) return;
  const token = localStorage.getItem("token");
  try {
    const res = await fetch(API_BASE + "/api/evidence/" + id, {
      method: "DELETE",
      headers: { "Authorization": "Bearer " + token }
    });
    if (!checkAuth(res)) return;
    if (!res.ok) { toast("Delete failed."); return; }
    const row = btn.closest("tr");
    if (row) row.remove();
    toast("Evidence #" + id + " deleted.");
  } catch (e) { toast("Connection error."); }
}
window.deleteEvidence = deleteEvidence;

async function loadNotifications() {
  const container = document.getElementById("notificationsTableBody");
  if (!container) return;

  const token = localStorage.getItem("token");

  try {
    const response = await fetch(API_BASE + "/api/notifications/", {
      headers: { "Authorization": "Bearer " + token }
    });

    if (!checkAuth(response)) return;
    if (!response.ok) {
      container.innerHTML = '<div class="list-item"><div class="item-title">Failed to load notifications.</div></div>';
      return;
    }

    const notifications = await response.json();
    container.innerHTML = "";

    if (!notifications.length) {
      container.innerHTML = '<div class="list-item"><div class="item-title">No notifications yet.</div></div>';
      return;
    }

    notifications.forEach(item => {
      const date = item.created_at
        ? new Date(item.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
        : '';
      const roleLabel = item.target_role === 'all' ? 'All' : item.target_role.charAt(0).toUpperCase() + item.target_role.slice(1);
      const notifRole = localStorage.getItem('userRole');
      const canDelete = notifRole === 'admin' || notifRole === 'officer';
      container.innerHTML += `
        <div class="list-item" id="notif-${item.id}">
          <div style="flex:1;">
            <div class="item-title">${esc(item.title)}</div>
            <div class="item-meta">${esc(item.message)}</div>
            ${date ? `<div class="item-meta" style="margin-top:2px;opacity:0.6;font-size:0.8rem">${esc(date)}</div>` : ''}
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span class="badge info">${esc(roleLabel)}</span>
            ${canDelete ? `<button class="btn btn-sm btn-danger" onclick="deleteNotification(${item.id})">✕</button>` : ''}
          </div>
        </div>
      `;
    });
  } catch (err) {
    container.innerHTML = '<div class="list-item"><div class="item-title">Connection error. Is the backend running?</div></div>';
  }
}

async function createNotification(event) {
  event.preventDefault();

  const token = localStorage.getItem("token");
  const title = document.getElementById("notifTitle").value.trim();
  const message = document.getElementById("notifMessage").value.trim();
  const target_role = document.getElementById("notifTargetRole").value;

  if (!title || !message) return;

  try {
    const response = await fetch(API_BASE + "/api/notifications/", {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ title, message, target_role })
    });

    if (!checkAuth(response)) return;
    if (!response.ok) {
      toast("Failed to send notification.");
      return;
    }

    document.getElementById("createNotifForm").reset();
    toast("Notification sent successfully.");
    loadNotifications();
  } catch (err) {
    toast("Connection error. Is the backend running?");
  }
}

async function deleteNotification(id) {
  if (!confirm("Delete this notification?")) return;
  const token = localStorage.getItem("token");
  try {
    const res = await fetch(API_BASE + "/api/notifications/" + id, {
      method: "DELETE",
      headers: { "Authorization": "Bearer " + token }
    });
    if (!checkAuth(res)) return;
    if (!res.ok) { toast("Delete failed."); return; }
    const el = document.getElementById("notif-" + id);
    if (el) el.remove();
    toast("Notification deleted.");
  } catch (e) { toast("Connection error."); }
}
window.deleteNotification = deleteNotification;

if (window.location.pathname.includes("notifications.html")) {
  loadNotifications().then(() => {
    // mark all visible notifications as read
    const container = document.getElementById('notificationsTableBody');
    if (container) {
      const ids = Array.from(container.querySelectorAll('[id^="notif-"]'))
        .map(el => parseInt(el.id.replace('notif-', ''))).filter(Boolean);
      if (ids.length) {
        localStorage.setItem('readNotifIds', JSON.stringify(ids));
        updateNotificationBadge();
      }
    }
  });
  const notifForm = document.getElementById("createNotifForm");
  if (notifForm) notifForm.addEventListener("submit", createNotification);
}

async function loadAlerts() {
  const container = document.getElementById("alertsListBody");
  if (!container) return;

  const token = localStorage.getItem("token");

  try {
    const response = await fetch(API_BASE + "/api/notifications/", {
      headers: { "Authorization": "Bearer " + token }
    });

    if (!checkAuth(response)) return;
    if (!response.ok) {
      container.innerHTML = '<div class="list-item"><div class="item-title">Failed to load alerts.</div></div>';
      return;
    }

    const items = await response.json();
    container.innerHTML = "";

    if (!items.length) {
      container.innerHTML = '<div class="list-item"><div class="item-title">No alerts at this time.</div></div>';
      return;
    }

    items.forEach(item => {
      const date = item.created_at
        ? new Date(item.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
        : '';
      const roleLabel = item.target_role === 'all' ? 'Public' : item.target_role.charAt(0).toUpperCase() + item.target_role.slice(1);
      container.innerHTML += `
        <div class="list-item">
          <div>
            <div class="item-title">${esc(item.title)}</div>
            <div class="item-meta">${esc(item.message)}</div>
            ${date ? `<div class="item-meta" style="margin-top:2px;opacity:0.6;font-size:0.8rem">${esc(date)}</div>` : ''}
          </div>
          <span class="badge info">${esc(roleLabel)}</span>
        </div>
      `;
    });
  } catch (err) {
    container.innerHTML = '<div class="list-item"><div class="item-title">Connection error. Is the backend running?</div></div>';
  }
}

if (window.location.pathname.includes("alerts.html")) {
  loadAlerts();
}

async function loadProfile() {
  const infoEl = document.getElementById("profileInfo");
  const titleEl = document.getElementById("profileTitle");
  if (!infoEl) return;

  const token = localStorage.getItem("token");
  try {
    const response = await fetch(API_BASE + "/api/auth/me", {
      headers: { "Authorization": "Bearer " + token }
    });
    if (!checkAuth(response)) return;
    if (!response.ok) { infoEl.innerHTML = "Failed to load profile."; return; }

    const user = await response.json();
    if (titleEl) {
      titleEl.textContent = user.role === 'citizen' ? 'Public Profile'
        : user.role === 'admin' ? 'Admin Profile' : 'Officer Profile';
    }
    const roleLabel = user.role.charAt(0).toUpperCase() + user.role.slice(1);
    const statusLabel = user.status.charAt(0).toUpperCase() + user.status.slice(1);
    let html = `<strong>${esc(user.full_name)}</strong><br/>
      Username: ${esc(user.username)}<br/>
      Email: ${esc(user.email || '—')}<br/>
      Role: ${esc(roleLabel)}<br/>
      Status: ${esc(statusLabel)}`;
    if (user.officer_code) html += `<br/>Officer Code: ${esc(user.officer_code)}`;
    infoEl.innerHTML = html;

    const editBtn = document.getElementById('editProfileBtn');
    if (editBtn) {
      editBtn.style.display = 'inline-block';
      editBtn.onclick = () => openEditProfile(user.full_name, user.email || '');
    } else {
      const btn = document.createElement('button');
      btn.textContent = 'Edit Profile';
      btn.className = 'btn btn-soft';
      btn.style.marginTop = '14px';
      btn.onclick = () => openEditProfile(user.full_name, user.email || '');
      infoEl.after(btn);
    }
  } catch (err) {
    infoEl.innerHTML = "Connection error. Is the backend running?";
  }
}

function openEditProfile(currentName, currentEmail) {
  const existing = document.getElementById('_editProfileModal');
  if (existing) existing.remove();

  const modal = document.createElement('div');
  modal.id = '_editProfileModal';
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:9000;display:flex;align-items:center;justify-content:center;';
  modal.innerHTML = `
    <div style="background:#1e293b;border-radius:16px;padding:32px;min-width:320px;max-width:420px;width:90%;box-shadow:0 24px 60px rgba(0,0,0,.4);color:#e2e8f0;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h3 style="margin:0;font-size:1.1rem;">Edit Profile</h3>
        <button onclick="document.getElementById('_editProfileModal').remove()" style="background:none;border:none;color:#94a3b8;font-size:1.4rem;cursor:pointer;">✕</button>
      </div>
      <div style="display:flex;flex-direction:column;gap:14px;">
        <div>
          <label style="font-size:.8rem;opacity:.7;">Full Name</label>
          <input id="_epName" value="${esc(currentName)}" style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#e2e8f0;margin-top:4px;box-sizing:border-box;" />
        </div>
        <div>
          <label style="font-size:.8rem;opacity:.7;">Email</label>
          <input id="_epEmail" type="email" value="${esc(currentEmail)}" style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#e2e8f0;margin-top:4px;box-sizing:border-box;" />
        </div>
        <div id="_epProfileErr" style="color:#f87171;font-size:.85rem;display:none;"></div>
        <button onclick="submitEditProfile()" style="padding:11px;background:#6366f1;color:#fff;border:none;border-radius:10px;font-weight:700;cursor:pointer;">Save Changes</button>
        <hr style="border-color:#334155;margin:4px 0;" />
        <details style="cursor:pointer;">
          <summary style="font-size:.9rem;opacity:.8;outline:none;">Change Password</summary>
          <div style="display:flex;flex-direction:column;gap:10px;margin-top:12px;">
            <input id="_epCurPw" type="password" placeholder="Current password" style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#e2e8f0;box-sizing:border-box;" />
            <input id="_epNewPw" type="password" placeholder="New password (min 6 chars)" style="width:100%;padding:10px;background:#0f172a;border:1px solid #334155;border-radius:8px;color:#e2e8f0;box-sizing:border-box;" />
            <div id="_epPwErr" style="color:#f87171;font-size:.85rem;display:none;"></div>
            <button onclick="submitChangePassword()" style="padding:11px;background:#0f172a;border:1px solid #6366f1;color:#6366f1;border-radius:10px;font-weight:700;cursor:pointer;">Update Password</button>
          </div>
        </details>
      </div>
    </div>`;
  document.body.appendChild(modal);
  modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
}

async function submitEditProfile() {
  const name  = document.getElementById('_epName').value.trim();
  const email = document.getElementById('_epEmail').value.trim();
  const errEl = document.getElementById('_epProfileErr');
  errEl.style.display = 'none';

  if (!name) { errEl.textContent = 'Name cannot be empty.'; errEl.style.display = 'block'; return; }

  const token = localStorage.getItem('token');
  try {
    const res = await fetch(API_BASE + '/api/users/me', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
      body: JSON.stringify({ full_name: name, email: email || null })
    });
    const data = await res.json();
    if (!res.ok) { errEl.textContent = data.detail || 'Update failed.'; errEl.style.display = 'block'; return; }
    localStorage.setItem('userName', data.full_name);
    document.getElementById('_editProfileModal').remove();
    toast('Profile updated successfully.');
    loadProfile();
  } catch (e) { errEl.textContent = 'Connection error.'; errEl.style.display = 'block'; }
}

async function submitChangePassword() {
  const cur   = document.getElementById('_epCurPw').value;
  const nw    = document.getElementById('_epNewPw').value;
  const errEl = document.getElementById('_epPwErr');
  errEl.style.display = 'none';

  if (!cur || !nw) { errEl.textContent = 'Both fields required.'; errEl.style.display = 'block'; return; }
  if (nw.length < 6) { errEl.textContent = 'New password must be at least 6 characters.'; errEl.style.display = 'block'; return; }

  const token = localStorage.getItem('token');
  try {
    const res = await fetch(API_BASE + '/api/users/me/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
      body: JSON.stringify({ current_password: cur, new_password: nw })
    });
    const data = await res.json();
    if (!res.ok) { errEl.textContent = data.detail || 'Failed.'; errEl.style.display = 'block'; return; }
    document.getElementById('_editProfileModal').remove();
    toast('Password changed. Please log in again.');
    setTimeout(() => {
      localStorage.clear();
      const base = window.location.pathname.includes('/authorized/') || window.location.pathname.includes('/unauthorized/') ? '../' : './';
      window.location.href = base + 'index.html';
    }, 2000);
  } catch (e) { errEl.textContent = 'Connection error.'; errEl.style.display = 'block'; }
}

window.openEditProfile  = openEditProfile;
window.submitEditProfile = submitEditProfile;
window.submitChangePassword = submitChangePassword;

if (window.location.pathname.includes("profile.html")) {
  loadProfile();
}

async function loadOfficerDropdown() {
  const select = document.getElementById("caseOfficer");
  if (!select) return;
  const token = localStorage.getItem("token");
  try {
    const response = await fetch(API_BASE + "/api/users/officers", {
      headers: { "Authorization": "Bearer " + token }
    });
    if (!response.ok) return;
    const officers = await response.json();
    select.innerHTML = '<option value="">— Select Officer —</option>';
    officers.forEach(o => {
      const label = o.officer_code ? `${o.full_name} (${o.officer_code})` : o.full_name;
      select.innerHTML += `<option value="${o.id}">${label}</option>`;
    });
  } catch (err) { /* leave default option */ }
}

if (window.location.pathname.includes("add-case.html")) {
  loadOfficerDropdown();
}

async function loadConvertOfficerDropdown() {
  const select = document.getElementById("convertOfficerSelect");
  if (!select) return;
  const token = localStorage.getItem("token");
  try {
    const response = await fetch(API_BASE + "/api/users/officers", {
      headers: { "Authorization": "Bearer " + token }
    });
    if (!response.ok) return;
    const officers = await response.json();
    select.innerHTML = '<option value="">— Select Officer (optional) —</option>';
    officers.forEach(o => {
      const label = o.officer_code ? `${o.full_name} (${o.officer_code})` : o.full_name;
      select.innerHTML += `<option value="${o.id}">${label}</option>`;
    });
  } catch (err) { /* leave default option */ }
}

if (window.location.pathname.includes("reports.html")) {
  loadReports();
  loadConvertOfficerDropdown();
}

// =========================
// REAL CATEGORY CHART (Dashboard)
// =========================

async function loadCategoryChart() {
  const token = localStorage.getItem("token");
  try {
    const response = await fetch(API_BASE + "/api/reports/", {
      headers: { "Authorization": "Bearer " + token }
    });
    if (!checkAuth(response) || !response.ok) return;
    const reports = await response.json();

    const counts = {};
    reports.forEach(r => {
      const cat = r.category || "Other";
      counts[cat] = (counts[cat] || 0) + 1;
    });

    const labels = Object.keys(counts);
    const data = Object.values(counts);

    if (!labels.length) return;
    chart('categoryChart', 'doughnut', labels, data);
  } catch (err) { /* silent — canvas stays empty */ }
}

if (
  window.location.pathname.includes("/authorized/") &&
  window.location.pathname.includes("dashboard.html") &&
  localStorage.getItem('userRole') !== 'citizen'
) {
  loadCategoryChart();
}

// =========================
// ANALYTICS PAGE
// =========================

async function loadAnalyticsStats() {
  const token = localStorage.getItem("token");
  try {
    const response = await fetch(API_BASE + "/api/dashboard/stats", {
      headers: { "Authorization": "Bearer " + token }
    });
    if (!checkAuth(response) || !response.ok) return;
    const data = await response.json();

    const casesEl = document.getElementById("analyticsCases");
    const casesNoteEl = document.getElementById("analyticsCasesNote");
    const resolvedEl = document.getElementById("analyticsResolved");
    const resolvedNoteEl = document.getElementById("analyticsResolvedNote");

    if (casesEl) casesEl.innerText = data.cases || 0;
    if (casesNoteEl) casesNoteEl.innerText = (data.open_cases || 0) + " still open";

    if (resolvedEl) {
      const total = data.cases || 0;
      const open = data.open_cases || 0;
      const rate = total > 0 ? Math.round(((total - open) / total) * 100) : 0;
      resolvedEl.innerText = rate + "%";
    }
    if (resolvedNoteEl) resolvedNoteEl.innerText = (data.cases || 0) + " total cases";
  } catch (err) { /* silent */ }
}

async function loadAnalyticsCharts() {
  const token = localStorage.getItem("token");
  try {
    const response = await fetch(API_BASE + "/api/reports/", {
      headers: { "Authorization": "Bearer " + token }
    });
    if (!checkAuth(response) || !response.ok) return;
    const reports = await response.json();

    // Report Status distribution → monthlyChart canvas
    const statusCounts = {};
    reports.forEach(r => {
      const s = r.status || "unknown";
      statusCounts[s] = (statusCounts[s] || 0) + 1;
    });
    const statusLabels = Object.keys(statusCounts);
    const statusData = Object.values(statusCounts);
    if (statusLabels.length) chart('monthlyChart', 'bar', statusLabels, statusData);

    // Crime Category distribution → riskChart canvas
    const catCounts = {};
    reports.forEach(r => {
      const c = r.category || "Other";
      catCounts[c] = (catCounts[c] || 0) + 1;
    });
    const catLabels = Object.keys(catCounts);
    const catData = Object.values(catCounts);
    if (catLabels.length) chart('riskChart', 'doughnut', catLabels, catData);
  } catch (err) { /* silent */ }
}

if (window.location.pathname.includes("analytics.html")) {
  loadAnalyticsStats();
  loadAnalyticsCharts();
}

function showCitizenSignup() {
  document.getElementById("citizenForm").classList.add("hidden");
  document.getElementById("citizenSignupForm").classList.remove("hidden");
}

function showCitizenLogin() {
  document.getElementById("citizenSignupForm").classList.add("hidden");
  document.getElementById("citizenForm").classList.remove("hidden");
}

async function citizenSignup(event) {
  event.preventDefault();

  const error = document.getElementById("signupError");
  error.textContent = "";

  const response = await fetch(API_BASE + "/api/auth/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      full_name: document.getElementById("signupFullName").value.trim(),
      username: document.getElementById("signupUsername").value.trim(),
      email: document.getElementById("signupEmail").value.trim(),
      password: document.getElementById("signupPassword").value.trim(),
      role: "citizen"
    })
  });

  const data = await response.json();

  if (!response.ok) {
    error.textContent = data.detail || "Signup failed.";
    return;
  }

  alert("Citizen account created successfully. Now login.");
  showCitizenLogin();
}

window.showCitizenSignup = showCitizenSignup;
window.showCitizenLogin = showCitizenLogin;
window.citizenSignup = citizenSignup;

// =========================
// FILE PREVIEW HELPERS
// =========================

function previewFiles(input) {
  const preview = document.getElementById("filePreview");
  if (!preview) return;
  preview.innerHTML = "";
  Array.from(input.files).slice(0, 5).forEach(file => {
    const wrap = document.createElement("div");
    wrap.style.cssText = "position:relative;width:80px;height:80px;border-radius:8px;overflow:hidden;background:rgba(0,0,0,0.08);display:flex;align-items:center;justify-content:center;flex-shrink:0;";
    if (file.type.startsWith("image/")) {
      const img = document.createElement("img");
      img.src = URL.createObjectURL(file);
      img.style.cssText = "width:100%;height:100%;object-fit:cover;";
      wrap.appendChild(img);
    } else {
      const icon = document.createElement("i");
      icon.className = "fa-solid fa-file-pdf";
      icon.style.cssText = "font-size:2rem;opacity:0.5;";
      wrap.appendChild(icon);
    }
    const label = document.createElement("div");
    label.textContent = file.name.length > 10 ? file.name.slice(0, 10) + "…" : file.name;
    label.style.cssText = "position:absolute;bottom:0;left:0;right:0;background:rgba(0,0,0,0.55);color:#fff;font-size:9px;padding:2px 4px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;";
    wrap.appendChild(label);
    preview.appendChild(wrap);
  });
}

function handleFileDrop(event) {
  event.preventDefault();
  const zone = document.getElementById("uploadZone");
  if (zone) zone.style.borderColor = "rgba(0,0,0,0.15)";
  const input = document.getElementById("evidenceFiles");
  if (!input || !event.dataTransfer || !event.dataTransfer.files.length) return;
  const transfer = new DataTransfer();
  Array.from(event.dataTransfer.files).slice(0, 5).forEach(f => transfer.items.add(f));
  input.files = transfer.files;
  previewFiles(input);
}

window.previewFiles = previewFiles;
window.handleFileDrop = handleFileDrop;

// =========================
// CITIZEN SUBMIT REPORT
// =========================

async function submitReport(event) {
  event.preventDefault();

  const category = document.getElementById("reportCategory").value;
  const location = document.getElementById("reportLocation").value.trim();
  const description = document.getElementById("reportDescription").value.trim();
  const errorEl = document.getElementById("reportError");
  const token = localStorage.getItem("token");

  if (errorEl) errorEl.textContent = "";

  const title = category + " — " + location;

  try {
    const response = await fetch(API_BASE + "/api/reports/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token
      },
      body: JSON.stringify({
        title: title,
        category: category,
        description: description,
        location: location,
        priority: "normal"
      })
    });

    const data = await response.json();

    if (!response.ok) {
      if (errorEl) errorEl.textContent = data.detail || "Submission failed.";
      return;
    }

    const filesInput = document.getElementById("evidenceFiles");
    const filesToUpload = filesInput ? Array.from(filesInput.files).slice(0, 5) : [];

    toast("Report submitted successfully. Reference: #" + data.id);
    event.target.reset();

    if (filesToUpload.length > 0) {
      let uploaded = 0;
      for (const file of filesToUpload) {
        const fd = new FormData();
        fd.append("file", file);
        try {
          const r = await fetch(API_BASE + "/api/evidence/upload/report/" + data.id, {
            method: "POST",
            headers: { "Authorization": "Bearer " + token },
            body: fd
          });
          if (r.ok) uploaded++;
        } catch (e) {}
      }
      if (uploaded > 0) toast(uploaded + " file(s) uploaded with your report.");
      const previewEl = document.getElementById("filePreview");
      if (previewEl) previewEl.innerHTML = "";
    }

  } catch (err) {
    if (errorEl) errorEl.textContent = "Connection error. Is the backend running?";
  }
}

window.submitReport = submitReport;

// =========================
// REPORT DETAIL PANEL
// =========================

let _activeReportId = null;
let _activeReportData = null;
let _activeReportEvidence = [];

function openReport(id, title, category, description, location, status, priority, createdAt) {
  _activeReportId = id;
  _activeReportData = { id, title, category, description, location, status, priority };

  document.getElementById("rpId").textContent = "#" + id;
  document.getElementById("rpTitle").textContent = title;
  document.getElementById("rpCategory").textContent = category;
  document.getElementById("rpLocation").textContent = location;
  document.getElementById("rpStatus").textContent = status;
  document.getElementById("rpPriority").textContent = priority;
  document.getElementById("rpDescription").textContent = description;
  const rpCreatedAtEl = document.getElementById("rpCreatedAt");
  if (rpCreatedAtEl) rpCreatedAtEl.textContent = createdAt ? formatPKT(createdAt) : "—";

  const linkedSection = document.getElementById("rpLinkedCaseSection");
  if (linkedSection) linkedSection.style.display = "none";

  document.getElementById("reportDetailPanel").style.display = "block";

  const _convertBtn = document.querySelector("#reportDetailPanel button.btn-primary:not(#rpOpenCaseBtn)");
  if (_convertBtn) {
    if (status === "converted") {
      _convertBtn.disabled = true;
      _convertBtn.innerText = "Already Converted";
    } else {
      _convertBtn.disabled = false;
      _convertBtn.innerHTML = '<i class="fa-solid fa-folder-plus"></i> Convert to Case';
    }
  }

  if (status === "converted" && linkedSection) {
    const _lcToken = localStorage.getItem("token");
    fetch(API_BASE + "/api/cases/", { headers: { "Authorization": "Bearer " + _lcToken } })
      .then(r => r.ok ? r.json() : [])
      .then(cases => {
        const linked = cases.find(c => c.case_no === "CASE-RPT-" + id);
        if (linked) {
          const noEl  = document.getElementById("rpLinkedCaseNo");
          const btnEl = document.getElementById("rpOpenCaseBtn");
          if (noEl)  noEl.textContent = linked.case_no + " — " + linked.title;
          if (btnEl) btnEl.onclick = () => { window.location.href = "case-details.html?id=" + linked.id; };
          linkedSection.style.display = "block";
        }
      }).catch(() => {});
  }

  _activeReportEvidence = [];
  const evidenceList = document.getElementById("rpEvidenceList");
  if (evidenceList) {
    evidenceList.innerHTML = '<p class="page-subtitle" style="margin:0;">Loading...</p>';
    const token = localStorage.getItem("token");
    fetch(API_BASE + "/api/evidence/report/" + id, {
      headers: { "Authorization": "Bearer " + token }
    }).then(r => r.ok ? r.json() : []).then(items => {
      _activeReportEvidence = items;
      const _countNote = document.getElementById("rpEvidenceCountNote");
      if (_countNote) _countNote.textContent = items.length ? "(" + items.length + " file" + (items.length > 1 ? "s" : "") + ")" : "";
      if (!items.length) {
        evidenceList.innerHTML = '<p class="page-subtitle" style="margin:0;">No files uploaded.</p>';
        return;
      }
      evidenceList.innerHTML = "";
      items.forEach(ev => {
        const isImage = ev.evidence_type && ev.evidence_type.startsWith("image/");
        const filename = ev.file_path ? ev.file_path.split(/[\\/]/).pop() : null;
        const url = filename ? API_BASE + "/uploads/" + filename : null;
        const wrap = document.createElement("div");
        wrap.style.cssText = "width:72px;height:72px;border-radius:8px;overflow:hidden;background:rgba(255,255,255,0.06);display:flex;align-items:center;justify-content:center;cursor:pointer;flex-shrink:0;";
        if (isImage && url) {
          wrap.innerHTML = '<img src="' + url + '" style="width:100%;height:100%;object-fit:cover;" title="' + ev.title + '">';
          wrap.onclick = () => window.open(url, "_blank");
        } else if (url) {
          wrap.innerHTML = '<i class="fa-solid fa-file-pdf" style="font-size:2rem;opacity:0.5;" title="' + ev.title + '"></i>';
          wrap.onclick = () => window.open(url, "_blank");
        } else {
          wrap.innerHTML = '<i class="fa-solid fa-file" style="font-size:2rem;opacity:0.5;" title="' + ev.title + '"></i>';
        }
        evidenceList.appendChild(wrap);
      });
    }).catch(() => {
      evidenceList.innerHTML = '<p class="page-subtitle" style="margin:0;">Could not load files.</p>';
    });
  }
}

function closeReportPanel() {
  document.getElementById("reportDetailPanel").style.display = "none";
  _activeReportId = null;
  _activeReportData = null;
}

window.openReport = openReport;
window.closeReportPanel = closeReportPanel;

async function updateReportStatus(status) {
  if (!_activeReportId) return;

  const token = localStorage.getItem("token");

  try {
    const response = await fetch(API_BASE + "/api/reports/" + _activeReportId, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token
      },
      body: JSON.stringify({ status: status })
    });

    if (!checkAuth(response)) return;

    if (!response.ok) {
      toast("Failed to update status.");
      return;
    }

    document.getElementById("rpStatus").textContent = status;
    if (_activeReportData) _activeReportData.status = status;

    toast("Report #" + _activeReportId + " marked as " + status + ".");
    loadReports();

  } catch (err) {
    toast("Connection error.");
  }
}

window.updateReportStatus = updateReportStatus;

async function convertReportToCase() {
  if (!_activeReportData) return;

  const token = localStorage.getItem("token");
  const r = _activeReportData;
  const targetCaseNo = "CASE-RPT-" + r.id;

  if (r.status === "converted") {
    toast("This report has already been converted to a case.");
    const convertBtn = document.querySelector("#reportDetailPanel button.btn-primary");
    if (convertBtn) { convertBtn.disabled = true; convertBtn.innerText = "Already Converted"; }
    return;
  }

  try {
    // Pre-check: look for an existing case with this deterministic case_no
    const checkRes = await fetch(API_BASE + "/api/cases/", {
      headers: { "Authorization": "Bearer " + token }
    });
    if (checkRes.ok) {
      const existing = await checkRes.json();
      const already = existing.find(c => c.case_no === targetCaseNo);
      if (already) {
        toast("This report has already been converted to Case " + targetCaseNo + ".");
        const convertBtn = document.querySelector("#reportDetailPanel button.btn-primary");
        if (convertBtn) { convertBtn.disabled = true; convertBtn.innerText = "Already Converted"; }
        return;
      }
    }

    const response = await fetch(API_BASE + "/api/cases/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token
      },
      body: JSON.stringify({
        case_no: targetCaseNo,
        title: r.title,
        crime_type: r.category,
        location: r.location !== "—" ? r.location : "",
        description: r.description,
        assigned_officer_id: (() => {
          const sel = document.getElementById("convertOfficerSelect");
          if (sel && sel.value) return parseInt(sel.value, 10);
          const uid = parseInt(localStorage.getItem("userId") || "0", 10);
          return uid || null;
        })()
      })
    });

    const data = await response.json();

    if (!checkAuth(response)) return;

    if (response.status === 400 && data.detail && data.detail.toLowerCase().includes("already exists")) {
      toast("This report has already been converted to Case " + targetCaseNo + ".");
      const convertBtn = document.querySelector("#reportDetailPanel button.btn-primary");
      if (convertBtn) { convertBtn.disabled = true; convertBtn.innerText = "Already Converted"; }
      return;
    }

    if (!response.ok) {
      toast("Case creation failed: " + (data.detail || "unknown error"));
      return;
    }

    toast("Case created: " + data.case_no + ". Redirecting to cases...");

    try {
      await fetch(API_BASE + "/api/reports/" + r.id, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "Authorization": "Bearer " + token },
        body: JSON.stringify({ status: "converted" })
      });
      if (_activeReportData) _activeReportData.status = "converted";
    } catch (e) {}

    if (_activeReportEvidence && _activeReportEvidence.length > 0) {
      for (const ev of _activeReportEvidence) {
        try {
          await fetch(API_BASE + "/api/evidence/" + ev.id, {
            method: "PATCH",
            headers: {
              "Content-Type": "application/json",
              "Authorization": "Bearer " + token
            },
            body: JSON.stringify({ case_id: data.id })
          });
        } catch (e) {}
      }
    }

    closeReportPanel();
    setTimeout(() => { window.location.href = "cases.html"; }, 1800);

  } catch (err) {
    toast("Connection error.");
  }
}

window.convertReportToCase = convertReportToCase;

// =========================
// DASHBOARD ACTIVITY
// =========================

async function loadDashboardActivity() {
  const container = document.getElementById("activityList");
  if (!container) return;

  const token = localStorage.getItem("token");

  try {
    const response = await fetch(API_BASE + "/api/dashboard/activity", {
      headers: { "Authorization": "Bearer " + token }
    });

    if (!checkAuth(response)) return;
    if (!response.ok) {
      container.innerHTML = '<div class="list-item"><div class="item-title">Failed to load activity.</div></div>';
      return;
    }

    const logs = await response.json();
    container.innerHTML = "";

    const recent = logs.slice(0, 5);

    if (!recent.length) {
      container.innerHTML = '<div class="list-item"><div class="item-title">No recent activity.</div></div>';
      return;
    }

    recent.forEach(log => {
      const time = formatPKT(log.created_at);
      const who  = log.username || (log.user_id ? "User #" + log.user_id : "System");
      container.innerHTML += `
        <div class="list-item">
          <div>
            <div class="item-title">${esc(log.action)}</div>
            <div class="item-meta">${esc(who)} • ${esc(log.details || "—")} • ${time}</div>
          </div>
          <span class="badge info">Log</span>
        </div>
      `;
    });
  } catch (err) {
    container.innerHTML = '<div class="list-item"><div class="item-title">Activity unavailable.</div></div>';
  }
}

if (
  window.location.pathname.includes("/authorized/") &&
  window.location.pathname.includes("dashboard.html") &&
  localStorage.getItem('userRole') !== 'citizen'
) {
  loadDashboardActivity();
}

// =========================
// ACTIVITY LOG PAGE
// =========================

async function loadActivityLog() {
  const tableBody = document.getElementById("activityLogBody");
  if (!tableBody) return;

  const token = localStorage.getItem("token");

  try {
    const response = await fetch(API_BASE + "/api/dashboard/activity", {
      headers: { "Authorization": "Bearer " + token }
    });

    if (!checkAuth(response)) return;
    if (!response.ok) {
      tableBody.innerHTML = '<tr><td colspan="5">Failed to load activity log.</td></tr>';
      return;
    }

    const logs = await response.json();
    tableBody.innerHTML = "";

    if (!logs.length) {
      tableBody.innerHTML = '<tr><td colspan="5">No activity logged yet.</td></tr>';
      return;
    }

    logs.forEach(log => {
      const timestamp = formatPKT(log.created_at);
      const who = log.username ? esc(log.username) : (log.user_id ? "User #" + log.user_id : "System");
      tableBody.innerHTML += `
        <tr>
          <td>${esc(timestamp)}</td>
          <td>${who}</td>
          <td>${esc(log.action)}</td>
          <td>${esc(log.details || "—")}</td>
          <td><span class="badge info">Log</span></td>
        </tr>
      `;
    });
  } catch (err) {
    tableBody.innerHTML = '<tr><td colspan="5">Connection error. Is the backend running?</td></tr>';
  }
}

if (window.location.pathname.includes("activity-log.html")) {
  loadActivityLog();
}

// =========================
// SETTINGS PAGE
// =========================

async function loadSettingsProfile() {
  const infoEl = document.getElementById("settingsProfileInfo");
  const statusEl = document.getElementById("settingsApiStatus");
  const badgeEl  = document.getElementById("settingsApiBadge");
  if (!infoEl) return;

  const token = localStorage.getItem("token");
  try {
    const res = await fetch(API_BASE + "/api/auth/me", {
      headers: { "Authorization": "Bearer " + token }
    });
    if (!checkAuth(res)) return;

    if (statusEl) statusEl.textContent = "Connected to " + API_BASE;
    if (badgeEl)  badgeEl.className = "badge closed";

    if (!res.ok) { infoEl.innerHTML = '<div class="list-item"><div class="item-title">Failed to load profile.</div></div>'; return; }

    const user = await res.json();
    window._settingsUserName  = user.full_name;
    window._settingsUserEmail = user.email || '';

    const roleLabel   = user.role.charAt(0).toUpperCase() + user.role.slice(1);
    const statusLabel = user.status.charAt(0).toUpperCase() + user.status.slice(1);
    const statusCls   = statusBadge(user.status);

    infoEl.innerHTML = `
      <div class="list-item">
        <div><div class="item-title">Full Name</div><div class="item-meta">${esc(user.full_name)}</div></div>
        <button class="btn btn-sm btn-soft" onclick="openEditProfile('${esc(user.full_name)}','${esc(user.email||'')}')">Edit</button>
      </div>
      <div class="list-item">
        <div><div class="item-title">Username</div><div class="item-meta">${esc(user.username)}</div></div>
        <span class="badge info">Read-only</span>
      </div>
      <div class="list-item">
        <div><div class="item-title">Email</div><div class="item-meta">${esc(user.email || '—')}</div></div>
      </div>
      <div class="list-item">
        <div><div class="item-title">Role</div><div class="item-meta">${esc(roleLabel)}</div></div>
        <span class="badge info">${esc(roleLabel)}</span>
      </div>
      <div class="list-item">
        <div><div class="item-title">Account Status</div><div class="item-meta">Current account state</div></div>
        <span class="badge ${statusCls}">${esc(statusLabel)}</span>
      </div>
      ${user.officer_code ? `<div class="list-item"><div><div class="item-title">Officer Code</div><div class="item-meta">${esc(user.officer_code)}</div></div></div>` : ''}
    `;
  } catch (e) {
    if (statusEl) statusEl.textContent = "Cannot connect to backend";
    if (badgeEl)  { badgeEl.textContent = "Offline"; badgeEl.className = "badge high"; }
    infoEl.innerHTML = '<div class="list-item"><div class="item-title">Connection error.</div></div>';
  }
}

if (window.location.pathname.includes("settings.html")) {
  loadSettingsProfile();
}

// =========================
// ROLE MANAGEMENT
// =========================

async function loadRoleManagement() {
  const tbody = document.getElementById('roleManagementBody');
  const note  = document.getElementById('roleManagementNote');
  if (!tbody) return;

  const token   = localStorage.getItem('token');
  const isAdmin = localStorage.getItem('userRole') === 'admin';
  const selfId  = parseInt(localStorage.getItem('userId') || '0');

  try {
    const res = await fetch(API_BASE + '/api/users/', { headers: { 'Authorization': 'Bearer ' + token } });
    if (!checkAuth(res)) return;
    if (!res.ok) { tbody.innerHTML = '<tr><td colspan="5">Failed to load users.</td></tr>'; return; }

    const users = await res.json();
    if (note) note.textContent = users.length + ' users total';
    tbody.innerHTML = '';

    users.forEach(u => {
      const cls  = u.role === 'admin' ? 'high' : u.role === 'officer' ? 'progress' : 'info';
      const self = u.id === selfId;
      const roleCell = (isAdmin && !self) ? `
        <select onchange="changeUserRole(${u.id},this.value,this)"
          style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:6px;padding:4px 8px;cursor:pointer;">
          <option value="citizen" ${u.role==='citizen'?'selected':''}>Citizen</option>
          <option value="officer" ${u.role==='officer'?'selected':''}>Officer</option>
          <option value="admin"   ${u.role==='admin'  ?'selected':''}>Admin</option>
        </select>` : `<span style="opacity:.5;font-size:.8rem;">${self ? 'You' : 'View only'}</span>`;

      tbody.innerHTML += `
        <tr>
          <td>#${u.id}</td>
          <td>${esc(u.full_name)}</td>
          <td>${esc(u.username)}</td>
          <td><span class="badge ${cls}">${esc(u.role)}</span></td>
          <td>${roleCell}</td>
        </tr>`;
    });
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="5">Connection error.</td></tr>';
  }
}

let _roleChangeBusy = false;

async function changeUserRole(userId, newRole, selectEl) {
  if (_roleChangeBusy) return;
  _roleChangeBusy = true;
  if (selectEl) selectEl.disabled = true;

  const token = localStorage.getItem('token');
  try {
    const res = await fetch(API_BASE + '/api/users/' + userId + '/role', {
      method:  'PATCH',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
      body:    JSON.stringify({ role: newRole })
    });
    let data = {}; try { data = await res.json(); } catch (e) {}
    if (!res.ok) { toast(data.detail || 'Role change failed.'); await loadRoleManagement(); _roleChangeBusy = false; return; }

    if ((newRole === 'officer' || newRole === 'admin') && data.officer_code) {
      // Save code first, then show modal — do NOT reload table (causes infinite onchange loop)
      localStorage.setItem('_pendingOfficerCode', JSON.stringify({
        name: data.full_name, username: data.username,
        role: newRole, code: data.officer_code
      }));
      _showOfficerCodeModal(data.full_name, data.username, newRole, data.officer_code);
      // Table will refresh when modal closes (page reload)
    } else {
      await loadRoleManagement();
      toast('Role updated to "' + newRole + '" for ' + esc(data.username || 'user'));
    }
  } catch (e) {
    toast('Connection error.');
  } finally {
    _roleChangeBusy = false;
  }
}

function _showOfficerCodeModal(name, username, role, code) {
  const existing = document.getElementById('_ocModal');
  if (existing) return;

  // — overlay —
  const modal = document.createElement('div');
  modal.id = '_ocModal';
  modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:999999;display:flex;align-items:center;justify-content:center;';

  // — card —
  const card = document.createElement('div');
  card.style.cssText = 'background:#1e293b;border-radius:16px;padding:36px 32px;max-width:440px;width:90%;box-shadow:0 30px 80px rgba(0,0,0,.8);color:#e2e8f0;text-align:center;';

  // icon
  const icon = document.createElement('div');
  icon.textContent = '🔑';
  icon.style.cssText = 'font-size:3rem;margin-bottom:12px;';

  // title
  const title = document.createElement('h2');
  title.textContent = 'Officer Code Assigned';
  title.style.cssText = 'margin:0 0 8px;font-size:1.3rem;';

  // subtitle
  const sub = document.createElement('p');
  sub.style.cssText = 'opacity:.7;margin-bottom:24px;font-size:.9rem;line-height:1.6;';
  sub.innerHTML = '<b>' + esc(name) + '</b> (@' + esc(username) + ') is now <b>' + esc(role) + '</b>.<br><span style="color:#fbbf24;">⚠️ Share this code — they MUST use it to login.</span>';

  // code box
  const codeBox = document.createElement('div');
  codeBox.style.cssText = 'background:#0f172a;border:2px dashed #6366f1;border-radius:12px;padding:20px 16px;margin-bottom:16px;';
  const codeLabel = document.createElement('div');
  codeLabel.textContent = 'OFFICER CODE';
  codeLabel.style.cssText = 'font-size:.7rem;opacity:.5;margin-bottom:8px;letter-spacing:2px;';
  const codeText = document.createElement('div');
  codeText.textContent = code;
  codeText.style.cssText = 'font-family:monospace;font-size:2rem;font-weight:900;letter-spacing:4px;color:#a5b4fc;';
  codeBox.appendChild(codeLabel);
  codeBox.appendChild(codeText);

  // copy message
  const copyMsg = document.createElement('div');
  copyMsg.style.cssText = 'color:#22c55e;font-size:.85rem;min-height:20px;margin-bottom:12px;';

  // copy button
  const copyBtn = document.createElement('button');
  copyBtn.textContent = '📋 Copy Code';
  copyBtn.style.cssText = 'width:100%;padding:13px;background:#6366f1;color:#fff;border:none;border-radius:10px;font-weight:700;cursor:pointer;font-size:1rem;margin-bottom:10px;display:block;';
  copyBtn.addEventListener('click', function() {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(code).then(function() {
        copyMsg.textContent = '✓ Copied!';
      }).catch(function() {
        copyMsg.textContent = 'Code: ' + code;
      });
    } else {
      copyMsg.textContent = 'Code: ' + code + ' (select and copy manually)';
    }
  });

  // countdown label
  const timerLabel = document.createElement('div');
  timerLabel.style.cssText = 'opacity:.45;font-size:.75rem;margin-bottom:10px;';
  timerLabel.textContent = 'Auto-closes in 60:00';

  // close button
  const closeBtn = document.createElement('button');
  closeBtn.textContent = '✓ I\'ve noted the code — Close';
  closeBtn.style.cssText = 'width:100%;padding:13px;background:#334155;color:#e2e8f0;border:none;border-radius:10px;font-weight:700;cursor:pointer;font-size:1rem;display:block;';

  card.appendChild(icon);
  card.appendChild(title);
  card.appendChild(sub);
  card.appendChild(codeBox);
  card.appendChild(copyMsg);
  card.appendChild(copyBtn);
  card.appendChild(timerLabel);
  card.appendChild(closeBtn);
  modal.appendChild(card);
  document.body.appendChild(modal);

  // 1-hour countdown — modal stays until close button OR 3600s
  let _secsLeft = 3600;
  const _ticker = setInterval(function() {
    _secsLeft--;
    const m = Math.floor(_secsLeft / 60);
    const s = _secsLeft % 60;
    timerLabel.textContent = 'Auto-closes in ' + String(m).padStart(2,'0') + ':' + String(s).padStart(2,'0');
    if (_secsLeft <= 0) {
      clearInterval(_ticker);
      modal.parentNode && modal.parentNode.removeChild(modal);
    }
  }, 1000);

  closeBtn.addEventListener('click', function() {
    clearInterval(_ticker);
    localStorage.removeItem('_pendingOfficerCode');
    modal.parentNode && modal.parentNode.removeChild(modal);
    window.location.reload();
  });
}

// On page load: restore modal if page refreshed before user closed it
if (window.location.pathname.includes('role-management.html')) {
  const _pending = localStorage.getItem('_pendingOfficerCode');
  if (_pending) {
    try {
      const p = JSON.parse(_pending);
      setTimeout(function() {
        _showOfficerCodeModal(p.name, p.username, p.role, p.code);
      }, 800);
    } catch(e) { localStorage.removeItem('_pendingOfficerCode'); }
  }
}

window.changeUserRole = changeUserRole;

if (window.location.pathname.includes('role-management.html')) {
  loadRoleManagement();
}

// =========================
// EMERGENCY SOS
// =========================

async function sendSOS() {
  if (!confirm('Send Emergency SOS? This creates an URGENT report for immediate police response.')) return;
  const token = localStorage.getItem('token');
  const btn   = document.getElementById('sosBtn');
  const res2  = document.getElementById('sosResult');
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...'; }
  try {
    const res = await fetch(API_BASE + '/api/reports/', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
      body:    JSON.stringify({
        title:       'EMERGENCY SOS — Immediate Assistance Required',
        category:    'Emergency SOS',
        description: 'Emergency SOS triggered at ' + new Date().toLocaleString('en-PK', { timeZone: 'Asia/Karachi' }),
        location:    '',
        priority:    'urgent'
      })
    });
    const data = await res.json();
    if (!res.ok) {
      if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Send SOS'; }
      toast('SOS failed: ' + (data.detail || 'Error')); return;
    }
    if (btn) { btn.innerHTML = '✓ SOS Sent'; btn.style.background = '#16a34a'; }
    if (res2) { res2.textContent = 'Alert sent! Reference #' + data.id + '. Authorities notified.'; res2.style.display = 'block'; }
    toast('🚨 SOS Alert sent! Reference #' + data.id);
  } catch (e) {
    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Send SOS'; }
    toast('Connection error. Call police directly: 15');
  }
}

function shareLocation() {
  const resEl = document.getElementById('locationResult');
  if (!navigator.geolocation) {
    if (resEl) resEl.textContent = 'Location not available on this device.';
    return;
  }
  navigator.geolocation.getCurrentPosition(
    pos => {
      const txt = 'Lat: ' + pos.coords.latitude.toFixed(5) + ', Lng: ' + pos.coords.longitude.toFixed(5);
      if (resEl) resEl.textContent = txt;
      navigator.clipboard.writeText(txt).catch(() => {});
      toast('Location copied: ' + txt);
    },
    () => {
      if (resEl) resEl.textContent = 'Permission denied. Enable location in browser.';
    }
  );
}

window.sendSOS        = sendSOS;
window.shareLocation  = shareLocation;

// =========================
// NOTIFICATION UNREAD BADGE
// =========================

async function updateNotificationBadge() {
  const token = localStorage.getItem('token');
  if (!token) return;
  try {
    const res = await fetch(API_BASE + '/api/notifications/', { headers: { 'Authorization': 'Bearer ' + token } });
    if (!res.ok) return;
    const items = await res.json();
    const readIds = JSON.parse(localStorage.getItem('readNotifIds') || '[]');
    const unread  = items.filter(n => !readIds.includes(n.id)).length;

    const topActions = document.querySelector('.top-actions');
    if (!topActions) return;
    const bellBtn = Array.from(topActions.querySelectorAll('button.btn-soft'))[1];
    if (!bellBtn) return;

    const old = bellBtn.querySelector('._nb');
    if (old) old.remove();
    if (unread > 0) {
      const badge = document.createElement('span');
      badge.className = '_nb';
      badge.textContent = unread > 9 ? '9+' : unread;
      badge.style.cssText = 'position:absolute;top:-5px;right:-5px;background:#ef4444;color:#fff;border-radius:50%;min-width:16px;height:16px;font-size:10px;display:flex;align-items:center;justify-content:center;font-weight:800;padding:0 2px;pointer-events:none;';
      bellBtn.style.position = 'relative';
      bellBtn.appendChild(badge);
    }
  } catch (e) {}
}

document.addEventListener('DOMContentLoaded', () => {
  if (localStorage.getItem('token')) updateNotificationBadge();
});

// =========================
// CITIZEN REPORT DELETE
// =========================

async function deleteCitizenReport(id, btn) {
  if (!confirm('Withdraw report #' + id + '? This cannot be undone.')) return;
  const token = localStorage.getItem('token');
  try {
    const res = await fetch(API_BASE + '/api/reports/' + id, {
      method:  'DELETE',
      headers: { 'Authorization': 'Bearer ' + token }
    });
    let data = {}; try { data = await res.json(); } catch (e) {}
    if (!res.ok) { toast(data.detail || 'Cannot withdraw this report.'); return; }
    const row = btn.closest('tr');
    if (row) row.remove();
    toast('Report #' + id + ' withdrawn successfully.');
  } catch (e) { toast('Connection error.'); }
}
window.deleteCitizenReport = deleteCitizenReport;

// =========================
// COMMUNITY SAFETY
// =========================

async function loadCommunitySafety() {
  const token = localStorage.getItem('token');
  try {
    const [statsRes, alertsRes] = await Promise.all([
      fetch(API_BASE + '/api/dashboard/stats', { headers: { 'Authorization': 'Bearer ' + token } }),
      fetch(API_BASE + '/api/notifications/', { headers: { 'Authorization': 'Bearer ' + token } })
    ]);

    if (statsRes.ok) {
      const s = await statsRes.json();
      const r = document.getElementById('csReports'); if (r) r.textContent = s.reports || 0;
      const c = document.getElementById('csCases');   if (c) c.textContent = s.cases || 0;
    }

    const alertsList = document.getElementById('csAlertsList');
    if (alertsRes.ok && alertsList) {
      const items = await alertsRes.json();
      const csAl = document.getElementById('csAlerts'); if (csAl) csAl.textContent = items.length;
      if (!items.length) { alertsList.innerHTML = '<div class="list-item"><div class="item-title">No public alerts at this time.</div></div>'; return; }
      alertsList.innerHTML = '';
      items.slice(0, 5).forEach(n => {
        alertsList.innerHTML += `<div class="list-item"><div><div class="item-title">${esc(n.title)}</div><div class="item-meta">${esc(n.message)}</div></div><span class="badge info">${n.target_role === 'all' ? 'Public' : esc(n.target_role)}</span></div>`;
      });
    }
  } catch (e) {}
}

if (window.location.pathname.includes('community-safety.html')) loadCommunitySafety();

// =========================
// CONTACT US FORM
// =========================

async function submitContactUs(event) {
  event.preventDefault();
  const subject = document.getElementById('contactSubject').value.trim();
  const location = document.getElementById('contactLocation').value.trim();
  const message = document.getElementById('contactMessage').value.trim();
  const errEl = document.getElementById('contactError');
  if (errEl) errEl.style.display = 'none';
  if (!subject || !message) { if (errEl) { errEl.textContent = 'Subject and message are required.'; errEl.style.display = 'block'; } return; }

  const token = localStorage.getItem('token');
  try {
    const res = await fetch(API_BASE + '/api/reports/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
      body: JSON.stringify({ title: 'Contact Us: ' + subject, category: 'General Inquiry', description: message, location: location || '', priority: 'normal' })
    });
    const data = await res.json();
    if (!res.ok) { if (errEl) { errEl.textContent = data.detail || 'Failed to send.'; errEl.style.display = 'block'; } return; }
    toast('Message sent! Reference #' + data.id + '. We will respond shortly.');
    document.getElementById('contactUsForm').reset();
  } catch (e) { if (errEl) { errEl.textContent = 'Connection error.'; errEl.style.display = 'block'; } }
}

if (window.location.pathname.includes('contact-us.html')) {
  const f = document.getElementById('contactUsForm');
  if (f) f.addEventListener('submit', submitContactUs);
}

// =========================
// ANONYMOUS TIP SUBMIT
// =========================

async function submitTip(event) {
  event.preventDefault();
  const category = document.getElementById('tipCategory').value;
  const location = document.getElementById('tipLocation').value.trim();
  const description = document.getElementById('tipDescription').value.trim();
  const errEl = document.getElementById('tipError');
  if (errEl) errEl.style.display = 'none';
  if (!description) { if (errEl) { errEl.textContent = 'Please describe what you observed.'; errEl.style.display = 'block'; } return; }

  const token = localStorage.getItem('token');
  try {
    const res = await fetch(API_BASE + '/api/reports/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
      body: JSON.stringify({ title: 'Anonymous Tip: ' + category, category: category, description: description, location: location || '', priority: 'normal' })
    });
    const data = await res.json();
    if (!res.ok) { if (errEl) { errEl.textContent = data.detail || 'Failed to submit.'; errEl.style.display = 'block'; } return; }
    toast('Tip submitted! Reference #' + data.id + '. Thank you for helping.');
    document.getElementById('tipForm').reset();
  } catch (e) { if (errEl) { errEl.textContent = 'Connection error.'; errEl.style.display = 'block'; } }
}

if (window.location.pathname.includes('tip-details.html')) {
  const f = document.getElementById('tipForm');
  if (f) f.addEventListener('submit', submitTip);
}

// =========================
// FORGOT PASSWORD
// =========================

function showForgotPassword() {
  const existing = document.getElementById('_fpModal');
  if (existing) existing.remove();

  const modal = document.createElement('div');
  modal.id = '_fpModal';
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:99999;display:flex;align-items:center;justify-content:center;';

  const box = document.createElement('div');
  box.style.cssText = 'background:#1e293b;border-radius:16px;padding:32px;max-width:380px;width:90%;color:#e2e8f0;';

  const title = document.createElement('h3');
  title.textContent = 'Forgot Password';
  title.style.cssText = 'margin:0 0 8px;';

  const sub = document.createElement('p');
  sub.textContent = 'Enter your username. A reset request will be sent to the administrator.';
  sub.style.cssText = 'opacity:.7;font-size:.9rem;margin-bottom:16px;line-height:1.5;';

  const input = document.createElement('input');
  input.type = 'text';
  input.placeholder = 'Your username';
  input.className = 'form-control';
  input.style.cssText = 'width:100%;margin-bottom:12px;box-sizing:border-box;';

  const errEl = document.createElement('div');
  errEl.style.cssText = 'color:#f87171;font-size:.85rem;min-height:18px;margin-bottom:10px;';

  const submitBtn = document.createElement('button');
  submitBtn.textContent = 'Send Reset Request';
  submitBtn.style.cssText = 'width:100%;padding:11px;background:#6366f1;color:#fff;border:none;border-radius:10px;font-weight:700;cursor:pointer;margin-bottom:8px;';

  const cancelBtn = document.createElement('button');
  cancelBtn.textContent = 'Cancel';
  cancelBtn.style.cssText = 'width:100%;padding:11px;background:#334155;color:#e2e8f0;border:none;border-radius:10px;font-weight:700;cursor:pointer;';

  submitBtn.addEventListener('click', async function() {
    const username = input.value.trim();
    if (!username) { errEl.textContent = 'Please enter your username.'; return; }
    errEl.textContent = '';
    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending...';
    try {
      const res = await fetch(API_BASE + '/api/auth/forgot-password?username=' + encodeURIComponent(username), { method: 'POST' });
      const data = await res.json();
      modal.remove();
      toast(data.message || 'Reset request sent!');
    } catch (e) {
      errEl.textContent = 'Connection error.';
      submitBtn.disabled = false;
      submitBtn.textContent = 'Send Reset Request';
    }
  });

  cancelBtn.addEventListener('click', () => modal.remove());

  box.appendChild(title);
  box.appendChild(sub);
  box.appendChild(input);
  box.appendChild(errEl);
  box.appendChild(submitBtn);
  box.appendChild(cancelBtn);
  modal.appendChild(box);
  document.body.appendChild(modal);
}

window.showForgotPassword = showForgotPassword;

// =========================
// CSV EXPORT
// =========================

function exportCSV(data, filename) {
  if (!data || !data.length) { toast('No data to export.'); return; }
  const keys = Object.keys(data[0]);
  const rows = [keys.join(',')];
  data.forEach(row => {
    rows.push(keys.map(k => '"' + String(row[k] ?? '').replace(/"/g, '""') + '"').join(','));
  });
  const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
  toast('Exported: ' + filename);
}

async function exportReportsCSV() {
  const token = localStorage.getItem('token');
  try {
    const res = await fetch(API_BASE + '/api/reports/?limit=1000', { headers: { 'Authorization': 'Bearer ' + token } });
    if (!res.ok) { toast('Export failed.'); return; }
    exportCSV(await res.json(), 'reports_' + new Date().toISOString().slice(0,10) + '.csv');
  } catch (e) { toast('Connection error.'); }
}

async function exportCasesCSV() {
  const token = localStorage.getItem('token');
  try {
    const res = await fetch(API_BASE + '/api/cases/?limit=1000', { headers: { 'Authorization': 'Bearer ' + token } });
    if (!res.ok) { toast('Export failed.'); return; }
    exportCSV(await res.json(), 'cases_' + new Date().toISOString().slice(0,10) + '.csv');
  } catch (e) { toast('Connection error.'); }
}

window.exportReportsCSV = exportReportsCSV;
window.exportCasesCSV   = exportCasesCSV;

// =========================
// MAP INIT
// =========================

async function initMap() {
  const mapEl = document.getElementById("crimeMap");
  if (!mapEl || typeof L === "undefined") return;

  const map = L.map("crimeMap").setView([24.8607, 67.0011], 12);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap contributors"
  }).addTo(map);

  const offsets = [
    [0,0],[0.02,0.02],[-0.02,0.03],[0.03,-0.02],
    [-0.03,-0.01],[0.01,-0.03],[-0.01,0.04],[0.04,0.01]
  ];
  const statusIcon = { open: '🔴', in_progress: '🟡', closed: '🟢' };

  const token = localStorage.getItem('token');
  try {
    const res = await fetch(API_BASE + "/api/cases/?limit=8", {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (res.ok) {
      const cases = await res.json();
      if (!cases.length) {
        L.marker([24.8607, 67.0011]).addTo(map)
          .bindPopup('<b>ForensiX ZR Unit</b><br>No active cases.').openPopup();
        return;
      }
      cases.forEach((c, i) => {
        const [dlat, dlng] = offsets[i % offsets.length];
        const icon = statusIcon[c.status] || '⚪';
        L.marker([24.8607 + dlat, 67.0011 + dlng])
          .addTo(map)
          .bindPopup(
            `<b>${esc(c.case_no)}</b><br>` +
            `${esc(c.title)}<br>` +
            `📍 ${esc(c.location || 'Location not specified')}<br>` +
            `${icon} ${esc(c.status)}`
          );
      });
    } else {
      L.marker([24.8607, 67.0011]).addTo(map).bindPopup('ForensiX ZR Unit Coverage Area').openPopup();
    }
  } catch (e) {
    L.marker([24.8607, 67.0011]).addTo(map).bindPopup('ForensiX ZR Unit Coverage Area').openPopup();
  }
}

if (
  window.location.pathname.includes("/authorized/") &&
  window.location.pathname.includes("dashboard.html")
) {
  initMap();
}

// =========================
// LOAD OFFICERS
// =========================

async function loadOfficers() {
  const tableBody = document.getElementById("officersTableBody");
  if (!tableBody) return;

  const token = localStorage.getItem("token");

  try {
    const response = await fetch(API_BASE + "/api/users/officers", {
      headers: { "Authorization": "Bearer " + token }
    });

    if (!checkAuth(response)) return;
    if (!response.ok) {
      tableBody.innerHTML = '<tr><td colspan="5">Failed to load officers.</td></tr>';
      return;
    }

    const officers = await response.json();
    tableBody.innerHTML = "";

    if (!officers.length) {
      tableBody.innerHTML = '<tr><td colspan="5">No officers found.</td></tr>';
      return;
    }

    officers.forEach(officer => {
      const cls = statusBadge(officer.status);
      tableBody.innerHTML += `
        <tr>
          <td>#${officer.id}</td>
          <td>${esc(officer.full_name)}</td>
          <td>${esc(officer.officer_code || "—")}</td>
          <td><span class="badge ${cls}">${esc(officer.status)}</span></td>
          <td><button class="btn btn-sm btn-soft" onclick="viewUserDetail(${officer.id},'${esc(officer.full_name)}','${esc(officer.role||'officer')}','${esc(officer.status)}','${esc(officer.email||'')}','${esc(officer.officer_code||'')}')">Profile</button></td>
        </tr>
      `;
    });
  } catch (err) {
    tableBody.innerHTML = '<tr><td colspan="5">Connection error. Is the backend running?</td></tr>';
  }
}

if (window.location.pathname.includes("officers.html")) {
  loadOfficers();
}

// =========================
// USER / OFFICER DETAIL MODAL
// =========================

function viewUserDetail(id, name, role, status, email, officerCode) {
  const existing = document.getElementById('_userDetailModal');
  if (existing) existing.remove();

  const currentUserRole = localStorage.getItem('userRole');
  const isAdmin = currentUserRole === 'admin';

  const roleLabel   = role.charAt(0).toUpperCase() + role.slice(1);
  const statusLabel = status.charAt(0).toUpperCase() + status.slice(1);
  const statusCls   = statusBadge(status);
  const isActive    = status === 'active';

  const actionBtns = isAdmin ? `
    <div style="display:flex;gap:8px;margin-top:8px;">
      <button onclick="toggleUserStatus(${id},'${isActive ? 'inactive' : 'active'}')" style="flex:1;padding:10px;background:${isActive ? '#ef4444' : '#22c55e'};color:#fff;border:none;border-radius:10px;font-weight:700;cursor:pointer;">
        ${isActive ? 'Deactivate Account' : 'Activate Account'}
      </button>
      <button onclick="document.getElementById('_userDetailModal').remove()" style="flex:1;padding:10px;background:#334155;color:#e2e8f0;border:none;border-radius:10px;font-weight:700;cursor:pointer;">
        Close
      </button>
    </div>` : `
    <button onclick="document.getElementById('_userDetailModal').remove()" style="width:100%;padding:10px;background:#334155;color:#e2e8f0;border:none;border-radius:10px;font-weight:700;cursor:pointer;margin-top:8px;">Close</button>`;

  const modal = document.createElement('div');
  modal.id = '_userDetailModal';
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:9000;display:flex;align-items:center;justify-content:center;';
  modal.innerHTML = `
    <div style="background:#1e293b;border-radius:16px;padding:32px;min-width:320px;max-width:420px;width:90%;box-shadow:0 24px 60px rgba(0,0,0,.4);color:#e2e8f0;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h3 style="margin:0;font-size:1.1rem;">${esc(roleLabel)} Profile</h3>
        <button onclick="document.getElementById('_userDetailModal').remove()" style="background:none;border:none;color:#94a3b8;font-size:1.4rem;cursor:pointer;">✕</button>
      </div>
      <div style="display:flex;flex-direction:column;gap:12px;">
        <div><span style="opacity:.6;font-size:.8rem;">Full Name</span><div style="font-weight:700;margin-top:2px;">${esc(name)}</div></div>
        <div><span style="opacity:.6;font-size:.8rem;">Role</span><div style="margin-top:2px;">${esc(roleLabel)}</div></div>
        <div><span style="opacity:.6;font-size:.8rem;">Status</span><div style="margin-top:4px;"><span class="badge ${statusCls}" id="_udStatusBadge">${esc(statusLabel)}</span></div></div>
        ${email ? `<div><span style="opacity:.6;font-size:.8rem;">Email</span><div style="margin-top:2px;">${esc(email)}</div></div>` : ''}
        ${officerCode ? `<div><span style="opacity:.6;font-size:.8rem;">Officer Code</span><div style="font-family:monospace;margin-top:2px;">${esc(officerCode)}</div></div>` : ''}
        <div><span style="opacity:.6;font-size:.8rem;">User ID</span><div style="margin-top:2px;">#${id}</div></div>
        <div id="_udStatusErr" style="color:#f87171;font-size:.85rem;display:none;"></div>
        ${actionBtns}
      </div>
    </div>`;
  document.body.appendChild(modal);
  modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
}

async function toggleUserStatus(userId, newStatus) {
  const currentUserId = parseInt(localStorage.getItem('userId') || '0');
  if (userId === currentUserId) {
    toast("You cannot change your own account status.");
    return;
  }
  const token = localStorage.getItem('token');
  const errEl = document.getElementById('_udStatusErr');
  try {
    const res = await fetch(API_BASE + `/api/users/${userId}/status?status=${newStatus}`, {
      method: 'PATCH',
      headers: { 'Authorization': 'Bearer ' + token }
    });
    let data = {};
    try { data = await res.json(); } catch (e) {}
    if (!res.ok) {
      if (errEl) { errEl.textContent = data.detail || 'Update failed.'; errEl.style.display = 'block'; }
      return;
    }
    document.getElementById('_userDetailModal').remove();
    toast(`User #${userId} marked as ${newStatus}.`);
    if (typeof loadUsers   === 'function') loadUsers();
    if (typeof loadOfficers === 'function') loadOfficers();
  } catch (e) {
    if (errEl) { errEl.textContent = 'Connection error.'; errEl.style.display = 'block'; }
  }
}

window.viewUserDetail   = viewUserDetail;
window.toggleUserStatus = toggleUserStatus;

// =========================
// CITIZEN REPORT TRACKER
// =========================

function trackReport(id, title, category, status, location, createdAt) {
  const existing = document.getElementById('_trackModal');
  if (existing) existing.remove();

  const statusLabels = { pending: 'Received', verified: 'Under Review', resolved: 'Resolved', rejected: 'Rejected', converted: 'Converted to Case' };
  const statusCls = statusBadge(status);
  const statusLabel = statusLabels[status] || status;
  const dateStr = createdAt ? formatPKT(createdAt) : '—';

  const steps = ['pending','verified','resolved'];
  const currentStep = steps.indexOf(status);

  const modal = document.createElement('div');
  modal.id = '_trackModal';
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:9000;display:flex;align-items:center;justify-content:center;';
  modal.innerHTML = `
    <div style="background:#1e293b;border-radius:16px;padding:32px;min-width:320px;max-width:440px;width:90%;box-shadow:0 24px 60px rgba(0,0,0,.4);color:#e2e8f0;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;">
        <h3 style="margin:0;font-size:1.1rem;">Report #${id} — Status</h3>
        <button onclick="document.getElementById('_trackModal').remove()" style="background:none;border:none;color:#94a3b8;font-size:1.4rem;cursor:pointer;">✕</button>
      </div>
      <div style="display:flex;flex-direction:column;gap:12px;">
        <div><span style="opacity:.6;font-size:.8rem;">Title</span><div style="font-weight:700;margin-top:2px;">${esc(title)}</div></div>
        <div><span style="opacity:.6;font-size:.8rem;">Category</span><div style="margin-top:2px;">${esc(category)}</div></div>
        <div><span style="opacity:.6;font-size:.8rem;">Location</span><div style="margin-top:2px;">${esc(location)}</div></div>
        <div><span style="opacity:.6;font-size:.8rem;">Submitted</span><div style="margin-top:2px;">${esc(dateStr)}</div></div>
        <div><span style="opacity:.6;font-size:.8rem;">Current Status</span><div style="margin-top:4px;"><span class="badge ${statusCls}">${esc(statusLabel)}</span></div></div>
        <div style="margin-top:8px;display:flex;gap:0;align-items:center;">
          ${steps.map((s,i) => {
            const done = i <= currentStep;
            const color = done ? '#22c55e' : '#334155';
            const lbl = { pending:'Received', verified:'Under Review', resolved:'Resolved' }[s];
            return `<div style="display:flex;flex-direction:column;align-items:center;flex:1;">
              <div style="width:28px;height:28px;border-radius:50%;background:${color};display:flex;align-items:center;justify-content:center;font-size:.75rem;font-weight:700;">${done ? '✓' : (i+1)}</div>
              <div style="font-size:.7rem;opacity:.7;margin-top:4px;text-align:center;">${lbl}</div>
            </div>${i < steps.length-1 ? `<div style="flex:1;height:2px;background:${i < currentStep ? '#22c55e' : '#334155'};margin-bottom:18px;"></div>` : ''}`;
          }).join('')}
        </div>
      </div>
    </div>`;
  document.body.appendChild(modal);
  modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
}

window.trackReport = trackReport;

// =========================
// LOAD USERS
// =========================

async function loadUsers() {
  const tableBody = document.getElementById("usersTableBody");
  if (!tableBody) return;

  const token = localStorage.getItem("token");

  try {
    const response = await fetch(API_BASE + "/api/users/", {
      headers: { "Authorization": "Bearer " + token }
    });

    if (!checkAuth(response)) return;
    if (!response.ok) {
      tableBody.innerHTML = '<tr><td colspan="5">Failed to load users.</td></tr>';
      return;
    }

    const users = await response.json();
    tableBody.innerHTML = "";

    if (!users.length) {
      tableBody.innerHTML = '<tr><td colspan="5">No users found.</td></tr>';
      return;
    }

    users.forEach(user => {
      const cls = statusBadge(user.status);
      tableBody.innerHTML += `
        <tr>
          <td>#${user.id}</td>
          <td>${esc(user.full_name)}</td>
          <td>${esc(user.role)}</td>
          <td><span class="badge ${cls}">${esc(user.status)}</span></td>
          <td><button class="btn btn-sm btn-soft" onclick="viewUserDetail(${user.id},'${esc(user.full_name)}','${esc(user.role)}','${esc(user.status)}','${esc(user.email||'')}','${esc(user.officer_code||'')}')">View</button></td>
        </tr>
      `;
    });
  } catch (err) {
    tableBody.innerHTML = '<tr><td colspan="5">Connection error. Is the backend running?</td></tr>';
  }
}

if (window.location.pathname.includes("users.html")) {
  loadUsers();
}

// =========================
// CITIZEN MY REPORTS
// =========================

async function loadMyReports() {
  const tableBody = document.getElementById("myReportsTableBody");
  if (!tableBody) return;

  const token = localStorage.getItem("token");

  try {
    const response = await fetch(API_BASE + "/api/reports/", {
      headers: { "Authorization": "Bearer " + token }
    });

    if (!checkAuth(response)) return;
    if (!response.ok) {
      tableBody.innerHTML = '<tr><td colspan="5">Failed to load reports.</td></tr>';
      return;
    }

    const reports = await response.json();
    tableBody.innerHTML = "";

    if (!reports.length) {
      tableBody.innerHTML = '<tr><td colspan="5">No reports submitted yet.</td></tr>';
      return;
    }

    const citizenLabel = { pending: "Received", verified: "Under Review", resolved: "Resolved", rejected: "Rejected" };

    reports.forEach(report => {
      const cls = statusBadge(report.status);
      const label = citizenLabel[report.status] || report.status || "Received";
      const canWithdraw = (report.status === 'pending');
      tableBody.innerHTML += `
        <tr>
          <td>#${report.id}</td>
          <td>${esc(report.title)}</td>
          <td>${esc(report.category || "General")}</td>
          <td><span class="badge ${cls}">${label}</span></td>
          <td style="display:flex;gap:4px;">
            <button class="btn btn-sm btn-soft" onclick="trackReport(${report.id},'${esc(report.title)}','${esc(report.category||'General')}','${esc(report.status||'pending')}','${esc(report.location||'—')}','${esc(report.created_at||'')}')">Track</button>
            ${canWithdraw ? `<button class="btn btn-sm btn-danger" onclick="deleteCitizenReport(${report.id},this)">Withdraw</button>` : ''}
          </td>
        </tr>
      `;
    });
  } catch (err) {
    tableBody.innerHTML = '<tr><td colspan="5">Connection error. Is the backend running?</td></tr>';
  }
}

if (window.location.pathname.includes("my-reports.html")) {
  loadMyReports();
}

// =========================
// CITIZEN DASHBOARD
// =========================

async function loadCitizenDashboard() {
  const token = localStorage.getItem("token");

  const countEl = document.getElementById("citizenReportCount");
  if (countEl) {
    try {
      const res = await fetch(API_BASE + "/api/reports/", {
        headers: { "Authorization": "Bearer " + token }
      });
      if (res.ok) {
        const reports = await res.json();
        countEl.textContent = reports.length;
      }
    } catch (e) { countEl.textContent = "—"; }
  }

  const alertsList = document.getElementById("citizenAlertsList");
  if (alertsList) {
    try {
      const res = await fetch(API_BASE + "/api/notifications/", {
        headers: { "Authorization": "Bearer " + token }
      });
      if (res.ok) {
        const items = await res.json();
        if (!items.length) {
          alertsList.innerHTML = '<div class="list-item"><div class="item-title">No alerts at this time.</div></div>';
        } else {
          alertsList.innerHTML = "";
          items.slice(0, 3).forEach(n => {
            alertsList.innerHTML += `
              <div class="list-item">
                <div>
                  <div class="item-title">${esc(n.title)}</div>
                  <div class="item-meta">${esc(n.message)}</div>
                </div>
                <span class="badge info">${n.target_role === "all" ? "Public" : esc(n.target_role)}</span>
              </div>`;
          });
        }
      }
    } catch (e) {
      alertsList.innerHTML = '<div class="list-item"><div class="item-title">Could not load alerts.</div></div>';
    }
  }
}

if (
  window.location.pathname.includes("/unauthorized/") &&
  window.location.pathname.includes("dashboard.html")
) {
  loadCitizenDashboard();
}

})();