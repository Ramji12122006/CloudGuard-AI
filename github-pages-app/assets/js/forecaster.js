/**
 * CloudGuard AI — Cost Forecasting Module
 * Module: forecaster.js
 */

const CloudGuardForecaster = (() => {
  /**
   * Generate cost forecast for the specified horizon (7, 14, or 30 days).
   *
   * @param {Array} dailyTrend - Array of { date: 'YYYY-MM-DD', cost: number }
   * @param {Object} options - { days: 14, method: 'auto' | 'baseline' | 'trend' }
   */
  function generateForecast(dailyTrend, options = {}) {
    const horizon = options.days || 14;
    const requestedMethod = options.method || 'auto';

    if (!dailyTrend || dailyTrend.length === 0) {
      return {
        isValid: false,
        reason: 'No historical billing data available to forecast.',
        points: [],
        projectedTotal: 0,
        projectedDailyAvg: 0,
        methodUsed: 'None',
        confidenceLevel: 'None',
        explanation: 'Upload billing CSV data to enable forecasting.',
        limitations: 'A minimum of 7 consecutive billing days is required for baseline forecasting.',
      };
    }

    // Sort chronologically
    const sorted = [...dailyTrend].sort((a, b) => (a.date > b.date ? 1 : -1));
    const n = sorted.length;

    // Minimum data check
    if (n < 7) {
      return {
        isValid: false,
        reason: `Insufficient data: Found ${n} days of history. CloudGuard requires at least 7 days to produce a defensible forecast.`,
        points: [],
        projectedTotal: 0,
        projectedDailyAvg: 0,
        methodUsed: 'Insufficient Data',
        confidenceLevel: 'Low',
        explanation: 'Only a few days of data are available. Projecting future cloud costs without sufficient baseline history would yield misleading results.',
        limitations: 'Cloud billing often exhibits weekly cycles (lower weekend compute, weekly batch jobs). At least 7–14 days are necessary to estimate representative averages.',
      };
    }

    // Determine method
    let method = 'baseline';
    if (requestedMethod === 'trend' || (requestedMethod === 'auto' && n >= 14)) {
      method = 'trend';
    }

    const costs = sorted.map(d => d.cost);
    const lastDateStr = sorted[n - 1].date;

    let forecastPoints = [];
    let methodExplanation = '';
    let confidenceBand = 0;

    // Estimate baseline variance / residual standard error for confidence intervals
    const mean = costs.reduce((a, b) => a + b, 0) / n;
    const variance = costs.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / (n - 1 || 1);
    const stdDev = Math.sqrt(variance);

    if (method === 'trend') {
      // Linear regression on time index: y = slope * x + intercept
      let sumX = 0;
      let sumY = 0;
      let sumXY = 0;
      let sumXX = 0;

      for (let i = 0; i < n; i++) {
        sumX += i;
        sumY += costs[i];
        sumXY += i * costs[i];
        sumXX += i * i;
      }

      const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX || 1);
      const intercept = (sumY - slope * sumX) / n;

      // Apply conservative trend damping to prevent unrealistic linear divergence
      const dampingFactor = 0.95; // dampens slope slightly into the future

      forecastPoints = [];
      let lastVal = costs[n - 1];

      for (let step = 1; step <= horizon; step++) {
        const nextDate = addDays(lastDateStr, step);
        const projectedIndex = n - 1 + step;
        
        // Damped slope projection
        const dampedSlope = slope * Math.pow(dampingFactor, step);
        let projectedVal = intercept + slope * (n - 1) + dampedSlope * step;

        // Prevent negative forecast if history was mostly positive
        if (mean > 0 && projectedVal < 0) {
          projectedVal = 0;
        }

        // Confidence interval widens with time horizon: ± (1.96 * stdDev * sqrt(1 + step/n))
        const stepMargin = 1.96 * stdDev * Math.sqrt(1 + step / n);

        forecastPoints.push({
          date: nextDate,
          cost: round2(projectedVal),
          upperBound: round2(projectedVal + stepMargin),
          lowerBound: round2(Math.max(0, projectedVal - stepMargin)),
        });
      }

      methodExplanation = `Trend-Adjusted Linear Projection: Calculated based on ${n} historical days with regression slope of $${slope.toFixed(2)}/day, damped for long-term stability.`;
      confidenceBand = round2(1.96 * stdDev);
    } else {
      // Simple Baseline: Exponentially Weighted Moving Average (EWMA) of recent 7 days
      const recentWindow = costs.slice(-7);
      const alpha = 0.3; // smoothing factor
      let ewma = recentWindow[0];
      for (let i = 1; i < recentWindow.length; i++) {
        ewma = alpha * recentWindow[i] + (1 - alpha) * ewma;
      }

      forecastPoints = [];
      const margin = 1.645 * stdDev; // 90% confidence interval

      for (let step = 1; step <= horizon; step++) {
        const nextDate = addDays(lastDateStr, step);
        const stepMargin = margin * Math.sqrt(1 + step / 7);

        forecastPoints.push({
          date: nextDate,
          cost: round2(ewma),
          upperBound: round2(ewma + stepMargin),
          lowerBound: round2(Math.max(0, ewma - stepMargin)),
        });
      }

      methodExplanation = `Weighted Moving Average (EWMA): Baseline calculated from the most recent 7 days of spending ($${ewma.toFixed(2)}/day). Suitable for steady spending patterns.`;
      confidenceBand = round2(margin);
    }

    const projectedTotal = round2(forecastPoints.reduce((sum, p) => sum + p.cost, 0));
    const projectedDailyAvg = round2(projectedTotal / horizon);

    return {
      isValid: true,
      points: forecastPoints,
      horizonDays: horizon,
      projectedTotal,
      projectedDailyAvg,
      methodUsed: method === 'trend' ? 'Trend-Adjusted Linear Regression' : 'Weighted Moving Average (EWMA)',
      confidenceLevel: n >= 28 ? 'High (28+ days history)' : n >= 14 ? 'Moderate (14–27 days history)' : 'Basic (7–13 days history)',
      explanation: methodExplanation,
      limitations: 'Statistical projections assume continuation of historical consumption rates. Forecasts do not anticipate unannounced architectural changes, major database migrations, or sudden provider pricing shifts.',
      historicalMean: round2(mean),
      historicalStdDev: round2(stdDev),
    };
  }

  function addDays(dateStr, days) {
    const d = new Date(dateStr);
    d.setUTCDate(d.getUTCDate() + days);
    const year = d.getUTCFullYear();
    const month = d.getUTCMonth() + 1;
    const day = d.getUTCDate();
    return `${year}-${month < 10 ? '0' : ''}${month}-${day < 10 ? '0' : ''}${day}`;
  }

  function round2(num) {
    return Math.round((num + Number.EPSILON) * 100) / 100;
  }

  return {
    generateForecast,
  };
})();

if (typeof window !== 'undefined') {
  window.CloudGuardForecaster = CloudGuardForecaster;
}
