/**
 * CloudGuard AI — Report Generation & Export Module
 * Module: reports.js
 */

const CloudGuardReports = (() => {
  /**
   * Export an array of billing records as CSV file.
   */
  function exportRecordsToCsv(records, filename = 'cloudguard-billing-export.csv') {
    if (!records || records.length === 0) {
      alert('No records available to export.');
      return;
    }

    const headers = [
      'usage_date',
      'service',
      'cost_amount',
      'region',
      'account_id',
      'account_name',
      'usage_quantity',
      'unit',
      'unit_price_usd',
      'tag_project',
      'tag_environment',
    ];

    const csvRows = [];
    csvRows.push(headers.join(','));

    records.forEach(r => {
      const row = headers.map(h => {
        let val = r[h] !== undefined && r[h] !== null ? String(r[h]) : '';
        // Escape quotes and wrap in quotes if commas/quotes exist
        if (val.includes(',') || val.includes('"') || val.includes('\n')) {
          val = `"${val.replace(/"/g, '""')}"`;
        }
        return val;
      });
      csvRows.push(row.join(','));
    });

    const csvContent = csvRows.join('\r\n');
    downloadBlob(csvContent, 'text/csv;charset=utf-8;', filename);
  }

  /**
   * Export structured analysis summary as JSON.
   */
  function exportAnalysisJson(state, filename = 'cloudguard-analysis-summary.json') {
    const { summary, filters, settings, analysis } = state;

    const exportPayload = {
      generator: 'CloudGuard AI (Browser Edition)',
      version: '2.0.0',
      exportedAt: new Date().toISOString(),
      activeFilters: filters,
      settings: {
        currency: settings.currency,
        sensitivity: settings.sensitivity,
        forecastDays: settings.forecastDays,
      },
      billingSummary: {
        totalSpend: analysis.aggregations ? analysis.aggregations.totalSpend : 0,
        grossSpend: analysis.aggregations ? analysis.aggregations.grossSpend : 0,
        totalCredits: analysis.aggregations ? analysis.aggregations.totalCredits : 0,
        avgDailyCost: analysis.aggregations ? analysis.aggregations.avgDailyCost : 0,
        uniqueBillingDays: analysis.aggregations ? analysis.aggregations.uniqueDays : 0,
        topService: analysis.aggregations ? analysis.aggregations.highestService : null,
      },
      serviceBreakdown: analysis.aggregations ? analysis.aggregations.byService : [],
      regionBreakdown: analysis.aggregations ? analysis.aggregations.byRegion : [],
      periodComparison: analysis.aggregations ? analysis.aggregations.periodComparison : null,
      detectedAnomalies: analysis.anomalies || [],
      costForecast: analysis.forecast || null,
      costRecommendations: analysis.recommendations || [],
    };

    const jsonStr = JSON.stringify(exportPayload, null, 2);
    downloadBlob(jsonStr, 'application/json;charset=utf-8;', filename);
  }

  /**
   * Helper to trigger a browser file download.
   */
  function downloadBlob(content, mimeType, filename) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  /**
   * Trigger print dialog for the report page.
   */
  function printReport() {
    window.print();
  }

  return {
    exportRecordsToCsv,
    exportAnalysisJson,
    downloadBlob,
    printReport,
  };
})();

if (typeof window !== 'undefined') {
  window.CloudGuardReports = CloudGuardReports;
}
