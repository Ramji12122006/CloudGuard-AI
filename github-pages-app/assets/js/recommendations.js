/**
 * CloudGuard AI — Cost Optimization Recommendation Engine
 * Module: recommendations.js
 */

const CloudGuardRecommendations = (() => {
  /**
   * Analyze billing records and aggregations to generate explainable, evidence-backed recommendations.
   *
   * @param {Array} records - Filtered/all billing records
   * @param {Object} aggregations - Aggregated metrics from CostEngine
   * @returns {Array} List of recommendations
   */
  function generateRecommendations(records, aggregations) {
    if (!records || records.length === 0 || !aggregations) {
      return [];
    }

    const recs = [];
    const { totalSpend, byService, byRegion, periodComparison } = aggregations;

    // Rule 1: High Steady Compute Spend -> Commitment Discounts (Savings Plans / Reserved Instances)
    const computeKeywords = ['ec2', 'compute', 'virtual machine', 'eks', 'gke', 'app engine', 'cloud run'];
    const computeServices = byService.filter(s =>
      computeKeywords.some(k => s.service.toLowerCase().includes(k))
    );

    computeServices.forEach(s => {
      // If compute represents >= 20% of spending and >= $200 total
      if (s.cost >= 200 && s.percentage >= 15) {
        // A standard 1-year No Upfront Compute Savings Plan or Reserved Instance typically delivers 20% - 32% savings
        const conservativeSavings = Math.round(s.cost * 0.25 * 100) / 100;
        recs.push({
          id: `rec_compute_commitment_${s.service.replace(/[^a-zA-Z0-9]/g, '_')}`,
          title: `Evaluate 1-Year Commitment Plans for ${s.service}`,
          category: 'Commitment Discounts',
          service: s.service,
          evidence: `${s.service} totaled $${s.cost.toFixed(2)} (${s.percentage}% of analyzed spend) across ${s.count} billing line items.`,
          reason: 'Consistent, on-demand compute workloads that run 24/7 are prime candidates for 1-Year or 3-Year Reserved Instances or Savings Plans.',
          suggestedAction: 'Review average compute baseline in AWS Cost Explorer / GCP Recommender and purchase a partial commitment covering 60–70% of continuous usage to avoid overcommitting.',
          estimatedSavings: conservativeSavings,
          estimatedSavingsLabel: `~$${conservativeSavings.toFixed(2)} (est. 25% on steady-state hours)`,
          confidence: 'High',
          limitations: 'Calculated using standard 25% 1-year no-upfront commitment discount against observed total. Actual savings depend on instance family flexibility and utilization consistency.',
        });
      }
    });

    // Rule 2: Sustained Storage Growth -> Lifecycle Tiering
    const storageKeywords = ['s3', 'storage', 'blob', 'filestore', 'elastic file system'];
    const storageServices = byService.filter(s =>
      storageKeywords.some(k => s.service.toLowerCase().includes(k))
    );

    storageServices.forEach(s => {
      // Analyze daily trend for storage
      const storageDaily = {};
      records
        .filter(r => r.service === s.service)
        .forEach(r => {
          storageDaily[r.usage_date] = (storageDaily[r.usage_date] || 0) + r.cost_amount;
        });

      const dates = Object.keys(storageDaily).sort();
      if (dates.length >= 7) {
        const firstHalf = dates.slice(0, Math.floor(dates.length / 2));
        const secondHalf = dates.slice(Math.floor(dates.length / 2));
        const firstAvg = firstHalf.reduce((sum, d) => sum + storageDaily[d], 0) / firstHalf.length;
        const secondAvg = secondHalf.reduce((sum, d) => sum + storageDaily[d], 0) / secondHalf.length;

        // If storage spending grew by >= 15% between first half and second half
        if (secondAvg > firstAvg * 1.15 && s.cost >= 50) {
          const growthPct = Math.round(((secondAvg - firstAvg) / firstAvg) * 100);
          const potentialSavings = Math.round(s.cost * 0.20 * 100) / 100;

          recs.push({
            id: `rec_storage_lifecycle_${s.service.replace(/[^a-zA-Z0-9]/g, '_')}`,
            title: `Configure Automated Lifecycle Transitions for ${s.service}`,
            category: 'Storage Optimization',
            service: s.service,
            evidence: `Daily average spend grew by ${growthPct}% from $${firstAvg.toFixed(2)}/day to $${secondAvg.toFixed(2)}/day over the observation period.`,
            reason: 'Storage costs are compounding over time, which frequently indicates log retention, uncleaned snapshots, or un-transitioned objects in standard high-frequency tiers.',
            suggestedAction: 'Implement bucket lifecycle rules to transition objects older than 30–60 days to Infrequent Access (e.g. S3 Standard-IA) or Archive Glacier, and enable expiration rules on incomplete multipart uploads.',
            estimatedSavings: potentialSavings,
            estimatedSavingsLabel: `~$${potentialSavings.toFixed(2)} (est. 20% tiering savings)`,
            confidence: 'Medium',
            limitations: 'Estimated based on average 20–40% price difference between Standard and Infrequent Access tiers. Object access frequency and minimum storage durations must be verified before moving objects.',
          });
        }
      }
    });

    // Rule 3: Data Transfer / Egress Spike or Significant Spend
    const transferKeywords = ['data transfer', 'egress', 'nat gateway', 'bandwidth'];
    const transferServices = byService.filter(s =>
      transferKeywords.some(k => s.service.toLowerCase().includes(k))
    );

    transferServices.forEach(s => {
      if (s.cost >= 40) {
        const potentialSavings = Math.round(s.cost * 0.30 * 100) / 100;
        recs.push({
          id: `rec_transfer_egress_${s.service.replace(/[^a-zA-Z0-9]/g, '_')}`,
          title: `Audit Cross-AZ & Internet Egress in ${s.service}`,
          category: 'Network Architecture',
          service: s.service,
          evidence: `${s.service} accumulated $${s.cost.toFixed(2)} in network charges during the selected period.`,
          reason: 'Network egress charges frequently accrue silently from cross-Availability Zone database communication, public NAT Gateway traversal for S3 downloads, or uncompressed API traffic.',
          suggestedAction: '1) Deploy VPC Gateway Endpoints for S3 and DynamoDB (free of charge); 2) Consolidate microservices within the same Availability Zone where high-throughput inter-node replication occurs; 3) Enable CloudFront / CDN caching for public static assets.',
          estimatedSavings: potentialSavings,
          estimatedSavingsLabel: `~$${potentialSavings.toFixed(2)} (est. 30% via VPC endpoints/CDN)`,
          confidence: 'Medium',
          limitations: 'Egress savings depend heavily on whether traffic is internet-bound or internal VPC traffic. Inspect VPC Flow Logs to determine source and destination IP distributions.',
        });
      }
    });

    // Rule 4: High Period-over-Period Service Cost Increase
    if (periodComparison && periodComparison.previousPeriodCost > 0) {
      // Find specific service that drove the growth
      const dates = Object.keys(
        records.reduce((acc, r) => {
          acc[r.usage_date] = true;
          return acc;
        }, {})
      ).sort();

      if (dates.length >= 4) {
        const mid = Math.floor(dates.length / 2);
        const p1Dates = new Set(dates.slice(0, mid));
        const p2Dates = new Set(dates.slice(mid));

        const p1ServiceCosts = {};
        const p2ServiceCosts = {};

        records.forEach(r => {
          if (p1Dates.has(r.usage_date)) {
            p1ServiceCosts[r.service] = (p1ServiceCosts[r.service] || 0) + r.cost_amount;
          } else if (p2Dates.has(r.usage_date)) {
            p2ServiceCosts[r.service] = (p2ServiceCosts[r.service] || 0) + r.cost_amount;
          }
        });

        Object.keys(p2ServiceCosts).forEach(svc => {
          const c1 = p1ServiceCosts[svc] || 0;
          const c2 = p2ServiceCosts[svc] || 0;
          const diff = c2 - c1;
          const pct = c1 > 0 ? (diff / c1) * 100 : 100;

          if (diff >= 50 && pct >= 30) {
            recs.push({
              id: `rec_growth_${svc.replace(/[^a-zA-Z0-9]/g, '_')}`,
              title: `Investigate Sudden Period-over-Period Spike in ${svc}`,
              category: 'Cost Spike Alert',
              service: svc,
              evidence: `Spending rose from $${c1.toFixed(2)} in the first half to $${c2.toFixed(2)} in the second half (+${pct.toFixed(1)}%, +$${diff.toFixed(2)}).`,
              reason: 'Service cost grew substantially faster than typical baseline variation, which often points to newly deployed workloads, unintended scaling, or unreleased test environments.',
              suggestedAction: `Check CI/CD deployment logs and cloud provider event history around the transition date (${dates[mid]}) to identify newly launched clusters or modified configurations.`,
              estimatedSavings: null,
              estimatedSavingsLabel: 'Variable (requires root-cause audit)',
              confidence: 'High',
              limitations: 'Calculated directly from observed historical periods. If this cost increase corresponds to an intended business launch or traffic scaling, this growth may be expected.',
            });
          }
        });
      }
    }

    // Rule 5: Resource Tagging Governance (Untagged Spend)
    const untaggedRecords = records.filter(r => r.tag_project === 'untagged' || !r.tag_project);
    if (untaggedRecords.length > 0 && records.length > 20) {
      const untaggedCost = untaggedRecords.reduce((sum, r) => sum + r.cost_amount, 0);
      const untaggedPct = totalSpend > 0 ? Math.round((untaggedCost / totalSpend) * 100) : 0;

      if (untaggedCost >= 100 && untaggedPct >= 20) {
        recs.push({
          id: 'rec_tagging_governance',
          title: 'Enforce Cost Allocation Tagging Governance',
          category: 'FinOps Governance',
          service: 'Multi-Service',
          evidence: `$${untaggedCost.toFixed(2)} (${untaggedPct}% of total spend) is not associated with any project tag.`,
          reason: 'Resources without owner, project, or environment tags cannot be attributed to specific engineering teams, making orphan resource cleanup and departmental accountability difficult.',
          suggestedAction: 'Enable AWS Organizations SCPs / Azure Policies to require standard tags ("Project", "Environment", "Owner") at resource creation time, and activate user tags in the cloud billing console.',
          estimatedSavings: null,
          estimatedSavingsLabel: 'Organizational transparency benefit',
          confidence: 'High',
          limitations: 'Tagging enables attribution but does not directly reduce cloud spend until unowned/idle resources are identified and terminated.',
        });
      }
    }

    // Rule 6: Region Distribution Review
    if (byRegion.length > 1) {
      const topRegion = byRegion[0];
      const nicheRegions = byRegion.filter(r => r.region !== topRegion.region && r.cost >= 100);
      if (nicheRegions.length > 0) {
        const secondary = nicheRegions[0];
        recs.push({
          id: `rec_region_${secondary.region.replace(/[^a-zA-Z0-9]/g, '_')}`,
          title: `Evaluate Workload Placement in Secondary Region (${secondary.region})`,
          category: 'Regional Architecture',
          service: 'Regional Services',
          evidence: `${secondary.region} accounts for $${secondary.cost.toFixed(2)} (${secondary.percentage}% of total spend).`,
          reason: 'Operating workloads across multiple geographic regions increases inter-region replication and management overhead unless required for strict disaster recovery or latency constraints.',
          suggestedAction: 'Verify whether workloads in this region represent active multi-region production, legacy disaster recovery, or stray developer test environments that can be consolidated.',
          estimatedSavings: null,
          estimatedSavingsLabel: 'Auditing recommendation',
          confidence: 'Medium',
          limitations: 'Regional consolidation must be balanced against low-latency user requirements and regulatory data sovereignty policies.',
        });
      }
    }

    return recs;
  }

  return {
    generateRecommendations,
  };
})();

if (typeof window !== 'undefined') {
  window.CloudGuardRecommendations = CloudGuardRecommendations;
}
