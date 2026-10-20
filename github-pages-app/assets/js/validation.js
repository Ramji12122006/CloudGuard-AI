/**
 * CloudGuard AI — Validation & Schema Module
 * Module: validation.js
 */

const CloudGuardValidation = (() => {
  // Standard schema definition
  const SCHEMA_FIELDS = {
    REQUIRED: ['usage_date', 'service', 'cost_amount'],
    OPTIONAL: [
      'region',
      'account_id',
      'account_name',
      'usage_quantity',
      'unit',
      'unit_price_usd',
      'tag_project',
      'tag_environment',
    ],
  };

  /**
   * Parse a date string into standard YYYY-MM-DD format.
   * Handles ISO 8601, YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY, YYYY/MM/DD.
   */
  function parseDate(dateStr) {
    if (!dateStr || typeof dateStr !== 'string') return null;
    const trimmed = dateStr.trim();
    if (!trimmed || trimmed.toLowerCase() === 'null' || trimmed.toLowerCase() === 'undefined') {
      return null;
    }

    // Check ISO 8601 or YYYY-MM-DD
    const isoMatch = trimmed.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})/);
    if (isoMatch) {
      const year = parseInt(isoMatch[1], 10);
      const month = parseInt(isoMatch[2], 10);
      const day = parseInt(isoMatch[3], 10);
      if (isValidDate(year, month, day)) {
        return `${year}-${pad2(month)}-${pad2(day)}`;
      }
    }

    // Check MM/DD/YYYY or DD/MM/YYYY
    const slashMatch = trimmed.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})/);
    if (slashMatch) {
      const first = parseInt(slashMatch[1], 10);
      const second = parseInt(slashMatch[2], 10);
      const year = parseInt(slashMatch[3], 10);

      // Heuristic: if first > 12, it must be DD/MM/YYYY
      if (first > 12 && second <= 12) {
        if (isValidDate(year, second, first)) {
          return `${year}-${pad2(second)}-${pad2(first)}`;
        }
      } else if (second > 12 && first <= 12) {
        // Must be MM/DD/YYYY
        if (isValidDate(year, first, second)) {
          return `${year}-${pad2(first)}-${pad2(second)}`;
        }
      } else {
        // Default to MM/DD/YYYY (standard US cloud billing format, e.g. AWS/Azure)
        if (isValidDate(year, first, second)) {
          return `${year}-${pad2(first)}-${pad2(second)}`;
        }
      }
    }

    // Native JS Date fallback
    const parsed = new Date(trimmed);
    if (!isNaN(parsed.getTime())) {
      const year = parsed.getUTCFullYear();
      const month = parsed.getUTCMonth() + 1;
      const day = parsed.getUTCDate();
      if (year >= 1990 && year <= 2100) {
        return `${year}-${pad2(month)}-${pad2(day)}`;
      }
    }

    return null;
  }

  function isValidDate(year, month, day) {
    if (year < 1990 || year > 2100) return false;
    if (month < 1 || month > 12) return false;
    if (day < 1 || day > 31) return false;
    const testDate = new Date(Date.UTC(year, month - 1, day));
    return (
      testDate.getUTCFullYear() === year &&
      testDate.getUTCMonth() === month - 1 &&
      testDate.getUTCDate() === day
    );
  }

  function pad2(num) {
    return num < 10 ? `0${num}` : `${num}`;
  }

  /**
   * Parse numeric cost value.
   * Strips symbols ($ , € £ etc), handles negative amounts and accounting parentheses (100.00).
   * Returns { valid: boolean, value: number, isCredit: boolean, raw: any }
   */
  function parseNumericCost(val) {
    if (val === null || val === undefined) {
      return { valid: false, value: 0, isCredit: false, reason: 'Missing cost value' };
    }

    let str = String(val).trim();
    if (str === '' || str.toLowerCase() === 'n/a' || str.toLowerCase() === 'nan' || str.toLowerCase() === 'null') {
      return { valid: false, value: 0, isCredit: false, reason: 'Empty or N/A cost value' };
    }

    // Check accounting parenthesis for negative e.g. (150.25)
    let isNegative = false;
    if (str.startsWith('(') && str.endsWith(')')) {
      isNegative = true;
      str = str.substring(1, str.length - 1).trim();
    } else if (str.startsWith('-')) {
      isNegative = true;
      str = str.substring(1).trim();
    }

    // Remove currency signs, commas, spaces
    str = str.replace(/[$€£₹¥,\s]/g, '');

    const num = parseFloat(str);
    if (isNaN(num)) {
      return { valid: false, value: 0, isCredit: false, reason: `Non-numeric cost: "${val}"` };
    }

    const finalVal = isNegative ? -Math.abs(num) : num;
    return {
      valid: true,
      value: finalVal,
      isCredit: finalVal < 0,
      reason: null,
    };
  }

  /**
   * Check if a set of column headers fulfills the minimum schema requirements.
   */
  function validateHeaders(headers, mapping = {}) {
    const mappedFields = Object.values(mapping);
    const missing = [];

    for (const req of SCHEMA_FIELDS.REQUIRED) {
      const isDirect = headers.includes(req);
      const isMapped = mappedFields.includes(req);
      if (!isDirect && !isMapped) {
        missing.push(req);
      }
    }

    return {
      isValid: missing.length === 0,
      missingFields: missing,
      allRequired: SCHEMA_FIELDS.REQUIRED,
    };
  }

  /**
   * Check duplicate rows based on hash of key fields.
   */
  function createRowFingerprint(row) {
    return `${row.usage_date}|${row.service}|${row.cost_amount}|${row.region || ''}|${row.account_id || ''}|${row.usage_quantity || ''}`;
  }

  return {
    SCHEMA_FIELDS,
    parseDate,
    parseNumericCost,
    validateHeaders,
    createRowFingerprint,
  };
})();

if (typeof window !== 'undefined') {
  window.CloudGuardValidation = CloudGuardValidation;
}
