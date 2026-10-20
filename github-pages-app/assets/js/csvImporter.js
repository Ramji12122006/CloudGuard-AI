/**
 * CloudGuard AI — CSV Billing Import Module
 * Module: csvImporter.js
 */

const CloudGuardImporter = (() => {
  let parsedRawData = null;
  let parsedHeaders = [];
  let suggestedMapping = {};

  /**
   * Parse a File object using Papa Parse.
   */
  function parseFile(file, onProgress, onComplete, onError) {
    if (!file) {
      if (onError) onError('No file provided.');
      return;
    }

    if (!file.name.toLowerCase().endsWith('.csv')) {
      if (onError) onError('Selected file is not a CSV. Please upload a .csv file.');
      return;
    }

    if (file.size === 0) {
      if (onError) onError('The uploaded CSV file is completely empty (0 bytes).');
      return;
    }

    if (!window.Papa) {
      if (onError) onError('Papa Parse library failed to load. Please check your internet connection.');
      return;
    }

    Papa.parse(file, {
      header: true,
      skipEmptyLines: 'greedy',
      dynamicTyping: false,
      transformHeader: header => header.trim(),
      complete: results => {
        if (!results.data || results.data.length === 0) {
          if (onError) onError('No valid data rows found in the CSV file.');
          return;
        }

        parsedRawData = results.data;
        parsedHeaders = results.meta.fields || Object.keys(results.data[0] || {});

        if (parsedHeaders.length === 0) {
          if (onError) onError('CSV header row appears to be missing or malformed.');
          return;
        }

        // Analyze detected columns
        const mappingResult = CloudGuardNormalizer.suggestMapping(parsedHeaders);
        suggestedMapping = mappingResult.mapping;

        if (onComplete) {
          onComplete({
            headers: parsedHeaders,
            rows: parsedRawData,
            suggestedMapping,
            ambiguousCostCols: mappingResult.ambiguousCostCols,
            previewRows: parsedRawData.slice(0, 15),
            totalRows: parsedRawData.length,
          });
        }
      },
      error: err => {
        if (onError) onError(`CSV parsing failed: ${err.message}`);
      },
    });
  }

  /**
   * Finalize the import using the confirmed column mapping.
   */
  function commitImport(columnMapping) {
    if (!parsedRawData || parsedRawData.length === 0) {
      throw new Error('No parsed CSV data in memory.');
    }

    // Validate headers against confirmed mapping
    const valResult = CloudGuardValidation.validateHeaders(parsedHeaders, columnMapping);
    if (!valResult.isValid) {
      throw new Error(`Missing required fields: ${valResult.missingFields.join(', ')}`);
    }

    // Normalize
    const { records, summary, warnings } = CloudGuardNormalizer.normalizeRecords(parsedRawData, columnMapping);

    if (records.length === 0) {
      throw new Error('All rows were rejected due to invalid dates, services, or cost values. Please review validation warnings.');
    }

    // Save to global state
    CloudGuardState.setRecords(records, summary, warnings);

    return { records, summary, warnings };
  }

  /**
   * Load the bundled sample CSV file via fetch.
   */
  async function loadSampleBillingData() {
    try {
      const response = await fetch('sample-data/sample-billing.csv');
      if (!response.ok) {
        throw new Error(`Failed to fetch sample billing data (status ${response.status})`);
      }
      const csvText = await response.text();

      return new Promise((resolve, reject) => {
        Papa.parse(csvText, {
          header: true,
          skipEmptyLines: 'greedy',
          complete: results => {
            parsedRawData = results.data;
            parsedHeaders = results.meta.fields || Object.keys(results.data[0] || {});
            const { mapping } = CloudGuardNormalizer.suggestMapping(parsedHeaders);
            const { records, summary, warnings } = CloudGuardNormalizer.normalizeRecords(parsedRawData, mapping);
            CloudGuardState.setRecords(records, summary, warnings);
            resolve({ records, summary, warnings });
          },
          error: err => reject(err),
        });
      });
    } catch (err) {
      console.error('Error loading sample billing data:', err);
      throw err;
    }
  }

  /**
   * Download a clean CSV template matching the standard schema.
   */
  function downloadSampleTemplate() {
    const templateContent = [
      'usage_date,service,cost_amount,region,account_id,account_name,usage_quantity,unit,unit_price_usd,tag_project,tag_environment',
      '2026-10-01,Amazon EC2,125.50,us-east-1,112233445566,Production-Account,1255,Hrs,0.10,api-gateway,production',
      '2026-10-01,Amazon S3,42.80,us-east-1,112233445566,Production-Account,1860,GB-Mo,0.023,data-lake,production',
      '2026-10-01,Amazon RDS,88.40,us-east-1,112233445566,Production-Account,720,Hrs,0.1228,api-gateway,production',
      '2026-10-01,AWS Promotional Credit,-50.00,us-east-1,112233445566,Production-Account,1,Count,50.00,enterprise-billing,production',
    ].join('\r\n');

    CloudGuardReports.downloadBlob(templateContent, 'text/csv;charset=utf-8;', 'cloudguard-template.csv');
  }

  function getParsedData() {
    return {
      rawData: parsedRawData,
      headers: parsedHeaders,
      suggestedMapping,
    };
  }

  return {
    parseFile,
    commitImport,
    loadSampleBillingData,
    downloadSampleTemplate,
    getParsedData,
  };
})();

if (typeof window !== 'undefined') {
  window.CloudGuardImporter = CloudGuardImporter;
}
