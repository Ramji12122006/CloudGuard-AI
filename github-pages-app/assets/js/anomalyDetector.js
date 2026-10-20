/**
 * CloudGuard AI — Statistical Anomaly Detection Engine
 * Module: anomalyDetector.js
 */

const CloudGuardAnomalyDetector = (() => {
  /**
   * Detect anomalies in cloud spending using Rolling Median & Median Absolute Deviation (MAD).
   *
   * @param {Array} records - Normalized billing records
   * @param {Object} options - Configuration options (sensitivity, madMultiplier, minHistoryDays)
   * @returns {Array} List of detected anomalies with statistical explanations
   */
  function detectAnomalies(records, options = {}) {
    if (!records || records.length === 0) return [];

    const sensitivity = options.sensitivity || 'balanced';
    const multiplier = options.madMultiplier || (sensitivity === 'strict' ? 2.0 : sensitivity === 'relaxed' ? 4.5 : 3.0);
    const minHistoryDays = options.minHistoryDays || 5;

    // 1. Group costs by service and date
    // service -> date -> totalDailyCost
    const serviceDateCosts = {};
    const allDatesSet = new Set();

    records.forEach(rec => {
      allDatesSet.add(rec.usage_date);
      if (!serviceDateCosts[rec.service]) {
        serviceDateCosts[rec.service] = {};
      }
      if (!serviceDateCosts[rec.service][rec.usage_date]) {
        serviceDateCosts[rec.service][rec.usage_date] = 0;
      }
      serviceDateCosts[rec.service][rec.usage_date] += rec.cost_amount;
    });

    const sortedDates = Array.from(allDatesSet).sort();
    const detectedAnomalies = [];

    // 2. Iterate through each service
    Object.keys(serviceDateCosts).forEach(service => {
      const dateMap = serviceDateCosts[service];
      const serviceDates = Object.keys(dateMap).sort();

      // We need at least minHistoryDays of data points
      if (serviceDates.length < minHistoryDays) {
        return; // Insufficient history to establish a statistically reliable baseline
      }

      // Rolling window evaluation
      for (let i = 0; i < serviceDates.length; i++) {
        const currentDate = serviceDates[i];
        const actualCost = dateMap[currentDate];

        // Gather baseline from prior days (up to 14 days of history)
        const historyWindow = serviceDates.slice(Math.max(0, i - 14), i);
        if (historyWindow.length < Math.min(minHistoryDays, 4)) {
          // Skip early days before baseline can be established
          continue;
        }

        const historicalCosts = historyWindow.map(d => dateMap[d]);
        const baselineMedian = calculateMedian(historicalCosts);
        const mad = calculateMAD(historicalCosts, baselineMedian);

        const delta = actualCost - baselineMedian;
        const absDelta = Math.abs(delta);

        // Check if anomaly condition is met
        let isAnomaly = false;
        let detectionReason = '';
        let severity = 'Low';

        // Safe Handling: Zero Baseline
        if (baselineMedian === 0) {
          if (actualCost >= 25.0) {
            isAnomaly = true;
            detectionReason = `Sudden active spend of $${actualCost.toFixed(2)} on service with $0.00 historical baseline.`;
            severity = actualCost >= 200 ? 'Critical' : actualCost >= 75 ? 'High' : 'Medium';
          }
        } else if (mad === 0) {
          // Constant historical spend
          if (absDelta >= 10.0 && absDelta / Math.max(1, baselineMedian) >= 0.5) {
            isAnomaly = true;
            detectionReason = `Spend changed by $${delta.toFixed(2)} (${formatPct(delta, baselineMedian)}) from constant baseline of $${baselineMedian.toFixed(2)}.`;
            severity = absDelta >= 100 ? 'Critical' : absDelta >= 40 ? 'High' : 'Medium';
          }
        } else {
          // Standard MAD threshold
          const threshold = multiplier * mad;
          const modifiedZ = (0.6745 * absDelta) / mad;

          if (absDelta > threshold && absDelta >= 5.0) {
            isAnomaly = true;
            const direction = delta > 0 ? 'higher' : 'lower';
            detectionReason = `Spend of $${actualCost.toFixed(2)} is ${modifiedZ.toFixed(1)}x MAD ${direction} than the rolling median baseline ($${baselineMedian.toFixed(2)} ± $${threshold.toFixed(2)}).`;

            // Severity ranking
            if (modifiedZ >= 6.0 || (delta > 0 && absDelta >= 200)) {
              severity = 'Critical';
            } else if (modifiedZ >= 4.0 || (delta > 0 && absDelta >= 75)) {
              severity = 'High';
            } else if (modifiedZ >= 2.5) {
              severity = 'Medium';
            } else {
              severity = 'Low';
            }
          }
        }

        if (isAnomaly) {
          const pctChange = baselineMedian !== 0 ? ((delta / Math.abs(baselineMedian)) * 100) : null;
          const investigationSteps = generateInvestigationSteps(service, actualCost, baselineMedian, delta);

          detectedAnomalies.push({
            id: `anom_${service.replace(/[^a-zA-Z0-9]/g, '_')}_${currentDate}`,
            date: currentDate,
            service,
            actualCost: round2(actualCost),
            baselineCost: round2(baselineMedian),
            costDifference: round2(delta),
            percentageDifference: pctChange !== null ? round2(pctChange) : null,
            severity,
            reason: detectionReason,
            investigationSteps,
            type: delta > 0 ? 'Spike' : 'Drop',
          });
        }
      }
    });

    // Sort anomalies: Critical first, then High, then most recent date
    const severityRank = { Critical: 4, High: 3, Medium: 2, Low: 1 };
    detectedAnomalies.sort((a, b) => {
      const rankDiff = (severityRank[b.severity] || 0) - (severityRank[a.severity] || 0);
      if (rankDiff !== 0) return rankDiff;
      return b.date > a.date ? 1 : -1;
    });

    return detectedAnomalies;
  }

  /**
   * Calculate median of numeric array.
   */
  function calculateMedian(arr) {
    if (!arr || arr.length === 0) return 0;
    const sorted = [...arr].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    if (sorted.length % 2 === 0) {
      return (sorted[mid - 1] + sorted[mid]) / 2;
    }
    return sorted[mid];
  }

  /**
   * Calculate Median Absolute Deviation (MAD).
   */
  function calculateMAD(arr, median) {
    if (!arr || arr.length === 0) return 0;
    const med = median !== undefined ? median : calculateMedian(arr);
    const deviations = arr.map(x => Math.abs(x - med));
    return calculateMedian(deviations);
  }

  function formatPct(delta, baseline) {
    if (!baseline) return 'N/A';
    const pct = (delta / Math.abs(baseline)) * 100;
    return `${pct > 0 ? '+' : ''}${pct.toFixed(1)}%`;
  }

  /**
   * Generate actionable investigation recommendations for an anomaly.
   */
  function generateInvestigationSteps(service, actual, baseline, delta) {
    const sLower = service.toLowerCase();
    const steps = [];

    if (sLower.includes('ec2') || sLower.includes('compute') || sLower.includes('vm')) {
      steps.push('Check autoscaling group min/max instance settings and recent scale-out events.');
      steps.push('Verify whether on-demand GPU or high-memory instances were launched for ad-hoc batch jobs.');
      steps.push('Inspect unattached EBS volumes or unassociated Elastic IPs created on this date.');
    } else if (sLower.includes('s3') || sLower.includes('storage') || sLower.includes('blob')) {
      steps.push('Inspect large bucket replication tasks, backup exports, or uncleaned multipart uploads.');
      steps.push('Review API request costs (PUT/LIST requests) if data volume did not spike proportionally.');
    } else if (sLower.includes('transfer') || sLower.includes('egress') || sLower.includes('nat')) {
      steps.push('Check VPC Flow Logs for sudden cross-AZ data replication or uncompressed database dumps.');
      steps.push('Verify if a public NAT Gateway was used instead of an internal S3/DynamoDB Gateway Endpoint.');
    } else if (sLower.includes('lambda') || sLower.includes('function')) {
      steps.push('Check for recursive invocation loops or infinite retry loops triggered by SQS/EventBridge.');
      steps.push('Review concurrency limits and memory allocation settings on updated function revisions.');
    } else if (sLower.includes('rds') || sLower.includes('database') || sLower.includes('sql')) {
      steps.push('Check for ad-hoc database snapshots or automated backup retention window expansions.');
      steps.push('Verify if Multi-AZ standby or read replicas were provisioned.');
    } else {
      steps.push(`Review cloud provider audit logs (e.g. AWS CloudTrail, GCP Audit Logs) for resources created in ${service}.`);
      steps.push('Confirm with engineering teams whether a scheduled load test or migration occurred on this date.');
    }

    steps.push('Compare granular line items in billing export to pinpoint specific Resource IDs.');
    return steps;
  }

  function round2(num) {
    return Math.round((num + Number.EPSILON) * 100) / 100;
  }

  return {
    detectAnomalies,
    calculateMedian,
    calculateMAD,
  };
})();

if (typeof window !== 'undefined') {
  window.CloudGuardAnomalyDetector = CloudGuardAnomalyDetector;
}
