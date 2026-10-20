/**
 * CloudGuard AI — Chart.js Visualization Module
 * Module: charts.js
 */

const CloudGuardCharts = (() => {
  // Store active Chart.js instances for proper disposal
  const instances = {
    overviewDaily: null,
    overviewService: null,
    overviewRegion: null,
    explorerMain: null,
    anomalyChart: null,
    forecastChart: null,
  };

  // Color Palette for Dark Dashboard Theme
  const COLORS = {
    cyan: '#06B6D4',
    cyanAlpha: 'rgba(6, 182, 212, 0.15)',
    blue: '#3B82F6',
    blueAlpha: 'rgba(59, 130, 246, 0.2)',
    indigo: '#6366F1',
    purple: '#A855F7',
    amber: '#F59E0B',
    amberAlpha: 'rgba(245, 158, 11, 0.2)',
    rose: '#F43F5E',
    roseAlpha: 'rgba(244, 63, 94, 0.2)',
    emerald: '#10B981',
    slateGrid: 'rgba(51, 65, 85, 0.5)',
    slateText: '#94A3B8',
    slateCard: '#1E293B',
    white: '#F8FAFC',
  };

  const PALETTE = [
    '#38BDF8', // Sky Blue
    '#06B6D4', // Cyan
    '#6366F1', // Indigo
    '#10B981', // Emerald
    '#F59E0B', // Amber
    '#EC4899', // Pink
    '#8B5CF6', // Purple
    '#14B8A6', // Teal
    '#F97316', // Orange
    '#E11D48', // Rose
  ];

  function getCurrencySymbol() {
    return CloudGuardState.getState().settings.symbol || '$';
  }

  function destroyChart(name) {
    if (instances[name]) {
      try {
        instances[name].destroy();
      } catch (e) {
        console.warn(`Error destroying chart ${name}:`, e);
      }
      instances[name] = null;
    }
  }

  /**
   * Render Overview Daily Spend Trend Chart
   */
  function renderOverviewDaily(canvasId, dailyTrend) {
    destroyChart('overviewDaily');
    const ctx = document.getElementById(canvasId);
    if (!ctx || !window.Chart) return;

    const sym = getCurrencySymbol();
    const labels = dailyTrend.map(d => d.date);
    const data = dailyTrend.map(d => d.cost);

    instances.overviewDaily = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Daily Cost',
            data,
            borderColor: COLORS.cyan,
            backgroundColor: COLORS.cyanAlpha,
            borderWidth: 2,
            tension: 0.25,
            fill: true,
            pointBackgroundColor: COLORS.cyan,
            pointBorderColor: '#0F172A',
            pointHoverRadius: 6,
            pointRadius: labels.length > 30 ? 1 : 3,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: COLORS.slateCard,
            titleColor: COLORS.white,
            bodyColor: COLORS.slateText,
            borderColor: '#334155',
            borderWidth: 1,
            padding: 10,
            callbacks: {
              label: ctx => ` ${ctx.dataset.label}: ${sym}${ctx.parsed.y.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            },
          },
        },
        scales: {
          x: {
            grid: { color: COLORS.slateGrid },
            ticks: { color: COLORS.slateText, maxTicksLimit: 10 },
          },
          y: {
            grid: { color: COLORS.slateGrid },
            ticks: {
              color: COLORS.slateText,
              callback: val => `${sym}${val}`,
            },
          },
        },
      },
    });
  }

  /**
   * Render Overview Service Breakdown Doughnut
   */
  function renderOverviewService(canvasId, byService) {
    destroyChart('overviewService');
    const ctx = document.getElementById(canvasId);
    if (!ctx || !window.Chart) return;

    const sym = getCurrencySymbol();
    const topServices = byService.slice(0, 7);
    const otherCost = byService.slice(7).reduce((sum, s) => sum + s.cost, 0);

    const labels = topServices.map(s => s.service);
    const data = topServices.map(s => s.cost);

    if (otherCost > 0) {
      labels.push('Other Services');
      data.push(Math.round(otherCost * 100) / 100);
    }

    instances.overviewService = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [
          {
            data,
            backgroundColor: PALETTE.slice(0, labels.length),
            borderColor: '#0F172A',
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'right',
            labels: {
              color: COLORS.slateText,
              boxWidth: 12,
              padding: 12,
              font: { size: 11 },
            },
          },
          tooltip: {
            backgroundColor: COLORS.slateCard,
            titleColor: COLORS.white,
            bodyColor: COLORS.slateText,
            borderColor: '#334155',
            borderWidth: 1,
            callbacks: {
              label: ctx => {
                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                return ` ${ctx.label}: ${sym}${ctx.parsed.toFixed(2)} (${pct}%)`;
              },
            },
          },
        },
        cutout: '68%',
      },
    });
  }

  /**
   * Render Overview Region Breakdown Doughnut
   */
  function renderOverviewRegion(canvasId, byRegion) {
    destroyChart('overviewRegion');
    const ctx = document.getElementById(canvasId);
    if (!ctx || !window.Chart) return;

    const sym = getCurrencySymbol();
    const topRegions = byRegion.slice(0, 6);
    const otherCost = byRegion.slice(6).reduce((sum, r) => sum + r.cost, 0);

    const labels = topRegions.map(r => r.region);
    const data = topRegions.map(r => r.cost);

    if (otherCost > 0) {
      labels.push('Other Regions');
      data.push(Math.round(otherCost * 100) / 100);
    }

    instances.overviewRegion = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [
          {
            data,
            backgroundColor: [
              '#06B6D4',
              '#3B82F6',
              '#10B981',
              '#F59E0B',
              '#8B5CF6',
              '#EC4899',
              '#64748B',
            ].slice(0, labels.length),
            borderColor: '#0F172A',
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'right',
            labels: {
              color: COLORS.slateText,
              boxWidth: 12,
              padding: 12,
              font: { size: 11 },
            },
          },
          tooltip: {
            backgroundColor: COLORS.slateCard,
            titleColor: COLORS.white,
            bodyColor: COLORS.slateText,
            borderColor: '#334155',
            borderWidth: 1,
            callbacks: {
              label: ctx => {
                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                const pct = total > 0 ? ((ctx.parsed / total) * 100).toFixed(1) : 0;
                return ` ${ctx.label}: ${sym}${ctx.parsed.toFixed(2)} (${pct}%)`;
              },
            },
          },
        },
        cutout: '68%',
      },
    });
  }

  /**
   * Render Cost Explorer Main Interactive Chart
   */
  function renderExplorerMain(canvasId, items, chartType = 'bar') {
    destroyChart('explorerMain');
    const ctx = document.getElementById(canvasId);
    if (!ctx || !window.Chart) return;

    const sym = getCurrencySymbol();
    const labels = items.map(i => i.date || i.name || i.service || i.region);
    const data = items.map(i => i.cost);

    instances.explorerMain = new Chart(ctx, {
      type: chartType,
      data: {
        labels,
        datasets: [
          {
            label: 'Cost',
            data,
            backgroundColor: chartType === 'line' ? COLORS.cyanAlpha : COLORS.blue,
            borderColor: chartType === 'line' ? COLORS.cyan : '#2563EB',
            borderWidth: chartType === 'line' ? 2 : 1,
            borderRadius: chartType === 'bar' ? 4 : 0,
            fill: chartType === 'line',
            tension: 0.2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: COLORS.slateCard,
            titleColor: COLORS.white,
            bodyColor: COLORS.slateText,
            borderColor: '#334155',
            borderWidth: 1,
            callbacks: {
              label: ctx => ` Cost: ${sym}${ctx.parsed.y.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
            },
          },
        },
        scales: {
          x: {
            grid: { color: COLORS.slateGrid },
            ticks: { color: COLORS.slateText, maxTicksLimit: 12 },
          },
          y: {
            grid: { color: COLORS.slateGrid },
            ticks: {
              color: COLORS.slateText,
              callback: val => `${sym}${val}`,
            },
          },
        },
      },
    });
  }

  /**
   * Render Anomaly Detection Time Series Chart
   */
  function renderAnomalyChart(canvasId, dailyTrend, anomalies) {
    destroyChart('anomalyChart');
    const ctx = document.getElementById(canvasId);
    if (!ctx || !window.Chart) return;

    const sym = getCurrencySymbol();
    const labels = dailyTrend.map(d => d.date);
    const costs = dailyTrend.map(d => d.cost);

    // Map anomalies to date points
    const anomalyMap = {};
    anomalies.forEach(a => {
      anomalyMap[a.date] = a;
    });

    const pointColors = labels.map(d => (anomalyMap[d] ? COLORS.rose : COLORS.cyan));
    const pointRadii = labels.map(d => (anomalyMap[d] ? 7 : 3));
    const pointHoverRadii = labels.map(d => (anomalyMap[d] ? 9 : 5));

    instances.anomalyChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Actual Cost',
            data: costs,
            borderColor: COLORS.cyan,
            backgroundColor: COLORS.cyanAlpha,
            borderWidth: 2,
            tension: 0.2,
            fill: false,
            pointBackgroundColor: pointColors,
            pointBorderColor: labels.map(d => (anomalyMap[d] ? '#FFFFFF' : '#0F172A')),
            pointBorderWidth: labels.map(d => (anomalyMap[d] ? 2 : 1)),
            pointRadius: pointRadii,
            pointHoverRadius: pointHoverRadii,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: COLORS.slateCard,
            titleColor: COLORS.white,
            bodyColor: COLORS.slateText,
            borderColor: '#334155',
            borderWidth: 1,
            callbacks: {
              label: ctx => {
                const d = labels[ctx.dataIndex];
                const anom = anomalyMap[d];
                if (anom) {
                  return [
                    ` Cost: ${sym}${ctx.parsed.y.toFixed(2)}`,
                    ` ⚠️ ANOMALY DETECTED [${anom.severity}]`,
                    ` Service: ${anom.service}`,
                    ` Baseline: ${sym}${anom.baselineCost.toFixed(2)} (${anom.costDifference > 0 ? '+' : ''}${sym}${anom.costDifference.toFixed(2)})`,
                  ];
                }
                return ` Cost: ${sym}${ctx.parsed.y.toFixed(2)}`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: { color: COLORS.slateGrid },
            ticks: { color: COLORS.slateText, maxTicksLimit: 10 },
          },
          y: {
            grid: { color: COLORS.slateGrid },
            ticks: {
              color: COLORS.slateText,
              callback: val => `${sym}${val}`,
            },
          },
        },
      },
    });
  }

  /**
   * Render Forecast Chart (Historical Actuals + Future Projections with Confidence Bounds)
   */
  function renderForecastChart(canvasId, historicalDaily, forecastData) {
    destroyChart('forecastChart');
    const ctx = document.getElementById(canvasId);
    if (!ctx || !window.Chart) return;

    const sym = getCurrencySymbol();

    if (!forecastData || !forecastData.isValid) {
      return;
    }

    const histLabels = historicalDaily.map(d => d.date);
    const histData = historicalDaily.map(d => d.cost);

    const fcastLabels = forecastData.points.map(p => p.date);
    const fcastData = forecastData.points.map(p => p.cost);
    const upperBounds = forecastData.points.map(p => p.upperBound);
    const lowerBounds = forecastData.points.map(p => p.lowerBound);

    // Merge labels
    const combinedLabels = [...histLabels, ...fcastLabels];

    // Historical dataset: filled with nulls during forecast horizon
    const histDataset = [...histData, ...Array(fcastLabels.length).fill(null)];

    // Forecast dataset: filled with nulls during historical period, but anchors to last historical point
    const lastHistVal = histData[histData.length - 1];
    const fcastDataset = [
      ...Array(histLabels.length - 1).fill(null),
      lastHistVal,
      ...fcastData,
    ];

    // Upper confidence band
    const upperDataset = [
      ...Array(histLabels.length - 1).fill(null),
      lastHistVal,
      ...upperBounds,
    ];

    // Lower confidence band
    const lowerDataset = [
      ...Array(histLabels.length - 1).fill(null),
      lastHistVal,
      ...lowerBounds,
    ];

    instances.forecastChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: combinedLabels,
        datasets: [
          {
            label: 'Historical Cost',
            data: histDataset,
            borderColor: COLORS.cyan,
            backgroundColor: COLORS.cyanAlpha,
            borderWidth: 2,
            tension: 0.2,
            fill: false,
            pointRadius: 2,
          },
          {
            label: 'Projected Forecast',
            data: fcastDataset,
            borderColor: COLORS.amber,
            backgroundColor: 'transparent',
            borderWidth: 2,
            borderDash: [5, 5],
            tension: 0.2,
            fill: false,
            pointRadius: 3,
            pointBackgroundColor: COLORS.amber,
          },
          {
            label: 'Upper Bound (95% CI)',
            data: upperDataset,
            borderColor: 'transparent',
            backgroundColor: COLORS.amberAlpha,
            borderWidth: 0,
            pointRadius: 0,
            fill: '+1', // Fill down to lower bound
          },
          {
            label: 'Lower Bound (95% CI)',
            data: lowerDataset,
            borderColor: 'transparent',
            backgroundColor: 'transparent',
            borderWidth: 0,
            pointRadius: 0,
            fill: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            labels: {
              color: COLORS.slateText,
              filter: item => item.text !== 'Lower Bound (95% CI)',
            },
          },
          tooltip: {
            backgroundColor: COLORS.slateCard,
            titleColor: COLORS.white,
            bodyColor: COLORS.slateText,
            borderColor: '#334155',
            borderWidth: 1,
            callbacks: {
              label: ctx => {
                if (ctx.raw === null || ctx.raw === undefined) return null;
                return ` ${ctx.dataset.label}: ${sym}${Number(ctx.raw).toFixed(2)}`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: { color: COLORS.slateGrid },
            ticks: { color: COLORS.slateText, maxTicksLimit: 12 },
          },
          y: {
            grid: { color: COLORS.slateGrid },
            ticks: {
              color: COLORS.slateText,
              callback: val => `${sym}${val}`,
            },
          },
        },
      },
    });
  }

  return {
    destroyChart,
    renderOverviewDaily,
    renderOverviewService,
    renderOverviewRegion,
    renderExplorerMain,
    renderAnomalyChart,
    renderForecastChart,
  };
})();

if (typeof window !== 'undefined') {
  window.CloudGuardCharts = CloudGuardCharts;
}
