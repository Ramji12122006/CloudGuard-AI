/**
 * CloudGuard AI — Data Normalizer Module
 * Module: dataNormalizer.js
 */

const CloudGuardNormalizer = (() => {
  // Alias mappings for standard schema fields
  const ALIAS_MAP = {
    usage_date: [
      'usage_date',
      'date',
      'billing_date',
      'usage_start_date',
      'usagestartdate',
      'start_date',
      'usage_end_date',
      'timestamp',
      'day',
      'billing_period_start_date',
    ],
    service: [
      'service',
      'service_name',
      'product_name',
      'product_service',
      'servicename',
      'productname',
      'productcode',
      'line_item_product_code',
      'consumed_service',
      'meter_category',
    ],
    cost_amount: [
      'cost_amount',
      'cost_usd',
      'cost',
      'unblended_cost',
      'line_item_unblended_cost',
      'amount',
      'total_cost',
      'billed_cost',
      'costamount',
      'costinbillingcurrency',
      'pretax_cost',
    ],
    region: [
      'region',
      'availability_zone',
      'product_region',
      'item_region',
      'location',
      'resourcelocation',
      'zone',
    ],
    account_id: [
      'account_id',
      'linked_account_id',
      'line_item_usage_account_id',
      'account',
      'subscription_id',
      'project_id',
      'accountid',
    ],
    account_name: [
      'account_name',
      'linked_account_name',
      'subscription_name',
      'project_name',
      'accountname',
    ],
    usage_quantity: [
      'usage_quantity',
      'quantity',
      'line_item_usage_amount',
      'usage_amount',
      'consumed_quantity',
      'usagequantity',
    ],
    unit: [
      'unit',
      'pricing_unit',
      'usage_unit',
      'unit_of_measure',
    ],
    unit_price_usd: [
      'unit_price_usd',
      'unit_price',
      'rate',
      'pricing_rate',
      'unit_rate',
    ],
    tag_project: [
      'tag_project',
      'project',
      'tag_name_project',
      'resource_tags_user_project',
      'tag_user_project',
    ],
    tag_environment: [
      'tag_environment',
      'environment',
      'env',
      'tag_name_environment',
      'tag_name_env',
      'resource_tags_user_environment',
      'tag_user_environment',
    ],
  };

  /**
   * Suggest automated mapping from raw CSV headers to standard schema fields.
   * Returns { mapping: { [rawHeader]: standardField }, ambiguousCostCols: string[] }
   */
  function suggestMapping(rawHeaders) {
    const mapping = {};
    const lowerHeaders = rawHeaders.map(h => ({
      raw: h,
      clean: h.toLowerCase().trim().replace(/[\s\-_.]+/g, '_'),
    }));

    // Find all possible matches for cost_amount
    const potentialCostMatches = [];
    const costAliases = ALIAS_MAP.cost_amount.map(a => a.toLowerCase().replace(/[\s\-_.]+/g, '_'));

    lowerHeaders.forEach(header => {
      if (costAliases.includes(header.clean)) {
        potentialCostMatches.push(header.raw);
      }
    });

    // Check ambiguous cost fields: if multiple candidates found, note them
    const ambiguousCostCols = potentialCostMatches.length > 1 ? potentialCostMatches : [];

    // Map each standard field
    Object.keys(ALIAS_MAP).forEach(stdField => {
      const aliases = ALIAS_MAP[stdField].map(a => a.toLowerCase().replace(/[\s\-_.]+/g, '_'));
      for (const h of lowerHeaders) {
        // Direct match
        if (aliases.includes(h.clean) && !mapping[h.raw]) {
          mapping[h.raw] = stdField;
          break;
        }
      }
    });

    return {
      mapping,
      ambiguousCostCols,
    };
  }

  /**
   * Normalize an array of raw parsed rows using the given column mapping.
   * Produces clean records, warnings, and comprehensive summary.
   */
  function normalizeRecords(rawRows, columnMapping) {
    const records = [];
    const warnings = [];
    const fingerprints = new Set();
    let duplicateCount = 0;
    let skippedCount = 0;
    let totalGrossSpend = 0;
    let totalCredits = 0;
    const servicesSet = new Set();
    const regionsSet = new Set();
    const accountsSet = new Set();

    // Invert mapping for quick lookup: standardField -> rawHeader
    const stdToRaw = {};
    Object.entries(columnMapping).forEach(([rawCol, stdField]) => {
      if (stdField) {
        stdToRaw[stdField] = rawCol;
      }
    });

    rawRows.forEach((row, index) => {
      const rowIndex = index + 1;

      // Extract required fields
      const rawDate = row[stdToRaw['usage_date']];
      const rawService = row[stdToRaw['service']];
      const rawCost = row[stdToRaw['cost_amount']];

      // Validate Date
      const parsedDate = CloudGuardValidation.parseDate(rawDate);
      if (!parsedDate) {
        warnings.push({
          row: rowIndex,
          type: 'INVALID_DATE',
          message: `Row ${rowIndex}: Skipped due to invalid or missing date ("${rawDate || ''}").`,
        });
        skippedCount++;
        return;
      }

      // Validate Service
      const cleanService = (rawService || '').trim();
      if (!cleanService) {
        warnings.push({
          row: rowIndex,
          type: 'MISSING_SERVICE',
          message: `Row ${rowIndex}: Skipped due to missing service name.`,
        });
        skippedCount++;
        return;
      }

      // Validate Cost
      const costResult = CloudGuardValidation.parseNumericCost(rawCost);
      if (!costResult.valid) {
        warnings.push({
          row: rowIndex,
          type: 'INVALID_COST',
          message: `Row ${rowIndex}: Skipped due to invalid cost: ${costResult.reason}.`,
        });
        skippedCount++;
        return;
      }

      // Extract optional fields
      const region = (row[stdToRaw['region']] || 'global').trim() || 'global';
      const accountId = (row[stdToRaw['account_id']] || '').trim() || 'Default-Account';
      const accountName = (row[stdToRaw['account_name']] || '').trim() || accountId;
      const usageQty = parseFloat(row[stdToRaw['usage_quantity']]) || 0;
      const unit = (row[stdToRaw['unit']] || '').trim();
      const unitPrice = parseFloat(row[stdToRaw['unit_price_usd']]) || 0;
      const tagProject = (row[stdToRaw['tag_project']] || '').trim() || 'untagged';
      const tagEnvironment = (row[stdToRaw['tag_environment']] || '').trim() || 'unspecified';

      const record = {
        id: `rec_${rowIndex}_${Date.now()}`,
        rowNumber: rowIndex,
        usage_date: parsedDate,
        service: cleanService,
        cost_amount: costResult.value,
        is_credit: costResult.isCredit,
        region,
        account_id: accountId,
        account_name: accountName,
        usage_quantity: usageQty,
        unit,
        unit_price_usd: unitPrice,
        tag_project: tagProject,
        tag_environment: tagEnvironment,
      };

      // Check duplicate
      const fp = CloudGuardValidation.createRowFingerprint(record);
      if (fingerprints.has(fp)) {
        duplicateCount++;
        // We still keep the row or skip? In financial auditing, duplicates can represent multiple items,
        // but identical entries within the same batch should be noted.
        warnings.push({
          row: rowIndex,
          type: 'DUPLICATE_ROW',
          message: `Row ${rowIndex}: Identical record detected (${record.usage_date}, ${record.service}, ${record.cost_amount}).`,
        });
      } else {
        fingerprints.add(fp);
      }

      // Accumulate totals
      if (record.cost_amount < 0) {
        totalCredits += Math.abs(record.cost_amount);
      } else {
        totalGrossSpend += record.cost_amount;
      }

      servicesSet.add(cleanService);
      regionsSet.add(region);
      accountsSet.add(accountId);

      records.push(record);
    });

    // Sort records chronologically
    records.sort((a, b) => (a.usage_date > b.usage_date ? 1 : -1));

    const netSpend = totalGrossSpend - totalCredits;
    const dates = records.map(r => r.usage_date);
    const minDate = dates[0] || null;
    const maxDate = dates[dates.length - 1] || null;

    // Distinct days
    const uniqueDays = new Set(dates).size;

    const summary = {
      totalRowsRead: rawRows.length,
      validRecords: records.length,
      skippedRows: skippedCount,
      duplicateRows: duplicateCount,
      totalGrossSpend,
      totalCredits,
      netSpend,
      dateRange: { min: minDate, max: maxDate, uniqueDays },
      serviceCount: servicesSet.size,
      servicesList: Array.from(servicesSet).sort(),
      regionCount: regionsSet.size,
      regionsList: Array.from(regionsSet).sort(),
      accountCount: accountsSet.size,
      accountsList: Array.from(accountsSet).sort(),
    };

    return {
      records,
      summary,
      warnings,
    };
  }

  return {
    ALIAS_MAP,
    suggestMapping,
    normalizeRecords,
  };
})();

if (typeof window !== 'undefined') {
  window.CloudGuardNormalizer = CloudGuardNormalizer;
}
