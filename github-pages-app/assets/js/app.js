/**
 * CloudGuard AI — Main Application Orchestrator
 * Module: app.js
 */

const CloudGuardApp = (() => {
  let pendingMappingHeaders = [];
  let pendingRawRows = [];
  let currentSuggestedMapping = {};

  function init() {
    // 1. Initialize State and Load Saved Settings
    CloudGuardState.loadSavedSettings();

    // 2. Initialize UI Controller
    CloudGuardUI.init();

    // 3. Register Global Event Subscriptions
    registerStateSubscriptions();

    // 4. Bind UI Event Listeners
    bindUploadEvents();
    bindFilterEvents();
    bindExplorerControls();
    bindSettingsEvents();
    bindReportEvents();
    bindModalEvents();

    // 5. Check URL Hash Route or Default to Overview
    const initialRoute = window.location.hash.replace('#', '') || 'overview';
    window.addEventListener('hashchange', () => {
      const route = window.location.hash.replace('#', '') || 'overview';
      CloudGuardUI.switchView(route);
    });
    CloudGuardUI.switchView(initialRoute);

    // 6. Check for previously persisted session data if opted-in
    checkPersistedSession();
  }

  function registerStateSubscriptions() {
    CloudGuardState.subscribe('data:changed', ({ records }) => {
      runAnalysisPipeline(records);
      CloudGuardUI.renderCurrentView(CloudGuardState.getState().currentView);
    });

    CloudGuardState.subscribe('filters:changed', () => {
      const state = CloudGuardState.getState();
      runAnalysisPipeline(state.records);
      CloudGuardUI.renderCurrentView(state.currentView);
    });

    CloudGuardState.subscribe('pagination:changed', () => {
      const state = CloudGuardState.getState();
      if (state.currentView === 'explorer') {
        CloudGuardUI.renderCurrentView('explorer');
      }
    });

    CloudGuardState.subscribe('settings:changed', () => {
      const state = CloudGuardState.getState();
      runAnalysisPipeline(state.records);
      CloudGuardUI.renderCurrentView(state.currentView);
    });

    CloudGuardState.subscribe('data:cleared', () => {
      CloudGuardUI.renderCurrentView(CloudGuardState.getState().currentView);
      CloudGuardUI.showToast('All billing data cleared successfully.', 'info');
    });
  }

  /**
   * Complete Analytical Calculation Pipeline
   * Runs client-side calculations reactively whenever data, filters, or settings change.
   */
  function runAnalysisPipeline(records) {
    if (!records || records.length === 0) {
      CloudGuardState.setAnalysisResults({
        aggregations: null,
        filteredRecords: [],
        anomalies: [],
        forecast: null,
        recommendations: [],
      });
      return;
    }

    const state = CloudGuardState.getState();

    // 1. Filter Records
    const filteredRecords = CloudGuardCostEngine.filterRecords(records, state.filters);

    // 2. Compute Aggregations
    const aggregations = CloudGuardCostEngine.computeAggregations(filteredRecords, records);

    // 3. Detect Anomalies (uses all records to preserve historical baseline accuracy)
    const anomalies = CloudGuardAnomalyDetector.detectAnomalies(records, {
      sensitivity: state.settings.sensitivity,
      madMultiplier: state.settings.madMultiplier,
    });

    // 4. Generate Forecast
    const forecast = CloudGuardForecaster.generateForecast(aggregations.dailyTrend, {
      days: state.settings.forecastDays,
      method: state.settings.forecastMethod,
    });

    // 5. Generate Cost Optimization Recommendations
    const recommendations = CloudGuardRecommendations.generateRecommendations(filteredRecords, aggregations);

    // Update global state analysis results
    CloudGuardState.setAnalysisResults({
      aggregations,
      filteredRecords,
      anomalies,
      forecast,
      recommendations,
    });
  }

  /**
   * Bind CSV Upload & Drag-and-Drop Handlers
   */
  function bindUploadEvents() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('csv-file-input');
    const sampleBtn = document.getElementById('btn-load-sample');
    const headerSampleBtn = document.getElementById('btn-header-sample');
    const templateBtn = document.getElementById('btn-download-template');
    const clearBtn = document.getElementById('btn-clear-data');

    if (dropZone && fileInput) {
      dropZone.addEventListener('click', () => fileInput.click());

      dropZone.addEventListener('dragover', e => {
        e.preventDefault();
        dropZone.classList.add('drag-active');
      });

      dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-active');
      });

      dropZone.addEventListener('drop', e => {
        e.preventDefault();
        dropZone.classList.remove('drag-active');
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          processSelectedFile(e.dataTransfer.files[0]);
        }
      });

      fileInput.addEventListener('change', e => {
        if (e.target.files && e.target.files.length > 0) {
          processSelectedFile(e.target.files[0]);
          e.target.value = ''; // Reset input
        }
      });
    }

    if (sampleBtn) {
      sampleBtn.addEventListener('click', loadSampleData);
    }
    if (headerSampleBtn) {
      headerSampleBtn.addEventListener('click', loadSampleData);
    }

    if (templateBtn) {
      templateBtn.addEventListener('click', () => {
        CloudGuardImporter.downloadSampleTemplate();
        CloudGuardUI.showToast('Downloaded sample CSV billing template.', 'success');
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to clear all imported data?')) {
          CloudGuardState.clearData();
        }
      });
    }
  }

  function processSelectedFile(file) {
    CloudGuardUI.showToast(`Reading ${file.name}...`, 'info');

    CloudGuardImporter.parseFile(
      file,
      pct => {},
      parsed => {
        pendingMappingHeaders = parsed.headers;
        pendingRawRows = parsed.rows;
        currentSuggestedMapping = parsed.suggestedMapping;

        // Open Column Mapping Modal for user verification
        openColumnMappingModal(parsed);
      },
      err => {
        CloudGuardUI.showToast(err, 'error', 5000);
      }
    );
  }

  async function loadSampleData() {
    try {
      CloudGuardUI.showToast('Loading bundled 30-day cloud billing dataset...', 'info');
      const { summary } = await CloudGuardImporter.loadSampleBillingData();
      CloudGuardUI.showToast(`Loaded ${summary.validRecords} sample records ($${summary.netSpend.toFixed(2)} total spend).`, 'success');
      CloudGuardUI.switchView('overview');
    } catch (err) {
      CloudGuardUI.showToast(`Failed to load sample data: ${err.message}`, 'error');
    }
  }

  /**
   * Column Mapping Modal Handling
   */
  function openColumnMappingModal(parsed) {
    const modal = document.getElementById('column-mapping-modal');
    const mappingTableBody = document.getElementById('mapping-table-body');
    const previewTableHead = document.getElementById('mapping-preview-head');
    const previewTableBody = document.getElementById('mapping-preview-body');
    const ambiguityNotice = document.getElementById('mapping-ambiguity-notice');

    if (!modal) return;

    // Show Ambiguity Warning if multiple possible cost fields were detected
    if (parsed.ambiguousCostCols && parsed.ambiguousCostCols.length > 1) {
      ambiguityNotice.classList.remove('hidden');
      ambiguityNotice.innerHTML = `
        <strong>⚠️ Multiple Cost Columns Detected:</strong> Found <code>${parsed.ambiguousCostCols.join(', ')}</code>.
        Please confirm which column represents the true net billed cost.
      `;
    } else {
      ambiguityNotice.classList.add('hidden');
    }

    // Build Mapping Selectors Table
    const stdFields = [
      { id: 'usage_date', label: 'usage_date (Required: Date)' },
      { id: 'service', label: 'service (Required: Service Name)' },
      { id: 'cost_amount', label: 'cost_amount (Required: Cost in USD)' },
      { id: 'region', label: 'region (Optional)' },
      { id: 'account_id', label: 'account_id (Optional)' },
      { id: 'account_name', label: 'account_name (Optional)' },
      { id: 'usage_quantity', label: 'usage_quantity (Optional)' },
      { id: 'unit', label: 'unit (Optional)' },
      { id: 'unit_price_usd', label: 'unit_price_usd (Optional)' },
      { id: 'tag_project', label: 'tag_project (Optional)' },
      { id: 'tag_environment', label: 'tag_environment (Optional)' },
    ];

    mappingTableBody.innerHTML = stdFields
      .map(std => {
        // Find best match in parsed headers
        let selectedHeader = '';
        Object.entries(parsed.suggestedMapping).forEach(([raw, mappedStd]) => {
          if (mappedStd === std.id) selectedHeader = raw;
        });

        const optionsHtml = `<option value="">-- Ignore Field --</option>` +
          parsed.headers
            .map(
              h => `<option value="${CloudGuardUI.escapeHtml(h)}" ${h === selectedHeader ? 'selected' : ''}>${CloudGuardUI.escapeHtml(h)}</option>`
            )
            .join('');

        return `
        <tr>
          <td>
            <strong>${std.id}</strong>
            ${std.id.includes('usage_date') || std.id.includes('service') || std.id.includes('cost_amount') ? '<span class="text-rose font-bold">*</span>' : ''}
            <div class="text-xs text-slate">${std.label}</div>
          </td>
          <td>
            <select class="form-select mapping-select" data-std-field="${std.id}">
              ${optionsHtml}
            </select>
          </td>
        </tr>
      `;
      })
      .join('');

    // Build Preview Table
    previewTableHead.innerHTML = `<tr>${parsed.headers.map(h => `<th>${CloudGuardUI.escapeHtml(h)}</th>`).join('')}</tr>`;
    previewTableBody.innerHTML = parsed.previewRows
      .slice(0, 10)
      .map(row => `<tr>${parsed.headers.map(h => `<td>${CloudGuardUI.escapeHtml(row[h] || '')}</td>`).join('')}</tr>`)
      .join('');

    modal.classList.remove('hidden');
  }

  function bindModalEvents() {
    const confirmBtn = document.getElementById('btn-confirm-mapping');
    const cancelBtn = document.getElementById('btn-cancel-mapping');
    const closeAnomBtn = document.getElementById('btn-close-anomaly-modal');

    if (confirmBtn) {
      confirmBtn.addEventListener('click', () => {
        // Collect mapping choices
        const selects = document.querySelectorAll('.mapping-select');
        const confirmedMapping = {};

        selects.forEach(sel => {
          const stdField = sel.getAttribute('data-std-field');
          const chosenRaw = sel.value;
          if (chosenRaw) {
            confirmedMapping[chosenRaw] = stdField;
          }
        });

        try {
          const { summary, warnings } = CloudGuardImporter.commitImport(confirmedMapping);
          document.getElementById('column-mapping-modal').classList.add('hidden');
          CloudGuardUI.showToast(`Successfully imported ${summary.validRecords} billing records ($${summary.netSpend.toFixed(2)} net spend).`, 'success');
          
          if (warnings.length > 0) {
            CloudGuardUI.showToast(`Imported with ${warnings.length} warning(s). Check Settings or logs for details.`, 'warning', 4500);
          }

          CloudGuardUI.switchView('overview');
        } catch (err) {
          alert(`Validation Error: ${err.message}`);
        }
      });
    }

    if (cancelBtn) {
      cancelBtn.addEventListener('click', () => {
        document.getElementById('column-mapping-modal').classList.add('hidden');
      });
    }

    if (closeAnomBtn) {
      closeAnomBtn.addEventListener('click', () => {
        document.getElementById('anomaly-investigation-modal').classList.add('hidden');
      });
    }

    // Close modals on escape key
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') {
        const mappingModal = document.getElementById('column-mapping-modal');
        const anomModal = document.getElementById('anomaly-investigation-modal');
        if (mappingModal) mappingModal.classList.add('hidden');
        if (anomModal) anomModal.classList.add('hidden');
      }
    });
  }

  /**
   * Filter controls
   */
  function bindFilterEvents() {
    const startInput = document.getElementById('filter-start-date');
    const endInput = document.getElementById('filter-end-date');
    const serviceSelect = document.getElementById('filter-service');
    const regionSelect = document.getElementById('filter-region');
    const searchInput = document.getElementById('filter-search');
    const resetBtn = document.getElementById('filter-reset-btn');

    function applyFilters() {
      const filters = {
        dateRange: {
          start: startInput ? startInput.value || null : null,
          end: endInput ? endInput.value || null : null,
        },
        services: serviceSelect && serviceSelect.value ? [serviceSelect.value] : [],
        regions: regionSelect && regionSelect.value ? [regionSelect.value] : [],
        searchTerm: searchInput ? searchInput.value : '',
      };
      CloudGuardState.updateFilters(filters);
    }

    if (startInput) startInput.addEventListener('change', applyFilters);
    if (endInput) endInput.addEventListener('change', applyFilters);
    if (serviceSelect) serviceSelect.addEventListener('change', applyFilters);
    if (regionSelect) regionSelect.addEventListener('change', applyFilters);

    let searchTimeout = null;
    if (searchInput) {
      searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(applyFilters, 300);
      });
    }

    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        const state = CloudGuardState.getState();
        if (state.records.length > 0) {
          const dates = state.records.map(r => r.usage_date).sort();
          if (startInput) startInput.value = dates[0] || '';
          if (endInput) endInput.value = dates[dates.length - 1] || '';
          if (serviceSelect) serviceSelect.value = '';
          if (regionSelect) regionSelect.value = '';
          if (searchInput) searchInput.value = '';

          CloudGuardState.updateFilters({
            dateRange: { start: dates[0] || null, end: dates[dates.length - 1] || null },
            services: [],
            regions: [],
            searchTerm: '',
          });
        }
      });
    }
  }

  /**
   * Cost Explorer Controls
   */
  function bindExplorerControls() {
    const granularityBtns = document.querySelectorAll('.btn-granularity');
    granularityBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        granularityBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const g = btn.getAttribute('data-granularity');
        CloudGuardState.getState().filters.granularity = g;
        CloudGuardUI.renderCurrentView('explorer');
      });
    });

    const chartTypeSelect = document.getElementById('explorer-chart-type');
    if (chartTypeSelect) {
      chartTypeSelect.addEventListener('change', () => {
        CloudGuardUI.renderCurrentView('explorer');
      });
    }

    // Sortable table headers
    const sortHeaders = document.querySelectorAll('.sortable-th');
    sortHeaders.forEach(th => {
      th.addEventListener('click', () => {
        const col = th.getAttribute('data-col');
        const curPagination = CloudGuardState.getState().pagination;
        let newDir = 'asc';
        if (curPagination.sortColumn === col && curPagination.sortDirection === 'asc') {
          newDir = 'desc';
        }
        CloudGuardState.updatePagination({ sortColumn: col, sortDirection: newDir });
      });
    });
  }

  function changePage(newPage) {
    CloudGuardState.updatePagination({ currentPage: newPage });
  }

  /**
   * Settings events
   */
  function bindSettingsEvents() {
    const curSelect = document.getElementById('setting-currency');
    const sensSelect = document.getElementById('setting-sensitivity');
    const fcastSelect = document.getElementById('setting-forecast-days');
    const persistCheck = document.getElementById('setting-local-storage');
    const resetAppBtn = document.getElementById('btn-reset-app');

    if (curSelect) {
      curSelect.addEventListener('change', () => {
        CloudGuardState.updateSettings({ currency: curSelect.value });
        CloudGuardUI.showToast(`Currency updated to ${curSelect.value}`, 'info');
      });
    }

    if (sensSelect) {
      sensSelect.addEventListener('change', () => {
        CloudGuardState.updateSettings({ sensitivity: sensSelect.value });
        CloudGuardUI.showToast(`Anomaly detection sensitivity set to ${sensSelect.value}`, 'info');
      });
    }

    if (fcastSelect) {
      fcastSelect.addEventListener('change', () => {
        CloudGuardState.updateSettings({ forecastDays: parseInt(fcastSelect.value, 10) });
        CloudGuardUI.showToast(`Forecast horizon set to ${fcastSelect.value} days`, 'info');
      });
    }

    if (persistCheck) {
      persistCheck.addEventListener('change', () => {
        const checked = persistCheck.checked;
        CloudGuardState.updateSettings({ localPersistence: checked });
        if (!checked) {
          localStorage.removeItem('cloudguard_saved_records');
          CloudGuardUI.showToast('Local browser caching disabled.', 'info');
        } else {
          CloudGuardUI.showToast('Local browser caching enabled for active session.', 'info');
        }
      });
    }

    if (resetAppBtn) {
      resetAppBtn.addEventListener('click', () => {
        if (confirm('Reset application to original defaults and clear all data?')) {
          localStorage.clear();
          CloudGuardState.clearData();
          CloudGuardState.updateSettings({
            currency: 'USD',
            sensitivity: 'balanced',
            forecastDays: 14,
            localPersistence: false,
          });
          CloudGuardUI.showToast('Application reset to factory defaults.', 'success');
        }
      });
    }
  }

  /**
   * Report events
   */
  function bindReportEvents() {
    const exportCsvBtn = document.getElementById('btn-export-csv');
    const exportJsonBtn = document.getElementById('btn-export-json');
    const printBtn = document.getElementById('btn-print-report');

    if (exportCsvBtn) {
      exportCsvBtn.addEventListener('click', () => {
        const state = CloudGuardState.getState();
        const recs = state.analysis.filteredRecords.length > 0 ? state.analysis.filteredRecords : state.records;
        CloudGuardReports.exportRecordsToCsv(recs, `cloudguard-billing-export-${new Date().toISOString().substring(0, 10)}.csv`);
        CloudGuardUI.showToast('Exported billing CSV file.', 'success');
      });
    }

    if (exportJsonBtn) {
      exportJsonBtn.addEventListener('click', () => {
        const state = CloudGuardState.getState();
        CloudGuardReports.exportAnalysisJson(state, `cloudguard-analysis-${new Date().toISOString().substring(0, 10)}.json`);
        CloudGuardUI.showToast('Exported analysis JSON report.', 'success');
      });
    }

    if (printBtn) {
      printBtn.addEventListener('click', () => {
        CloudGuardReports.printReport();
      });
    }
  }

  function checkPersistedSession() {
    const state = CloudGuardState.getState();
    if (state.settings.localPersistence) {
      try {
        const saved = localStorage.getItem('cloudguard_saved_records');
        if (saved) {
          const records = JSON.parse(saved);
          if (records && records.length > 0) {
            const { summary } = CloudGuardNormalizer.normalizeRecords(records, {
              usage_date: 'usage_date',
              service: 'service',
              cost_amount: 'cost_amount',
              region: 'region',
              account_id: 'account_id',
              account_name: 'account_name',
              tag_project: 'tag_project',
              tag_environment: 'tag_environment',
            });
            CloudGuardState.setRecords(records, summary);
            CloudGuardUI.showToast(`Restored ${records.length} records from local session.`, 'info');
          }
        }
      } catch (e) {
        console.warn('Could not restore saved records:', e);
      }
    }
  }

  return {
    init,
    changePage,
    loadSampleData,
  };
})();

// Initialize on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
  CloudGuardApp.init();
});

if (typeof window !== 'undefined') {
  window.CloudGuardApp = CloudGuardApp;
}
