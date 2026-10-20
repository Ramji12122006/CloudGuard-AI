/**
 * CloudGuard AI — User Interface & View Controller
 * Module: ui.js
 */

const CloudGuardUI = (() => {
  // DOM Elements cache
  let views = {};
  let navLinks = [];
  let toastContainer = null;

  function init() {
    // Cache views
    const viewElements = document.querySelectorAll('.view-section');
    viewElements.forEach(el => {
      const id = el.id.replace('view-', '');
      views[id] = el;
    });

    navLinks = Array.from(document.querySelectorAll('.sidebar-nav a, .mobile-nav a'));
    toastContainer = document.getElementById('toast-container');

    // Register navigation clicks
    navLinks.forEach(link => {
      link.addEventListener('click', e => {
        e.preventDefault();
        const targetView = link.getAttribute('data-view');
        switchView(targetView);
        closeMobileSidebar();
      });
    });

    // Mobile Hamburger
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('sidebar');
    if (menuToggle && sidebar) {
      menuToggle.addEventListener('click', () => {
        sidebar.classList.toggle('open');
      });
    }

    // Close mobile sidebar on backdrop click
    const backdrop = document.getElementById('sidebar-backdrop');
    if (backdrop) {
      backdrop.addEventListener('click', closeMobileSidebar);
    }
  }

  function closeMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
      sidebar.classList.remove('open');
    }
  }

  function switchView(viewName) {
    if (!views[viewName]) {
      viewName = 'overview';
    }

    // Update active nav links
    navLinks.forEach(link => {
      if (link.getAttribute('data-view') === viewName) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });

    // Toggle view containers
    Object.keys(views).forEach(v => {
      if (v === viewName) {
        views[v].classList.remove('hidden');
      } else {
        views[v].classList.add('hidden');
      }
    });

    // Update URL hash without reload
    window.location.hash = `#${viewName}`;

    // Update current view in state
    CloudGuardState.getState().currentView = viewName;

    // Trigger render for newly activated view
    renderCurrentView(viewName);
  }

  function renderCurrentView(viewName) {
    const state = CloudGuardState.getState();
    const hasData = state.records && state.records.length > 0;

    // Toggle Empty State vs Content
    document.querySelectorAll('.empty-state-notice').forEach(el => {
      el.style.display = hasData ? 'none' : 'flex';
    });
    document.querySelectorAll('.data-content-wrapper').forEach(el => {
      el.style.display = hasData ? 'block' : 'none';
    });

    // Update Topbar Badge
    updateDataStatusBar(state);

    if (!hasData) return;

    // View-specific renders
    switch (viewName) {
      case 'overview':
        renderOverview(state);
        break;
      case 'explorer':
        renderCostExplorer(state);
        break;
      case 'anomalies':
        renderAnomalies(state);
        break;
      case 'forecast':
        renderForecast(state);
        break;
      case 'optimization':
        renderOptimization(state);
        break;
      case 'reports':
        renderReports(state);
        break;
      case 'settings':
        renderSettings(state);
        break;
    }
  }

  function updateDataStatusBar(state) {
    const statusEl = document.getElementById('global-data-status');
    const dateRangeEl = document.getElementById('global-date-range');
    const sym = state.settings.symbol || '$';

    if (state.records && state.records.length > 0) {
      const net = state.summary ? state.summary.netSpend : 0;
      statusEl.innerHTML = `<span class="status-indicator online"></span> <strong>${state.records.length.toLocaleString()}</strong> records loaded (<span class="text-cyan font-mono">${sym}${net.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>)`;
      
      if (state.summary && state.summary.dateRange) {
        dateRangeEl.textContent = `${state.summary.dateRange.min} → ${state.summary.dateRange.max} (${state.summary.dateRange.uniqueDays} days)`;
      }
    } else {
      statusEl.innerHTML = `<span class="status-indicator offline"></span> No billing data loaded`;
      dateRangeEl.textContent = 'Ready for import';
    }
  }

  /**
   * Render Overview Dashboard Cards & Charts
   */
  function renderOverview(state) {
    const agg = state.analysis.aggregations;
    if (!agg) return;

    const sym = state.settings.symbol || '$';

    // 1. Total Cloud Spending
    document.getElementById('kpi-total-spend').textContent = `${sym}${agg.totalSpend.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    
    // Total Credits callout if any
    const creditsEl = document.getElementById('kpi-total-credits');
    if (agg.totalCredits > 0) {
      creditsEl.textContent = `Includes -${sym}${agg.totalCredits.toFixed(2)} credits`;
      creditsEl.style.display = 'block';
    } else {
      creditsEl.style.display = 'none';
    }

    // 2. Average Daily Cost
    document.getElementById('kpi-avg-daily').textContent = `${sym}${agg.avgDailyCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById('kpi-days-count').textContent = `Across ${agg.uniqueDays} billing days`;

    // 3. Highest Cost Cloud Service
    document.getElementById('kpi-highest-service').textContent = agg.highestService.service;
    document.getElementById('kpi-highest-service-cost').textContent = `${sym}${agg.highestService.cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} (${agg.highestService.percentage}%)`;

    // 4. Period Comparison
    const comp = agg.periodComparison;
    const compEl = document.getElementById('kpi-period-change');
    const compBadge = document.getElementById('kpi-period-badge');

    if (comp.percentChange !== 0) {
      const isUp = comp.trend === 'up';
      compEl.textContent = `${isUp ? '+' : ''}${comp.percentChange.toFixed(1)}%`;
      compBadge.className = `kpi-badge ${isUp ? 'badge-rose' : 'badge-emerald'}`;
      compBadge.innerHTML = `${isUp ? '▲' : '▼'} ${sym}${Math.abs(comp.costDifference).toFixed(2)} vs prior period`;
    } else {
      compEl.textContent = '0.0%';
      compBadge.className = 'kpi-badge badge-neutral';
      compBadge.textContent = 'No period change';
    }

    // 5. Detected Anomalies Count
    const anomCount = (state.analysis.anomalies || []).length;
    document.getElementById('kpi-anomalies-count').textContent = anomCount;
    const anomBadge = document.getElementById('kpi-anomalies-badge');
    if (anomCount > 0) {
      anomBadge.className = 'kpi-badge badge-rose';
      anomBadge.textContent = `${anomCount} spike${anomCount > 1 ? 's' : ''} detected`;
    } else {
      anomBadge.className = 'kpi-badge badge-emerald';
      anomBadge.textContent = 'Normal spending pattern';
    }

    // 6. Estimated Potential Savings
    const recs = state.analysis.recommendations || [];
    const totalPotentialSavings = recs.reduce((sum, r) => sum + (r.estimatedSavings || 0), 0);
    document.getElementById('kpi-potential-savings').textContent = `${sym}${totalPotentialSavings.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById('kpi-recs-count').textContent = `${recs.length} actionable recommendation${recs.length !== 1 ? 's' : ''}`;

    // Render Overview Charts
    CloudGuardCharts.renderOverviewDaily('chart-overview-daily', agg.dailyTrend);
    CloudGuardCharts.renderOverviewService('chart-overview-service', agg.byService);
    CloudGuardCharts.renderOverviewRegion('chart-overview-region', agg.byRegion);

    // Recent Records preview (top 5)
    renderOverviewRecentTable(state.records.slice(0, 5), sym);

    // Recent Anomalies preview (top 3)
    renderOverviewRecentAnomalies(state.analysis.anomalies.slice(0, 3), sym);

    // Top Recommendations preview (top 2)
    renderOverviewTopRecs(recs.slice(0, 2), sym);
  }

  function renderOverviewRecentTable(recentRecords, sym) {
    const tbody = document.getElementById('overview-recent-table-body');
    if (!tbody) return;

    if (recentRecords.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-center text-slate">No recent records.</td></tr>`;
      return;
    }

    tbody.innerHTML = recentRecords
      .map(
        r => `
      <tr>
        <td class="font-mono text-xs">${r.usage_date}</td>
        <td><strong>${escapeHtml(r.service)}</strong></td>
        <td><span class="badge badge-slate">${escapeHtml(r.region)}</span></td>
        <td class="text-xs text-slate">${escapeHtml(r.tag_project || 'untagged')}</td>
        <td class="font-mono text-right ${r.cost_amount < 0 ? 'text-emerald' : 'text-white'}">
          ${r.cost_amount < 0 ? '-' : ''}${sym}${Math.abs(r.cost_amount).toFixed(2)}
        </td>
      </tr>
    `
      )
      .join('');
  }

  function renderOverviewRecentAnomalies(recentAnomalies, sym) {
    const container = document.getElementById('overview-recent-anomalies');
    if (!container) return;

    if (recentAnomalies.length === 0) {
      container.innerHTML = `<div class="empty-mini-card"><p class="text-slate text-sm">No critical anomalies detected in current dataset.</p></div>`;
      return;
    }

    container.innerHTML = recentAnomalies
      .map(
        a => `
      <div class="mini-alert-card border-left-${a.severity.toLowerCase()}">
        <div class="mini-alert-header">
          <span class="font-bold text-sm">${escapeHtml(a.service)}</span>
          <span class="badge badge-${a.severity.toLowerCase()}">${a.severity}</span>
        </div>
        <p class="text-xs text-slate mt-1">${a.date} — Actual: <span class="font-mono text-rose">${sym}${a.actualCost.toFixed(2)}</span> vs Baseline: <span class="font-mono">${sym}${a.baselineCost.toFixed(2)}</span></p>
        <p class="text-xs text-slate mt-1">${escapeHtml(a.reason)}</p>
      </div>
    `
      )
      .join('');
  }

  function renderOverviewTopRecs(recs, sym) {
    const container = document.getElementById('overview-top-recommendations');
    if (!container) return;

    if (recs.length === 0) {
      container.innerHTML = `<div class="empty-mini-card"><p class="text-slate text-sm">No optimization recommendations available for this data.</p></div>`;
      return;
    }

    container.innerHTML = recs
      .map(
        r => `
      <div class="mini-rec-card">
        <div class="mini-rec-header">
          <span class="badge badge-cyan">${escapeHtml(r.category)}</span>
          ${r.estimatedSavings ? `<span class="badge badge-emerald">Save ~${sym}${r.estimatedSavings.toFixed(2)}</span>` : ''}
        </div>
        <h5 class="font-bold text-sm mt-1 text-white">${escapeHtml(r.title)}</h5>
        <p class="text-xs text-slate mt-1">${escapeHtml(r.evidence)}</p>
      </div>
    `
      )
      .join('');
  }

  /**
   * Render Cost Explorer
   */
  function renderCostExplorer(state) {
    const agg = state.analysis.aggregations;
    if (!agg) return;

    const sym = state.settings.symbol || '$';

    // Populate filter dropdowns if not already populated
    populateFilterDropdowns(state);

    // Render Explorer Chart
    const granularity = state.filters.granularity || 'daily';
    const chartType = document.getElementById('explorer-chart-type') ? document.getElementById('explorer-chart-type').value : 'bar';
    const groupedTrend = CloudGuardCostEngine.aggregateByGranularity(agg.dailyTrend, granularity);
    CloudGuardCharts.renderExplorerMain('chart-explorer-main', groupedTrend, chartType);

    // Paginated Table
    const paginated = CloudGuardCostEngine.paginateRecords(state.analysis.filteredRecords, state.pagination);
    renderExplorerTable(paginated, sym);
  }

  function populateFilterDropdowns(state) {
    const serviceSelect = document.getElementById('filter-service');
    const regionSelect = document.getElementById('filter-region');

    if (!serviceSelect || !regionSelect) return;

    // Services
    if (state.summary && state.summary.servicesList) {
      const currentVal = state.filters.services[0] || '';
      serviceSelect.innerHTML = `<option value="">All Services (${state.summary.servicesList.length})</option>` +
        state.summary.servicesList
          .map(s => `<option value="${escapeHtml(s)}" ${s === currentVal ? 'selected' : ''}>${escapeHtml(s)}</option>`)
          .join('');
    }

    // Regions
    if (state.summary && state.summary.regionsList) {
      const currentVal = state.filters.regions[0] || '';
      regionSelect.innerHTML = `<option value="">All Regions (${state.summary.regionsList.length})</option>` +
        state.summary.regionsList
          .map(r => `<option value="${escapeHtml(r)}" ${r === currentVal ? 'selected' : ''}>${escapeHtml(r)}</option>`)
          .join('');
    }

    // Set Date range inputs
    const startInput = document.getElementById('filter-start-date');
    const endInput = document.getElementById('filter-end-date');
    if (startInput && endInput && state.filters.dateRange) {
      startInput.value = state.filters.dateRange.start || '';
      endInput.value = state.filters.dateRange.end || '';
    }
  }

  function renderExplorerTable(paginated, sym) {
    const tbody = document.getElementById('explorer-table-body');
    const paginationControls = document.getElementById('explorer-pagination-controls');
    const recordRangeLabel = document.getElementById('explorer-record-range');

    if (!tbody) return;

    if (paginated.records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-slate py-4">No matching records found for the applied filters.</td></tr>`;
      if (recordRangeLabel) recordRangeLabel.textContent = 'Showing 0 records';
      if (paginationControls) paginationControls.innerHTML = '';
      return;
    }

    if (recordRangeLabel) {
      recordRangeLabel.textContent = `Showing ${paginated.startIndex}–${paginated.endIndex} of ${paginated.totalRecords.toLocaleString()} records`;
    }

    tbody.innerHTML = paginated.records
      .map(
        r => `
      <tr>
        <td class="font-mono text-xs">${r.usage_date}</td>
        <td><strong>${escapeHtml(r.service)}</strong></td>
        <td><span class="badge badge-slate">${escapeHtml(r.region)}</span></td>
        <td class="text-xs text-slate">${escapeHtml(r.account_name || r.account_id)}</td>
        <td class="text-xs text-slate">${escapeHtml(r.tag_project || 'untagged')}</td>
        <td class="text-xs text-slate">${escapeHtml(r.tag_environment || 'unspecified')}</td>
        <td class="font-mono text-right ${r.cost_amount < 0 ? 'text-emerald' : 'text-white'}">
          ${r.cost_amount < 0 ? '-' : ''}${sym}${Math.abs(r.cost_amount).toFixed(2)}
        </td>
      </tr>
    `
      )
      .join('');

    // Render pagination buttons
    if (paginationControls) {
      let buttons = '';
      buttons += `<button class="btn btn-secondary btn-sm" ${paginated.currentPage === 1 ? 'disabled' : ''} onclick="CloudGuardApp.changePage(${paginated.currentPage - 1})">Previous</button>`;
      buttons += `<span class="px-2 text-xs text-slate">Page <strong>${paginated.currentPage}</strong> of <strong>${paginated.totalPages}</strong></span>`;
      buttons += `<button class="btn btn-secondary btn-sm" ${paginated.currentPage === paginated.totalPages ? 'disabled' : ''} onclick="CloudGuardApp.changePage(${paginated.currentPage + 1})">Next</button>`;
      paginationControls.innerHTML = buttons;
    }
  }

  /**
   * Render Anomaly Detection View
   */
  function renderAnomalies(state) {
    const anomalies = state.analysis.anomalies || [];
    const agg = state.analysis.aggregations;
    const sym = state.settings.symbol || '$';

    document.getElementById('anomalies-total-count').textContent = anomalies.length;

    // Render Anomaly Chart
    if (agg && agg.dailyTrend) {
      CloudGuardCharts.renderAnomalyChart('chart-anomaly-timeseries', agg.dailyTrend, anomalies);
    }

    const tbody = document.getElementById('anomalies-table-body');
    if (!tbody) return;

    if (anomalies.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center text-slate py-4">No statistical anomalies detected under the current sensitivity threshold.</td></tr>`;
      return;
    }

    tbody.innerHTML = anomalies
      .map(
        a => `
      <tr>
        <td class="font-mono text-xs">${a.date}</td>
        <td><strong>${escapeHtml(a.service)}</strong></td>
        <td><span class="badge badge-${a.severity.toLowerCase()}">${a.severity}</span></td>
        <td class="font-mono text-right text-rose font-bold">${sym}${a.actualCost.toFixed(2)}</td>
        <td class="font-mono text-right text-slate">${sym}${a.baselineCost.toFixed(2)}</td>
        <td class="font-mono text-right ${a.costDifference > 0 ? 'text-rose' : 'text-emerald'}">
          ${a.costDifference > 0 ? '+' : ''}${sym}${a.costDifference.toFixed(2)}
          ${a.percentageDifference !== null ? `(${a.percentageDifference > 0 ? '+' : ''}${a.percentageDifference.toFixed(1)}%)` : ''}
        </td>
        <td>
          <button class="btn btn-outline btn-xs" onclick="CloudGuardUI.showInvestigationModal('${a.id}')">
            Investigate
          </button>
        </td>
      </tr>
    `
      )
      .join('');
  }

  function showInvestigationModal(anomalyId) {
    const state = CloudGuardState.getState();
    const anomaly = (state.analysis.anomalies || []).find(a => a.id === anomalyId);
    if (!anomaly) return;

    const sym = state.settings.symbol || '$';
    const modal = document.getElementById('anomaly-investigation-modal');
    const content = document.getElementById('anomaly-modal-content');
    if (!modal || !content) return;

    content.innerHTML = `
      <div class="modal-body-details">
        <div class="flex-between items-center mb-3">
          <h4 class="font-bold text-lg text-white">${escapeHtml(anomaly.service)} — Anomaly Investigation</h4>
          <span class="badge badge-${anomaly.severity.toLowerCase()}">${anomaly.severity} Severity</span>
        </div>
        <div class="kpi-grid-mini mb-3">
          <div class="mini-stat">
            <span class="label">Date</span>
            <span class="val font-mono">${anomaly.date}</span>
          </div>
          <div class="mini-stat">
            <span class="label">Actual Spend</span>
            <span class="val font-mono text-rose">${sym}${anomaly.actualCost.toFixed(2)}</span>
          </div>
          <div class="mini-stat">
            <span class="label">Historical Baseline</span>
            <span class="val font-mono">${sym}${anomaly.baselineCost.toFixed(2)}</span>
          </div>
          <div class="mini-stat">
            <span class="label">Statistical Divergence</span>
            <span class="val font-mono ${anomaly.costDifference > 0 ? 'text-rose' : 'text-emerald'}">
              ${anomaly.costDifference > 0 ? '+' : ''}${sym}${anomaly.costDifference.toFixed(2)}
            </span>
          </div>
        </div>
        
        <div class="alert-box mb-3">
          <strong>Statistical Detection Rationale:</strong>
          <p class="text-sm mt-1 text-slate">${escapeHtml(anomaly.reason)}</p>
        </div>

        <h5 class="font-bold text-sm text-white mb-2">Recommended Investigation Checklist:</h5>
        <ul class="investigation-checklist">
          ${anomaly.investigationSteps.map(step => `<li>${escapeHtml(step)}</li>`).join('')}
        </ul>

        <div class="disclaimer-callout mt-3">
          <small class="text-slate"><strong>Note:</strong> Statistical anomaly detection flags deviation from rolling baseline patterns. It does not establish security breaches, fraud, or billing errors without verification in your cloud management console.</small>
        </div>
      </div>
    `;

    modal.classList.remove('hidden');
  }

  /**
   * Render Cost Forecast View
   */
  function renderForecast(state) {
    const fcast = state.analysis.forecast;
    const agg = state.analysis.aggregations;
    const sym = state.settings.symbol || '$';

    if (!fcast) return;

    const noticeEl = document.getElementById('forecast-sufficiency-notice');
    const contentEl = document.getElementById('forecast-content-wrapper');

    if (!fcast.isValid) {
      if (noticeEl) {
        noticeEl.style.display = 'block';
        noticeEl.innerHTML = `
          <div class="alert-box alert-warning">
            <h4 class="font-bold mb-1">⚠️ Forecasting Unavailable</h4>
            <p class="text-sm">${escapeHtml(fcast.reason)}</p>
            <p class="text-xs text-slate mt-2">${escapeHtml(fcast.limitations)}</p>
          </div>
        `;
      }
      if (contentEl) contentEl.style.display = 'none';
      return;
    }

    if (noticeEl) noticeEl.style.display = 'none';
    if (contentEl) contentEl.style.display = 'block';

    // Update KPI stats
    document.getElementById('forecast-projected-total').textContent = `${sym}${fcast.projectedTotal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    document.getElementById('forecast-projected-daily').textContent = `${sym}${fcast.projectedDailyAvg.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}/day`;
    document.getElementById('forecast-method-badge').textContent = fcast.methodUsed;
    document.getElementById('forecast-confidence-badge').textContent = fcast.confidenceLevel;
    document.getElementById('forecast-method-explanation').textContent = fcast.explanation;
    document.getElementById('forecast-limitations').textContent = fcast.limitations;

    // Render Chart
    if (agg && agg.dailyTrend) {
      CloudGuardCharts.renderForecastChart('chart-forecast-projection', agg.dailyTrend, fcast);
    }

    // Render Forecast Table
    const tbody = document.getElementById('forecast-table-body');
    if (tbody) {
      tbody.innerHTML = fcast.points
        .map(
          p => `
        <tr>
          <td class="font-mono text-xs">${p.date}</td>
          <td class="font-mono text-right text-amber font-bold">${sym}${p.cost.toFixed(2)}</td>
          <td class="font-mono text-right text-slate">${sym}${p.lowerBound.toFixed(2)}</td>
          <td class="font-mono text-right text-slate">${sym}${p.upperBound.toFixed(2)}</td>
        </tr>
      `
        )
        .join('');
    }
  }

  /**
   * Render Cost Optimization View
   */
  function renderOptimization(state) {
    const recs = state.analysis.recommendations || [];
    const sym = state.settings.symbol || '$';

    document.getElementById('recs-total-count').textContent = recs.length;
    const totalPotentialSavings = recs.reduce((sum, r) => sum + (r.estimatedSavings || 0), 0);
    document.getElementById('recs-total-savings').textContent = `${sym}${totalPotentialSavings.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const container = document.getElementById('recommendations-card-list');
    if (!container) return;

    if (recs.length === 0) {
      container.innerHTML = `
        <div class="empty-state-card text-center p-6">
          <p class="text-slate">No cost optimization opportunities identified for this dataset.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = recs
      .map(
        r => `
      <div class="rec-card mb-4">
        <div class="rec-card-header">
          <div class="flex items-center gap-2">
            <span class="badge badge-cyan">${escapeHtml(r.category)}</span>
            <span class="badge badge-slate">${escapeHtml(r.service)}</span>
          </div>
          ${
            r.estimatedSavings
              ? `<div class="savings-tag font-mono"><span class="label">Est. Potential:</span> <strong>${escapeHtml(r.estimatedSavingsLabel || `${sym}${r.estimatedSavings.toFixed(2)}`)}</strong></div>`
              : `<span class="badge badge-neutral">${escapeHtml(r.estimatedSavingsLabel || 'Auditing Review')}</span>`
          }
        </div>
        
        <h4 class="font-bold text-base text-white mt-2">${escapeHtml(r.title)}</h4>
        
        <div class="evidence-box mt-2">
          <strong>Observed Evidence:</strong> ${escapeHtml(r.evidence)}
        </div>

        <div class="rec-details-grid mt-3">
          <div>
            <span class="label-heading">Rationale</span>
            <p class="text-xs text-slate mt-1">${escapeHtml(r.reason)}</p>
          </div>
          <div>
            <span class="label-heading">Recommended Action</span>
            <p class="text-xs text-slate mt-1">${escapeHtml(r.suggestedAction)}</p>
          </div>
        </div>

        <div class="limitations-footer mt-3">
          <small class="text-slate"><strong>Confidence:</strong> ${r.confidence} | <strong>Limitations:</strong> ${escapeHtml(r.limitations)}</small>
        </div>
      </div>
    `
      )
      .join('');
  }

  /**
   * Render Reports View
   */
  function renderReports(state) {
    const agg = state.analysis.aggregations;
    const sym = state.settings.symbol || '$';
    if (!agg) return;

    document.getElementById('report-generated-timestamp').textContent = new Date().toLocaleString();
    document.getElementById('report-date-range').textContent = `${agg.dailyTrend[0]?.date || 'N/A'} to ${agg.dailyTrend[agg.dailyTrend.length - 1]?.date || 'N/A'}`;
    document.getElementById('report-total-spend').textContent = `${sym}${agg.totalSpend.toFixed(2)}`;
    document.getElementById('report-daily-avg').textContent = `${sym}${agg.avgDailyCost.toFixed(2)}`;
    document.getElementById('report-top-service').textContent = `${agg.highestService.service} (${sym}${agg.highestService.cost.toFixed(2)})`;
    document.getElementById('report-anomalies-count').textContent = (state.analysis.anomalies || []).length;
    
    const recs = state.analysis.recommendations || [];
    const totalPotentialSavings = recs.reduce((sum, r) => sum + (r.estimatedSavings || 0), 0);
    document.getElementById('report-potential-savings').textContent = `${sym}${totalPotentialSavings.toFixed(2)}`;

    // Report Service Breakdown
    const serviceTbody = document.getElementById('report-service-tbody');
    if (serviceTbody) {
      serviceTbody.innerHTML = agg.byService
        .map(
          s => `
        <tr>
          <td>${escapeHtml(s.service)}</td>
          <td class="font-mono text-right">${sym}${s.cost.toFixed(2)}</td>
          <td class="font-mono text-right">${s.percentage}%</td>
        </tr>
      `
        )
        .join('');
    }
  }

  /**
   * Render Settings View
   */
  function renderSettings(state) {
    const curSelect = document.getElementById('setting-currency');
    const sensSelect = document.getElementById('setting-sensitivity');
    const fcastSelect = document.getElementById('setting-forecast-days');
    const persistCheck = document.getElementById('setting-local-storage');

    if (curSelect) curSelect.value = state.settings.currency || 'USD';
    if (sensSelect) sensSelect.value = state.settings.sensitivity || 'balanced';
    if (fcastSelect) fcastSelect.value = state.settings.forecastDays || 14;
    if (persistCheck) persistCheck.checked = state.settings.localPersistence || false;
  }

  /**
   * Toast notification helper
   */
  function showToast(message, type = 'info', duration = 3500) {
    if (!toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${type === 'success' ? '✓' : type === 'error' ? '✕' : type === 'warning' ? '⚠' : 'ℹ'}</span>
      <span class="toast-message">${escapeHtml(message)}</span>
    `;

    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('fade-out');
      setTimeout(() => {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 300);
    }, duration);
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  return {
    init,
    switchView,
    renderCurrentView,
    showToast,
    showInvestigationModal,
    escapeHtml,
  };
})();

if (typeof window !== 'undefined') {
  window.CloudGuardUI = CloudGuardUI;
}
