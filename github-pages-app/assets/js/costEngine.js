/**
 * CloudGuard AI — Cost Calculation & Aggregation Engine
 * Module: costEngine.js
 */

const CloudGuardCostEngine = (() => {
  /**
   * Filter records based on active filter criteria.
   */
  function filterRecords(records, filters) {
    if (!records || records.length === 0) return [];

    const { dateRange, services, regions, accounts, searchTerm } = filters;
    const searchLower = (searchTerm || '').trim().toLowerCase();

    return records.filter(rec => {
      // Date Range Filter
      if (dateRange && dateRange.start && rec.usage_date < dateRange.start) {
        return false;
      }
      if (dateRange && dateRange.end && rec.usage_date > dateRange.end) {
        return false;
      }

      // Service Filter
      if (services && services.length > 0 && !services.includes(rec.service)) {
        return false;
      }

      // Region Filter
      if (regions && regions.length > 0 && !regions.includes(rec.region)) {
        return false;
      }

      // Account Filter
      if (accounts && accounts.length > 0 && !accounts.includes(rec.account_id)) {
        return false;
      }

      // Live Text Search Filter
      if (searchLower) {
        const matchService = rec.service.toLowerCase().includes(searchLower);
        const matchRegion = (rec.region || '').toLowerCase().includes(searchLower);
        const matchAccount = (rec.account_name || rec.account_id || '').toLowerCase().includes(searchLower);
        const matchProject = (rec.tag_project || '').toLowerCase().includes(searchLower);
        const matchEnv = (rec.tag_environment || '').toLowerCase().includes(searchLower);
        if (!matchService && !matchRegion && !matchAccount && !matchProject && !matchEnv) {
          return false;
        }
      }

      return true;
    });
  }

  /**
   * Compute comprehensive dashboard metrics and breakdowns from a set of records.
   */
  function computeAggregations(filteredRecords, allRecords = []) {
    if (!filteredRecords || filteredRecords.length === 0) {
      return {
        totalSpend: 0,
        grossSpend: 0,
        totalCredits: 0,
        uniqueDays: 0,
        avgDailyCost: 0,
        highestService: { service: 'None', cost: 0, percentage: 0 },
        dailyTrend: [],
        byService: [],
        byRegion: [],
        byAccount: [],
        byProject: [],
        byEnvironment: [],
        periodComparison: {
          currentPeriodCost: 0,
          previousPeriodCost: 0,
          costDifference: 0,
          percentChange: 0,
          trend: 'neutral',
        },
      };
    }

    let grossSpend = 0;
    let totalCredits = 0;
    const dailyMap = {};
    const serviceMap = {};
    const regionMap = {};
    const accountMap = {};
    const projectMap = {};
    const envMap = {};

    filteredRecords.forEach(rec => {
      const cost = rec.cost_amount;
      if (cost < 0) {
        totalCredits += Math.abs(cost);
      } else {
        grossSpend += cost;
      }

      // Daily grouping
      if (!dailyMap[rec.usage_date]) {
        dailyMap[rec.usage_date] = 0;
      }
      dailyMap[rec.usage_date] += cost;

      // Service grouping
      if (!serviceMap[rec.service]) {
        serviceMap[rec.service] = { cost: 0, count: 0 };
      }
      serviceMap[rec.service].cost += cost;
      serviceMap[rec.service].count += 1;

      // Region grouping
      const region = rec.region || 'global';
      if (!regionMap[region]) {
        regionMap[region] = 0;
      }
      regionMap[region] += cost;

      // Account grouping
      const accKey = rec.account_name || rec.account_id || 'Default';
      if (!accountMap[accKey]) {
        accountMap[accKey] = 0;
      }
      accountMap[accKey] += cost;

      // Project grouping
      const project = rec.tag_project || 'untagged';
      if (!projectMap[project]) {
        projectMap[project] = 0;
      }
      projectMap[project] += cost;

      // Environment grouping
      const env = rec.tag_environment || 'unspecified';
      if (!envMap[env]) {
        envMap[env] = 0;
      }
      envMap[env] += cost;
    });

    const netSpend = grossSpend - totalCredits;
    const uniqueDates = Object.keys(dailyMap).sort();
    const uniqueDays = uniqueDates.length;
    const avgDailyCost = uniqueDays > 0 ? netSpend / uniqueDays : 0;

    // Build Daily Trend Array
    const dailyTrend = uniqueDates.map(date => ({
      date,
      cost: round2(dailyMap[date]),
    }));

    // Service Breakdown
    const byService = Object.entries(serviceMap)
      .map(([service, data]) => ({
        service,
        cost: round2(data.cost),
        count: data.count,
        percentage: netSpend > 0 ? round2((data.cost / netSpend) * 100) : 0,
      }))
      .sort((a, b) => b.cost - a.cost);

    const highestService = byService[0] || { service: 'None', cost: 0, percentage: 0 };

    // Region Breakdown
    const byRegion = Object.entries(regionMap)
      .map(([region, cost]) => ({
        region,
        cost: round2(cost),
        percentage: netSpend > 0 ? round2((cost / netSpend) * 100) : 0,
      }))
      .sort((a, b) => b.cost - a.cost);

    // Account Breakdown
    const byAccount = Object.entries(accountMap)
      .map(([account, cost]) => ({
        account,
        cost: round2(cost),
        percentage: netSpend > 0 ? round2((cost / netSpend) * 100) : 0,
      }))
      .sort((a, b) => b.cost - a.cost);

    // Project Breakdown
    const byProject = Object.entries(projectMap)
      .map(([project, cost]) => ({
        project,
        cost: round2(cost),
        percentage: netSpend > 0 ? round2((cost / netSpend) * 100) : 0,
      }))
      .sort((a, b) => b.cost - a.cost);

    // Environment Breakdown
    const byEnvironment = Object.entries(envMap)
      .map(([environment, cost]) => ({
        environment,
        cost: round2(cost),
        percentage: netSpend > 0 ? round2((cost / netSpend) * 100) : 0,
      }))
      .sort((a, b) => b.cost - a.cost);

    // Period-over-period comparison
    const periodComparison = calculatePeriodComparison(uniqueDates, dailyMap);

    return {
      totalSpend: round2(netSpend),
      grossSpend: round2(grossSpend),
      totalCredits: round2(totalCredits),
      uniqueDays,
      avgDailyCost: round2(avgDailyCost),
      highestService,
      dailyTrend,
      byService,
      byRegion,
      byAccount,
      byProject,
      byEnvironment,
      periodComparison,
    };
  }

  /**
   * Calculate spending change compared with the previous period of identical length.
   */
  function calculatePeriodComparison(sortedDates, dailyMap) {
    if (!sortedDates || sortedDates.length < 2) {
      return {
        currentPeriodCost: 0,
        previousPeriodCost: 0,
        costDifference: 0,
        percentChange: 0,
        trend: 'neutral',
      };
    }

    const midpoint = Math.floor(sortedDates.length / 2);
    const prevDates = sortedDates.slice(0, midpoint);
    const currDates = sortedDates.slice(midpoint);

    let prevTotal = 0;
    prevDates.forEach(d => {
      prevTotal += dailyMap[d] || 0;
    });

    let currTotal = 0;
    currDates.forEach(d => {
      currTotal += dailyMap[d] || 0;
    });

    const diff = currTotal - prevTotal;
    let pct = 0;
    if (prevTotal > 0) {
      pct = round2((diff / prevTotal) * 100);
    } else if (prevTotal === 0 && currTotal > 0) {
      pct = 100.0;
    }

    let trend = 'neutral';
    if (diff > 0.01) trend = 'up';
    else if (diff < -0.01) trend = 'down';

    return {
      currentPeriodCost: round2(currTotal),
      previousPeriodCost: round2(prevTotal),
      costDifference: round2(diff),
      percentChange: pct,
      trend,
    };
  }

  /**
   * Aggregate daily spending by Weekly or Monthly granularity.
   */
  function aggregateByGranularity(dailyTrend, granularity = 'daily') {
    if (granularity === 'daily' || !dailyTrend || dailyTrend.length === 0) {
      return dailyTrend;
    }

    const groups = {};

    dailyTrend.forEach(item => {
      let key = item.date;
      if (granularity === 'monthly') {
        key = item.date.substring(0, 7); // YYYY-MM
      } else if (granularity === 'weekly') {
        const d = new Date(item.date);
        const day = d.getUTCDay();
        const diff = d.getUTCDate() - day + (day === 0 ? -6 : 1); // Monday
        const monday = new Date(d.setUTCDate(diff));
        key = `W-${monday.toISOString().substring(0, 10)}`;
      }

      if (!groups[key]) {
        groups[key] = 0;
      }
      groups[key] += item.cost;
    });

    return Object.keys(groups).map(k => ({
      date: k,
      cost: round2(groups[k]),
    }));
  }

  /**
   * Sort and paginate records for the data table.
   */
  function paginateRecords(records, pagination) {
    const { currentPage = 1, pageSize = 15, sortColumn = 'usage_date', sortDirection = 'desc' } = pagination;

    const sorted = [...records].sort((a, b) => {
      let valA = a[sortColumn];
      let valB = b[sortColumn];

      if (valA === undefined || valA === null) valA = '';
      if (valB === undefined || valB === null) valB = '';

      if (typeof valA === 'number' && typeof valB === 'number') {
        return sortDirection === 'asc' ? valA - valB : valB - valA;
      }

      const strA = String(valA).toLowerCase();
      const strB = String(valB).toLowerCase();
      if (strA < strB) return sortDirection === 'asc' ? -1 : 1;
      if (strA > strB) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    const totalRecords = sorted.length;
    const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize));
    const validPage = Math.min(Math.max(1, currentPage), totalPages);
    const startIdx = (validPage - 1) * pageSize;
    const pageRecords = sorted.slice(startIdx, startIdx + pageSize);

    return {
      records: pageRecords,
      totalRecords,
      totalPages,
      currentPage: validPage,
      pageSize,
      startIndex: startIdx + 1,
      endIndex: Math.min(startIdx + pageSize, totalRecords),
    };
  }

  function round2(num) {
    return Math.round((num + Number.EPSILON) * 100) / 100;
  }

  return {
    filterRecords,
    computeAggregations,
    aggregateByGranularity,
    paginateRecords,
    round2,
  };
})();

if (typeof window !== 'undefined') {
  window.CloudGuardCostEngine = CloudGuardCostEngine;
}
