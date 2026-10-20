/**
 * CloudGuard AI — Client-Side Automated Test Suite
 * Module: tests/test-suite.js
 */

const CloudGuardTestSuite = (() => {
  const tests = [];
  let passedCount = 0;
  let failedCount = 0;
  const testResults = [];

  function test(name, fn) {
    tests.push({ name, fn });
  }

  function assert(condition, message) {
    if (!condition) {
      throw new Error(message || 'Assertion failed');
    }
  }

  function assertEqual(actual, expected, message) {
    if (actual !== expected) {
      throw new Error(`${message || 'Assertion failed'}: expected "${expected}", received "${actual}"`);
    }
  }

  function assertCloseTo(actual, expected, epsilon = 0.05, message) {
    if (Math.abs(actual - expected) > epsilon) {
      throw new Error(`${message || 'Assertion failed'}: expected ~${expected}, received ${actual} (diff ${Math.abs(actual - expected)})`);
    }
  }

  // --------------------------------------------------------------------------
  // TEST DEFINITIONS
  // --------------------------------------------------------------------------

  // Group 1: Date Parsing Tests
  test('Date Parser - ISO 8601 (YYYY-MM-DD)', () => {
    const res = CloudGuardValidation.parseDate('2026-09-15');
    assertEqual(res, '2026-09-15', 'ISO format parsing');
  });

  test('Date Parser - US Format (MM/DD/YYYY)', () => {
    const res = CloudGuardValidation.parseDate('09/15/2026');
    assertEqual(res, '2026-09-15', 'US slash format parsing');
  });

  test('Date Parser - European Format (DD/MM/YYYY)', () => {
    const res = CloudGuardValidation.parseDate('25/09/2026');
    assertEqual(res, '2026-09-25', 'EU format parsing');
  });

  test('Date Parser - Full ISO timestamp', () => {
    const res = CloudGuardValidation.parseDate('2026-09-15T14:30:00Z');
    assertEqual(res, '2026-09-15', 'Timestamp parsing');
  });

  test('Date Parser - Invalid inputs', () => {
    assertEqual(CloudGuardValidation.parseDate(''), null, 'Empty string');
    assertEqual(CloudGuardValidation.parseDate('invalid-date'), null, 'Garbage text');
    assertEqual(CloudGuardValidation.parseDate(null), null, 'Null');
    assertEqual(CloudGuardValidation.parseDate('2026-02-31'), null, 'Impossible calendar date');
  });

  // Group 2: Numeric & Currency Parsing Tests
  test('Numeric Cost - Standard positive number', () => {
    const res = CloudGuardValidation.parseNumericCost('145.25');
    assert(res.valid, 'Should be valid');
    assertEqual(res.value, 145.25, 'Cost value');
    assert(!res.isCredit, 'Not credit');
  });

  test('Numeric Cost - Currency symbols and commas', () => {
    const res = CloudGuardValidation.parseNumericCost('$1,245.80');
    assert(res.valid, 'Should handle comma and dollar sign');
    assertEqual(res.value, 1245.80, 'Parsed number');
  });

  test('Numeric Cost - Accounting parentheses (Negative credit)', () => {
    const res = CloudGuardValidation.parseNumericCost('(150.00)');
    assert(res.valid, 'Should recognize parentheses as negative');
    assertEqual(res.value, -150.00, 'Negative value');
    assert(res.isCredit, 'Should flag as credit');
  });

  test('Numeric Cost - Minus sign negative credit', () => {
    const res = CloudGuardValidation.parseNumericCost('-$45.50');
    assert(res.valid, 'Minus sign handling');
    assertEqual(res.value, -45.50, 'Negative amount');
    assert(res.isCredit, 'Credit flag');
  });

  test('Numeric Cost - Invalid / Non-numeric entries', () => {
    assert(!CloudGuardValidation.parseNumericCost('N/A').valid, 'N/A should fail');
    assert(!CloudGuardValidation.parseNumericCost('NaN').valid, 'NaN should fail');
    assert(!CloudGuardValidation.parseNumericCost('FREE').valid, 'FREE should fail');
    assert(!CloudGuardValidation.parseNumericCost('').valid, 'Empty string should fail');
  });

  // Group 3: Schema & Header Validation
  test('Header Validation - Direct match', () => {
    const headers = ['usage_date', 'service', 'cost_amount', 'region'];
    const res = CloudGuardValidation.validateHeaders(headers);
    assert(res.isValid, 'Should validate direct headers');
    assertEqual(res.missingFields.length, 0, 'No missing fields');
  });

  test('Header Validation - Missing required column', () => {
    const headers = ['usage_date', 'region']; // missing service & cost_amount
    const res = CloudGuardValidation.validateHeaders(headers);
    assert(!res.isValid, 'Should flag missing fields');
    assert(res.missingFields.includes('service'), 'Missing service');
    assert(res.missingFields.includes('cost_amount'), 'Missing cost_amount');
  });

  test('Column Auto-Mapping Heuristic - AWS CUR Style', () => {
    const headers = ['line_item_unblended_cost', 'line_item_usage_start_date', 'line_item_product_code'];
    const { mapping } = CloudGuardNormalizer.suggestMapping(headers);
    assertEqual(mapping['line_item_unblended_cost'], 'cost_amount', 'Cost mapping');
    assertEqual(mapping['line_item_usage_start_date'], 'usage_date', 'Date mapping');
    assertEqual(mapping['line_item_product_code'], 'service', 'Service mapping');
  });

  test('Column Auto-Mapping Heuristic - Ambiguous Cost Columns', () => {
    const headers = ['unblended_cost', 'blended_cost', 'usage_date', 'service'];
    const { ambiguousCostCols } = CloudGuardNormalizer.suggestMapping(headers);
    assert(ambiguousCostCols.length >= 2, 'Should flag multiple candidate cost columns');
  });

  // Group 4: Record Normalization & Credit Calculations
  test('Normalization - Accurate Net Spend and Credit Aggregation', () => {
    const rawRows = [
      { usage_date: '2026-09-01', service: 'Amazon EC2', cost_amount: '100.00' },
      { usage_date: '2026-09-02', service: 'Amazon S3', cost_amount: '50.00' },
      { usage_date: '2026-09-03', service: 'Promotional Credit', cost_amount: '-25.00' },
    ];
    const mapping = { usage_date: 'usage_date', service: 'service', cost_amount: 'cost_amount' };
    const { records, summary } = CloudGuardNormalizer.normalizeRecords(rawRows, mapping);

    assertEqual(records.length, 3, 'All 3 rows parsed');
    assertEqual(summary.totalGrossSpend, 150.00, 'Gross spend');
    assertEqual(summary.totalCredits, 25.00, 'Credits total');
    assertEqual(summary.netSpend, 125.00, 'Net spend (150 - 25)');
  });

  test('Normalization - Duplicate Detection', () => {
    const rawRows = [
      { usage_date: '2026-09-01', service: 'Amazon EC2', cost_amount: '100.00' },
      { usage_date: '2026-09-01', service: 'Amazon EC2', cost_amount: '100.00' }, // duplicate
    ];
    const mapping = { usage_date: 'usage_date', service: 'service', cost_amount: 'cost_amount' };
    const { summary } = CloudGuardNormalizer.normalizeRecords(rawRows, mapping);
    assertEqual(summary.duplicateRows, 1, 'Duplicate counted');
  });

  // Group 5: Cost Engine Computations
  test('Cost Engine - Aggregations & Daily Average', () => {
    const records = [
      { usage_date: '2026-09-01', service: 'Amazon EC2', cost_amount: 100.00, region: 'us-east-1' },
      { usage_date: '2026-09-01', service: 'Amazon S3', cost_amount: 50.00, region: 'us-east-1' },
      { usage_date: '2026-09-02', service: 'Amazon EC2', cost_amount: 150.00, region: 'us-west-2' },
    ];
    const agg = CloudGuardCostEngine.computeAggregations(records, records);

    assertEqual(agg.totalSpend, 300.00, 'Total net spend');
    assertEqual(agg.uniqueDays, 2, '2 distinct billing days');
    assertEqual(agg.avgDailyCost, 150.00, 'Daily average (300 / 2)');
    assertEqual(agg.highestService.service, 'Amazon EC2', 'Highest service');
    assertEqual(agg.highestService.cost, 250.00, 'Highest service cost');
    assertEqual(agg.highestService.percentage, 83.33, 'Highest service percentage');
  });

  test('Cost Engine - Period-over-Period Comparison', () => {
    const records = [
      { usage_date: '2026-09-01', service: 'EC2', cost_amount: 100.00 },
      { usage_date: '2026-09-02', service: 'EC2', cost_amount: 100.00 },
      { usage_date: '2026-09-03', service: 'EC2', cost_amount: 150.00 },
      { usage_date: '2026-09-04', service: 'EC2', cost_amount: 150.00 },
    ];
    const agg = CloudGuardCostEngine.computeAggregations(records, records);
    // Period 1 (01, 02) = 200, Period 2 (03, 04) = 300. Delta = +100 (+50%)
    assertEqual(agg.periodComparison.currentPeriodCost, 300.00, 'Current period');
    assertEqual(agg.periodComparison.previousPeriodCost, 200.00, 'Previous period');
    assertEqual(agg.periodComparison.costDifference, 100.00, 'Difference');
    assertEqual(agg.periodComparison.percentChange, 50.00, 'Percent change');
    assertEqual(agg.periodComparison.trend, 'up', 'Upward trend');
  });

  // Group 6: Anomaly Detection Tests (MAD & Rolling Median)
  test('Anomaly Detector - Rolling Median & MAD Calculation', () => {
    const values = [10, 12, 11, 13, 100]; // 100 is outlier
    const median = CloudGuardAnomalyDetector.calculateMedian(values);
    assertEqual(median, 12, 'Median should be 12 (unaffected by 100)');
    const mad = CloudGuardAnomalyDetector.calculateMAD(values, median);
    // deviations: |10-12|=2, |12-12|=0, |11-12|=1, |13-12|=1, |100-12|=88 -> sorted: 0, 1, 1, 2, 88 -> median = 1
    assertEqual(mad, 1, 'MAD should be 1');
  });

  test('Anomaly Detector - Flagging a sudden cost spike', () => {
    // 7 days normal ($50), day 8 spike ($500)
    const records = [];
    for (let day = 1; day <= 7; day++) {
      records.push({
        usage_date: `2026-09-0${day}`,
        service: 'Amazon EC2',
        cost_amount: 50.00 + (day % 2),
      });
    }
    records.push({
      usage_date: '2026-09-08',
      service: 'Amazon EC2',
      cost_amount: 500.00, // Spike!
    });

    const anomalies = CloudGuardAnomalyDetector.detectAnomalies(records, { sensitivity: 'balanced' });
    assert(anomalies.length >= 1, 'Should detect at least 1 anomaly');
    assertEqual(anomalies[0].date, '2026-09-08', 'Spike date');
    assertEqual(anomalies[0].actualCost, 500.00, 'Actual cost');
    assertEqual(anomalies[0].severity, 'Critical', 'Critical severity');
    assert(anomalies[0].investigationSteps.length > 0, 'Investigation steps present');
  });

  // Group 7: Forecasting Tests
  test('Forecaster - Data sufficiency check (<7 days)', () => {
    const shortTrend = [
      { date: '2026-09-01', cost: 100 },
      { date: '2026-09-02', cost: 105 },
    ];
    const fcast = CloudGuardForecaster.generateForecast(shortTrend, { days: 14 });
    assert(!fcast.isValid, 'Should reject forecasting with only 2 days');
    assert(fcast.reason.includes('Insufficient data'), 'Explains data requirement');
  });

  test('Forecaster - 14-day projection with bounds (>=14 days)', () => {
    const fullTrend = [];
    for (let i = 1; i <= 15; i++) {
      fullTrend.push({
        date: `2026-09-${i < 10 ? '0' : ''}${i}`,
        cost: 100 + i * 2,
      });
    }
    const fcast = CloudGuardForecaster.generateForecast(fullTrend, { days: 14 });
    assert(fcast.isValid, 'Forecast should be valid');
    assertEqual(fcast.points.length, 14, '14 future points');
    assert(fcast.projectedTotal > 0, 'Projected total positive');
    assert(fcast.points[0].upperBound >= fcast.points[0].cost, 'Upper bound >= projected');
    assert(fcast.points[0].lowerBound <= fcast.points[0].cost, 'Lower bound <= projected');
  });

  // Group 8: Optimization Recommendations
  test('Recommendations - Compute Commitment Rule', () => {
    // Service with $300 spend (> $200 and > 15% share)
    const records = [];
    for (let i = 1; i <= 10; i++) {
      records.push({
        usage_date: `2026-09-${i < 10 ? '0' : ''}${i}`,
        service: 'Amazon EC2',
        cost_amount: 30.00,
      });
    }
    const agg = CloudGuardCostEngine.computeAggregations(records, records);
    const recs = CloudGuardRecommendations.generateRecommendations(records, agg);

    const computeRec = recs.find(r => r.category === 'Commitment Discounts');
    assert(computeRec !== undefined, 'Should generate Commitment recommendation');
    assert(computeRec.estimatedSavings > 0, 'Calculated defensible savings');
    assertEqual(computeRec.confidence, 'High', 'High confidence');
  });

  // --------------------------------------------------------------------------
  // RUNNER
  // --------------------------------------------------------------------------
  async function runAll() {
    passedCount = 0;
    failedCount = 0;
    testResults.length = 0;

    for (const t of tests) {
      const start = performance.now();
      try {
        await t.fn();
        const duration = Math.round((performance.now() - start) * 100) / 100;
        passedCount++;
        testResults.push({ name: t.name, status: 'PASSED', duration, error: null });
      } catch (err) {
        const duration = Math.round((performance.now() - start) * 100) / 100;
        failedCount++;
        testResults.push({ name: t.name, status: 'FAILED', duration, error: err.message });
      }
    }

    return {
      total: tests.length,
      passed: passedCount,
      failed: failedCount,
      results: testResults,
    };
  }

  return {
    test,
    runAll,
  };
})();

if (typeof window !== 'undefined') {
  window.CloudGuardTestSuite = CloudGuardTestSuite;
}
