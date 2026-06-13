/* ═══════════════════════════════════════════════════
   MPIPS Dashboard — Application Controller
   ═══════════════════════════════════════════════════ */

// ── Utility Functions ──────────────────────────────

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}

function truncateId(id, len = 12) {
  if (!id) return '—';
  return id.length > len ? id.substring(0, len) + '…' : id;
}

function formatTimestamp(iso) {
  if (!iso) return '—';
  const date = new Date(iso);
  const now = new Date();
  const diff = Math.floor((now - date) / 1000);
  if (diff < 5) return 'just now';
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function formatDuration(startIso, endIso) {
  if (!startIso) return '—';
  const start = new Date(startIso);
  const end = endIso ? new Date(endIso) : new Date();
  const diff = Math.max(0, Math.floor((end - start) / 1000));
  const mins = Math.floor(diff / 60);
  const secs = diff % 60;
  if (mins === 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

function categoryColor(cat) {
  const map = {
    io: 'category-io',
    geometry: 'category-geometry',
    adjustments: 'category-adjustments',
    filtering: 'category-filtering',
    advanced: 'category-advanced',
    iqa: 'category-iqa',
  };
  return map[cat] || 'category-io';
}

function statusBadgeClass(status) {
  const map = {
    queued: 'badge-queued',
    running: 'badge-running',
    completed: 'badge-completed',
    failed: 'badge-failed',
    cancelled: 'badge-cancelled',
  };
  return map[status] || 'badge-queued';
}

function categoryLabel(cat) {
  const labels = {
    io: 'I/O',
    geometry: 'Geometry',
    adjustments: 'Adjustments',
    filtering: 'Filtering',
    advanced: 'Advanced',
    iqa: 'IQA',
  };
  return labels[cat] || cat;
}


// ── API Client ─────────────────────────────────────

class ApiClient {
  constructor(baseUrl = window.location.origin) {
    this.baseUrl = baseUrl;
  }

  getToken() {
    return localStorage.getItem('mpips_token') || '';
  }

  setToken(token) {
    localStorage.setItem('mpips_token', token);
  }

  clearToken() {
    localStorage.removeItem('mpips_token');
  }

  async request(method, path, body = null) {
    const headers = { 'Accept': 'application/json' };
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const opts = { method, headers };
    if (body) {
      headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const resp = await fetch(`${this.baseUrl}${path}`, opts);
    if (!resp.ok) {
      const text = await resp.text().catch(() => '');
      throw new Error(`HTTP ${resp.status}: ${text || resp.statusText}`);
    }
    return resp.json();
  }

  async getHealth() {
    const resp = await fetch(`${this.baseUrl}/health`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return resp.json();
  }

  async testAuth() {
    return this.request('GET', '/v1/secure-test');
  }

  async getNodes() {
    return this.request('GET', '/v1/nodes');
  }

  async getJobs() {
    return this.request('GET', '/v1/jobs');
  }

  async getJob(id) {
    return this.request('GET', `/v1/jobs/${id}`);
  }

  async cancelJob(id) {
    return this.request('DELETE', `/v1/jobs/${id}`);
  }
}


// ── Dashboard App ──────────────────────────────────

class DashboardApp {
  constructor() {
    this.api = new ApiClient();
    this.activeTab = 'overview';
    this.health = null;
    this.nodes = [];
    this.jobs = [];
    this.nodeFilter = 'all';
    this.nodeSearch = '';
    this.healthInterval = null;
    this.jobsInterval = null;
    this.autoRefreshJobs = false;
  }

  init() {
    this.bindNavigation();
    this.bindAuthModal();
    this.bindJobModal();

    if (this.api.getToken()) {
      this.hideAuthModal();
      this.connect();
    } else {
      this.showAuthModal();
    }
  }

  // ── Navigation ───────────────────────────────────

  bindNavigation() {
    document.querySelectorAll('.nav-item[data-tab]').forEach(btn => {
      btn.addEventListener('click', () => {
        this.switchTab(btn.dataset.tab);
      });
    });

    const disconnectBtn = document.getElementById('disconnectBtn');
    if (disconnectBtn) {
      disconnectBtn.addEventListener('click', () => {
        this.api.clearToken();
        this.setConnectionStatus('error', 'Disconnected');
        this.showToast('Disconnected from MPIPS', 'info');
        this.showAuthModal();
      });
    }
  }

  switchTab(tabName) {
    this.activeTab = tabName;

    // Update nav active states
    document.querySelectorAll('.nav-item[data-tab]').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // Show/hide content
    document.querySelectorAll('.tab-content').forEach(section => {
      section.classList.toggle('active', section.id === `tab-${tabName}`);
    });

    // Update topbar title
    const titles = { overview: 'Overview', nodes: 'Node Catalog', jobs: 'Jobs' };
    document.getElementById('pageTitle').textContent = titles[tabName] || tabName;

    // Update topbar actions
    this.renderTopbarActions(tabName);

    // Load data for tab
    if (tabName === 'overview') this.loadOverview();
    if (tabName === 'nodes') this.loadNodes();
    if (tabName === 'jobs') this.loadJobs();
  }

  renderTopbarActions(tab) {
    const container = document.getElementById('topbarActions');
    container.innerHTML = '';

    if (tab === 'jobs') {
      container.innerHTML = `
        <label class="auto-refresh-toggle">
          <input type="checkbox" class="toggle-switch" id="autoRefreshToggle"
                 ${this.autoRefreshJobs ? 'checked' : ''}>
          <span>Auto-refresh</span>
        </label>
        <button class="btn btn-ghost btn-sm" id="refreshJobsBtn">⟳ Refresh</button>
      `;
      document.getElementById('autoRefreshToggle').addEventListener('change', (e) => {
        this.autoRefreshJobs = e.target.checked;
        this.setupJobsAutoRefresh();
      });
      document.getElementById('refreshJobsBtn').addEventListener('click', () => {
        this.loadJobs();
      });
    }
  }

  // ── Auth Modal ───────────────────────────────────

  bindAuthModal() {
    const connectBtn = document.getElementById('authConnectBtn');
    const input = document.getElementById('authTokenInput');

    connectBtn.addEventListener('click', () => this.handleConnect());
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.handleConnect();
    });
  }

  async handleConnect() {
    const input = document.getElementById('authTokenInput');
    const error = document.getElementById('authError');
    const btn = document.getElementById('authConnectBtn');
    const token = input.value.trim();

    if (!token) {
      error.textContent = 'Please enter a Bearer token';
      error.classList.add('visible');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Connecting…';
    error.classList.remove('visible');

    this.api.setToken(token);

    try {
      await this.api.testAuth();
      this.hideAuthModal();
      this.connect();
    } catch (err) {
      error.textContent = `Connection failed: ${err.message}`;
      error.classList.add('visible');
      this.api.clearToken();
    } finally {
      btn.disabled = false;
      btn.textContent = 'Connect';
    }
  }

  showAuthModal() {
    document.getElementById('authModal').style.display = 'flex';
  }

  hideAuthModal() {
    document.getElementById('authModal').style.display = 'none';
  }

  // ── Connection ───────────────────────────────────

  async connect() {
    try {
      await this.api.testAuth();
      this.health = await this.api.getHealth();
      this.setConnectionStatus('connected', 'Connected');
      this.showToast('Connected to MPIPS', 'success');
      this.loadOverview();
      this.startHealthPolling();
    } catch (err) {
      this.setConnectionStatus('error', 'Authentication failed');
      this.showToast(`Authentication failed: ${err.message}`, 'error');
      this.api.clearToken();
      this.showAuthModal();
    }
  }

  setConnectionStatus(state, text) {
    const el = document.getElementById('connectionStatus');
    el.className = `connection-status ${state}`;
    el.querySelector('.status-text').textContent = text;
  }

  startHealthPolling() {
    if (this.healthInterval) clearInterval(this.healthInterval);
    this.healthInterval = setInterval(async () => {
      try {
        this.health = await this.api.getHealth();
        this.setConnectionStatus('connected', 'Connected');
        if (this.activeTab === 'overview') this.renderOverview();
      } catch {
        this.setConnectionStatus('error', 'Disconnected');
      }
    }, 30000);
  }

  // ── Overview Tab ─────────────────────────────────

  async loadOverview() {
    try {
      this.health = await this.api.getHealth();
      if (this.nodes.length === 0) {
        try {
          const data = await this.api.getNodes();
          this.nodes = data.nodes || [];
        } catch { /* nodes will load in nodes tab */ }
      }
      this.renderOverview();
    } catch (err) {
      this.showToast(`Failed to load health: ${err.message}`, 'error');
    }
  }

  renderOverview() {
    const h = this.health || {};

    document.getElementById('statNodesValue').textContent = this.nodes.length || '—';
    document.getElementById('statStatusValue').textContent = h.status || '—';
    document.getElementById('statStatusValue').className = 'stat-value' +
      (h.status === 'healthy' ? ' healthy-text' : '');
    document.getElementById('statVersionValue').textContent = h.version || '—';

    // Uptime detail
    document.getElementById('statUptimeDetail').textContent = h.uptime_human || '';

    // Health details card
    const redis = h.redis || {};
    const celery = h.celery || {};
    document.getElementById('healthRedisStatus').textContent = redis.status || '—';
    document.getElementById('healthRedisStatus').className =
      redis.status === 'connected' ? 'detail-value accent-text' : 'detail-value';
    document.getElementById('healthCeleryStatus').textContent = celery.status || '—';
    document.getElementById('healthCeleryWorkers').textContent =
      celery.workers !== undefined ? celery.workers : '—';
    document.getElementById('healthEnvironment').textContent = h.environment || '—';
    document.getElementById('healthUptime').textContent = h.uptime_human || '—';
  }

  // ── Nodes Tab ────────────────────────────────────

  async loadNodes() {
    const container = document.getElementById('nodesGrid');
    if (this.nodes.length === 0) {
      container.innerHTML = '<div class="loading-state"><div class="spinner spinner-lg"></div><span>Loading nodes…</span></div>';
      try {
        const data = await this.api.getNodes();
        this.nodes = data.nodes || [];
      } catch (err) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠</div><div class="empty-state-title">Failed to load nodes</div><div class="empty-state-desc">${escapeHtml(err.message)}</div></div>`;
        return;
      }
    }
    this.bindNodeFilters();
    this.renderNodes();
  }

  bindNodeFilters() {
    // Search
    const search = document.getElementById('nodeSearchInput');
    if (search && !search.dataset.bound) {
      search.addEventListener('input', (e) => {
        this.nodeSearch = e.target.value.toLowerCase();
        this.renderNodes();
      });
      search.dataset.bound = 'true';
    }

    // Category filters
    document.querySelectorAll('.category-filter-btn').forEach(btn => {
      if (!btn.dataset.bound) {
        btn.addEventListener('click', () => {
          this.nodeFilter = btn.dataset.category;
          document.querySelectorAll('.category-filter-btn').forEach(b =>
            b.classList.toggle('active', b.dataset.category === this.nodeFilter)
          );
          this.renderNodes();
        });
        btn.dataset.bound = 'true';
      }
    });
  }

  renderNodes() {
    const container = document.getElementById('nodesGrid');
    const countEl = document.getElementById('nodeCount');

    let filtered = this.nodes;

    if (this.nodeFilter !== 'all') {
      filtered = filtered.filter(n => n.category === this.nodeFilter);
    }

    if (this.nodeSearch) {
      filtered = filtered.filter(n =>
        (n.name || '').toLowerCase().includes(this.nodeSearch) ||
        (n.description || '').toLowerCase().includes(this.nodeSearch) ||
        (n.id || '').toLowerCase().includes(this.nodeSearch)
      );
    }

    countEl.textContent = `${filtered.length} node${filtered.length !== 1 ? 's' : ''}`;

    if (filtered.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">⬡</div>
          <div class="empty-state-title">No nodes found</div>
          <div class="empty-state-desc">Try adjusting your search or filter criteria.</div>
        </div>`;
      return;
    }

    container.innerHTML = filtered.map(node => this.renderNodeCard(node)).join('');

    // Bind expand toggles
    container.querySelectorAll('.node-card').forEach(card => {
      card.addEventListener('click', () => {
        card.classList.toggle('expanded');
      });
    });
  }

  renderNodeCard(node) {
    const catClass = categoryColor(node.category);
    const inputs = node.inputs || [];
    const outputs = node.outputs || [];
    const params = node.parameters || [];

    let paramsTable = '';
    if (params.length > 0) {
      const rows = params.map(p => `
        <tr>
          <td>${escapeHtml(p.name)}</td>
          <td>${escapeHtml(p.type)}</td>
          <td>${p.default !== null && p.default !== undefined ? escapeHtml(String(p.default)) : '—'}</td>
          <td>${p.min !== null && p.min !== undefined ? p.min : '—'} / ${p.max !== null && p.max !== undefined ? p.max : '—'}</td>
          <td>${p.options ? escapeHtml(p.options.join(', ')) : '—'}</td>
          <td>${escapeHtml(p.description || '')}</td>
        </tr>
      `).join('');

      paramsTable = `
        <table class="param-table">
          <thead><tr>
            <th>Name</th><th>Type</th><th>Default</th><th>Min/Max</th><th>Options</th><th>Description</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>`;
    } else {
      paramsTable = '<div style="color: var(--text-muted); font-size: var(--text-xs);">No configurable parameters</div>';
    }

    return `
      <div class="node-card ${catClass}">
        <div class="node-card-header">
          <div class="node-category-stripe"></div>
          <div class="node-card-body">
            <div class="node-card-title">
              ${escapeHtml(node.name)}
              <span class="version-badge">v${escapeHtml(node.version)}</span>
            </div>
            <div class="node-card-desc">${escapeHtml(node.description || '')}</div>
          </div>
        </div>
        <div class="node-card-meta">
          <span>⬤ ${inputs.length} in</span>
          <span>◯ ${outputs.length} out</span>
          <span>⚙ ${params.length} params</span>
          <span class="node-card-expand">▼</span>
        </div>
        <div class="node-card-details">
          ${paramsTable}
        </div>
      </div>`;
  }

  // ── Jobs Tab ─────────────────────────────────────

  async loadJobs() {
    const container = document.getElementById('jobsTableBody');
    container.innerHTML = '<tr><td colspan="6"><div class="loading-state"><div class="spinner"></div><span>Loading…</span></div></td></tr>';

    try {
      const data = await this.api.getJobs();
      this.jobs = data || [];
      this.renderJobs();
    } catch (err) {
      container.innerHTML = '';
      this.renderJobsEmpty();
    }
  }

  renderJobs() {
    const container = document.getElementById('jobsTableBody');
    if (this.jobs.length === 0) {
      this.renderJobsEmpty();
      return;
    }

    container.innerHTML = this.jobs.map(job => this.renderJobRow(job)).join('');

    // Render the job lookup search/filter area
    this.renderJobLookup();

    // Bind row clicks to open the modal
    container.querySelectorAll('.job-row').forEach(row => {
      row.addEventListener('click', () => {
        const jobId = row.dataset.jobId;
        const job = this.jobs.find(j => j.job_id === jobId);
        if (job) {
          this.showJobDetail(job);
        }
      });
    });
  }

  renderJobsEmpty() {
    const container = document.getElementById('jobsTableBody');
    container.innerHTML = `
      <tr>
        <td colspan="6">
          <div class="empty-state">
            <div class="empty-state-icon">▶</div>
            <div class="empty-state-title">No jobs to display</div>
            <div class="empty-state-desc">
              Jobs are submitted from the MIPC control plane.
              Enter a Job ID below to look up its status.
            </div>
          </div>
        </td>
      </tr>`;

    // Show the job lookup input
    this.renderJobLookup();
  }

  renderJobLookup() {
    const toolbar = document.getElementById('jobLookupArea');
    if (!toolbar || toolbar.dataset.bound) return;

    toolbar.innerHTML = `
      <div class="search-group job-lookup-group">
        <span class="search-icon">🔍</span>
        <input type="text" class="search-input" id="jobIdInput"
               placeholder="Enter a Job ID to look up status…">
      </div>
      <button class="btn btn-primary btn-sm" id="lookupJobBtn">Look up</button>`;

    document.getElementById('lookupJobBtn').addEventListener('click', () => this.lookupJob());
    document.getElementById('jobIdInput').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.lookupJob();
    });
    toolbar.dataset.bound = 'true';
  }

  async lookupJob() {
    const input = document.getElementById('jobIdInput');
    const jobId = input.value.trim();
    if (!jobId) return;

    try {
      const job = await this.api.getJob(jobId);
      this.showJobDetail(job);
    } catch (err) {
      this.showToast(`Job not found: ${err.message}`, 'error');
    }
  }

  renderJobRow(job) {
    return `
      <tr class="job-row" data-job-id="${escapeHtml(job.job_id)}">
        <td class="job-id-cell">${escapeHtml(truncateId(job.job_id))}</td>
        <td><span class="badge ${statusBadgeClass(job.status)}">${escapeHtml(job.status)}</span></td>
        <td>
          <div class="progress-bar">
            <div class="progress-bar-fill ${job.status === 'running' ? 'running' : ''}"
                 style="width: ${job.progress || 0}%"></div>
          </div>
          <div class="progress-text">${(job.progress || 0).toFixed(0)}%</div>
        </td>
        <td class="job-id-cell">${escapeHtml(truncateId(job.tenant_id))}</td>
        <td>${formatTimestamp(job.started_at)}</td>
        <td>${formatDuration(job.started_at, job.finished_at)}</td>
      </tr>`;
  }

  setupJobsAutoRefresh() {
    if (this.jobsInterval) {
      clearInterval(this.jobsInterval);
      this.jobsInterval = null;
    }
    if (this.autoRefreshJobs) {
      this.jobsInterval = setInterval(() => this.loadJobs(), 5000);
    }
  }

  // ── Job Detail Modal ─────────────────────────────

  bindJobModal() {
    document.getElementById('jobDetailClose').addEventListener('click', () => {
      this.hideJobDetail();
    });
    document.getElementById('jobDetailModal').addEventListener('click', (e) => {
      if (e.target.id === 'jobDetailModal') this.hideJobDetail();
    });
  }

  showJobDetail(job) {
    const modal = document.getElementById('jobDetailModal');
    const body = document.getElementById('jobDetailBody');

    const outputs = job.outputs && Object.keys(job.outputs).length > 0
      ? `<div class="json-block">${escapeHtml(JSON.stringify(job.outputs, null, 2))}</div>`
      : '<span style="color: var(--text-muted);">No outputs yet</span>';

    const errorSection = job.error
      ? `<div class="detail-section">
           <div class="detail-section-title">Error Details</div>
           <div class="json-block" style="color: var(--status-failed);">${escapeHtml(typeof job.error === 'string' ? job.error : JSON.stringify(job.error, null, 2))}</div>
         </div>`
      : '';

    const cancelBtn = ['queued', 'running'].includes(job.status)
      ? `<div class="detail-section"><button class="btn btn-danger" id="cancelJobBtn">✕ Cancel Job</button></div>`
      : '';

    body.innerHTML = `
      <div style="margin-bottom: var(--space-md);">
        <span class="badge ${statusBadgeClass(job.status)}" style="font-size: var(--text-sm); padding: 4px 14px;">${escapeHtml(job.status)}</span>
      </div>

      <div class="progress-bar progress-bar-wide">
        <div class="progress-bar-fill ${job.status === 'running' ? 'running' : ''}"
             style="width: ${job.progress || 0}%"></div>
      </div>

      <div class="detail-grid">
        <span class="detail-label">Job ID</span>
        <span class="detail-value mono">${escapeHtml(job.job_id)}</span>

        <span class="detail-label">Tenant ID</span>
        <span class="detail-value mono">${escapeHtml(job.tenant_id)}</span>

        <span class="detail-label">Execution ID</span>
        <span class="detail-value mono">${escapeHtml(job.external_execution_id)}</span>

        <span class="detail-label">Progress</span>
        <span class="detail-value">${(job.progress || 0).toFixed(1)}%</span>

        <span class="detail-label">Current Node</span>
        <span class="detail-value">${escapeHtml(job.current_node || '—')}</span>

        <span class="detail-label">Started</span>
        <span class="detail-value">${job.started_at ? new Date(job.started_at).toLocaleString() : '—'}</span>

        <span class="detail-label">Finished</span>
        <span class="detail-value">${job.finished_at ? new Date(job.finished_at).toLocaleString() : '—'}</span>

        <span class="detail-label">Duration</span>
        <span class="detail-value">${formatDuration(job.started_at, job.finished_at)}</span>
      </div>

      <div class="detail-section">
        <div class="detail-section-title">Outputs</div>
        ${outputs}
      </div>

      ${errorSection}
      ${cancelBtn}`;

    if (document.getElementById('cancelJobBtn')) {
      document.getElementById('cancelJobBtn').addEventListener('click', async () => {
        try {
          await this.api.cancelJob(job.job_id);
          this.showToast('Job cancelled', 'success');
          this.hideJobDetail();
          this.loadJobs();
        } catch (err) {
          this.showToast(`Cancel failed: ${err.message}`, 'error');
        }
      });
    }

    modal.style.display = 'flex';
  }

  hideJobDetail() {
    document.getElementById('jobDetailModal').style.display = 'none';
  }

  // ── Toast Notifications ──────────────────────────

  showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
}


// ── Initialize ─────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  const app = new DashboardApp();
  app.init();
});
