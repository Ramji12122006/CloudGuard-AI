/**
 * CloudGuard AI — Central State Management
 * Module: state.js
 */

const CloudGuardState = (() => {
  // Initial default state
  const state = {
    // Raw and normalized data
    rawCsvData: null,
    rawHeaders: [],
    records: [],
    warnings: [],
    summary: null,

    // Active filters
    filters: {
      dateRange: { start: null, end: null },
      services: [],
      regions: [],
      accounts: [],
      projects: [],
      environments: [],
      searchTerm: '',
      granularity: 'daily', // 'daily', 'weekly', 'monthly'
    },

    // Pagination for Cost Explorer
    pagination: {
      currentPage: 1,
      pageSize: 15,
      sortColumn: 'usage_date',
      sortDirection: 'desc',
    },

    // User settings
    settings: {
      currency: 'USD',
      symbol: '$',
      datePreset: 'all',
      sensitivity: 'balanced', // 'strict', 'balanced', 'relaxed'
      madMultiplier: 3.0,
      forecastDays: 14,
      forecastMethod: 'auto', // 'auto', 'baseline', 'trend'
      enableAnimations: true,
      localPersistence: false,
    },

    // Derived analysis results cache
    analysis: {
      aggregations: null,
      filteredRecords: [],
      anomalies: [],
      forecast: null,
      recommendations: [],
    },

    // UI state
    currentView: 'overview',
    isProcessing: false,
    pendingColumnMapping: null,
  };

  // Pub/Sub listeners
  const listeners = {};

  function subscribe(event, callback) {
    if (!listeners[event]) {
      listeners[event] = [];
    }
    listeners[event].push(callback);
    return () => {
      listeners[event] = listeners[event].filter(cb => cb !== callback);
    };
  }

  function emit(event, data) {
    if (listeners[event]) {
      listeners[event].forEach(cb => {
        try {
          cb(data);
        } catch (err) {
          console.error(`Error in listener for ${event}:`, err);
        }
      });
    }
  }

  function getState() {
    return state;
  }

  function setRecords(records, summary, warnings = []) {
    state.records = records;
    state.summary = summary;
    state.warnings = warnings;

    // Reset filters to full span of new data
    if (records.length > 0) {
      const dates = records.map(r => r.usage_date).filter(Boolean).sort();
      state.filters.dateRange = {
        start: dates[0] || null,
        end: dates[dates.length - 1] || null,
      };
      state.filters.services = [];
      state.filters.regions = [];
      state.filters.accounts = [];
      state.filters.searchTerm = '';
      state.pagination.currentPage = 1;
    } else {
      state.filters.dateRange = { start: null, end: null };
      state.analysis = {
        aggregations: null,
        filteredRecords: [],
        anomalies: [],
        forecast: null,
        recommendations: [],
      };
    }

    if (state.settings.localPersistence && records.length > 0) {
      try {
        localStorage.setItem('cloudguard_saved_records', JSON.stringify(records.slice(0, 5000)));
      } catch (e) {
        console.warn('Could not persist records to localStorage (quota exceeded or private mode).');
      }
    }

    emit('data:changed', { records, summary, warnings });
  }

  function updateFilters(newFilters) {
    state.filters = { ...state.filters, ...newFilters };
    state.pagination.currentPage = 1; // Reset to page 1 on filter change
    emit('filters:changed', state.filters);
  }

  function updatePagination(newPagination) {
    state.pagination = { ...state.pagination, ...newPagination };
    emit('pagination:changed', state.pagination);
  }

  function updateSettings(newSettings) {
    state.settings = { ...state.settings, ...newSettings };
    if (newSettings.currency) {
      const symbols = {
        USD: '$',
        EUR: '€',
        GBP: '£',
        INR: '₹',
        CAD: 'C$',
        AUD: 'A$',
        JPY: '¥',
      };
      state.settings.symbol = symbols[newSettings.currency] || '$';
    }
    if (newSettings.sensitivity) {
      const multipliers = { strict: 2.0, balanced: 3.0, relaxed: 4.5 };
      state.settings.madMultiplier = multipliers[newSettings.sensitivity] || 3.0;
    }
    try {
      localStorage.setItem('cloudguard_settings', JSON.stringify(state.settings));
    } catch (e) {
      // LocalStorage might be disabled
    }
    emit('settings:changed', state.settings);
  }

  function setAnalysisResults(analysis) {
    state.analysis = { ...state.analysis, ...analysis };
    emit('analysis:updated', state.analysis);
  }

  function clearData() {
    state.rawCsvData = null;
    state.rawHeaders = [];
    state.records = [];
    state.warnings = [];
    state.summary = null;
    state.filters.dateRange = { start: null, end: null };
    state.filters.services = [];
    state.filters.regions = [];
    state.filters.searchTerm = '';
    state.analysis = {
      aggregations: null,
      filteredRecords: [],
      anomalies: [],
      forecast: null,
      recommendations: [],
    };
    try {
      localStorage.removeItem('cloudguard_saved_records');
    } catch (e) {}
    emit('data:cleared');
  }

  function loadSavedSettings() {
    try {
      const saved = localStorage.getItem('cloudguard_settings');
      if (saved) {
        const parsed = JSON.parse(saved);
        updateSettings(parsed);
      }
    } catch (e) {}
  }

  return {
    getState,
    subscribe,
    emit,
    setRecords,
    updateFilters,
    updatePagination,
    updateSettings,
    setAnalysisResults,
    clearData,
    loadSavedSettings,
  };
})();

// Export globally for browser context
if (typeof window !== 'undefined') {
  window.CloudGuardState = CloudGuardState;
}
