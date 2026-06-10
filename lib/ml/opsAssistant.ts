import { createClient } from '@supabase/supabase-js'

export type OpsInsightSeverity = 'HIGH' | 'MEDIUM' | 'LOW'
export type OpsInsightCategory = 'overdue_order' | 'unassigned_ready_order' | 'demand_surge' | 'partner_shortage' | 'merchant_delay' | 'high_risk_order' | 'refund_spike' | 'low_trust_partner' | 'data_quality_failure'

export interface OpsInsightData {
  severity: OpsInsightSeverity
  category: OpsInsightCategory
  source_table: string
  source_id?: string
  entity_id?: string
  features: Record<string, unknown>
  explanation: string
  recommended_action: string
}

export async function generateOpsInsights(supabaseUrl: string, supabaseServiceKey: string): Promise<OpsInsightData[]> {
  const supabase = createClient(supabaseUrl, supabaseServiceKey)
  const insights: OpsInsightData[] = []

  // 1. Overdue Orders
  const { data: overdueOrders } = await supabase
    .from('orders')
    .select('id, customer_id, merchant_id, status, created_at, total_amount')
    .in('status', ['accepted', 'preparing', 'ready', 'picked_up'])
    .lt('created_at', new Date(Date.now() - 45 * 60 * 1000).toISOString())
  
  if (overdueOrders) {
    for (const order of overdueOrders) {
      insights.push({
        severity: 'HIGH',
        category: 'overdue_order',
        source_table: 'orders',
        source_id: order.id,
        entity_id: order.merchant_id || undefined,
        features: { delay_mins: 45, status: order.status, total_amount: order.total_amount },
        explanation: `Order ${order.id.slice(0, 8)} has been stuck in '${order.status}' for over 45 minutes.`,
        recommended_action: 'Contact merchant or assign priority partner.'
      })
    }
  }

  // 2. Unassigned Ready Orders
  const { data: unassignedOrders } = await supabase
    .from('orders')
    .select('id, merchant_id, created_at')
    .eq('status', 'ready')
  
  if (unassignedOrders) {
    for (const order of unassignedOrders) {
      // Check if it has an accepted job
      const { data: jobs } = await supabase
        .from('status_events')
        .select('id')
        .eq('entity_id', order.id)
        .eq('entity_type', 'order')
        .eq('status', 'partner_accepted')
        .limit(1)

      if (!jobs || jobs.length === 0) {
        insights.push({
          severity: 'MEDIUM',
          category: 'unassigned_ready_order',
          source_table: 'orders',
          source_id: order.id,
          entity_id: order.merchant_id || undefined,
          features: { status: 'ready', has_partner: false },
          explanation: `Order ${order.id.slice(0, 8)} is ready but has no partner assigned.`,
          recommended_action: 'Broadcast to wider partner radius or apply surge incentive.'
        })
      }
    }
  }

  // 3. Demand Surge (from Demand Forecasts)
  const { data: surges } = await supabase
    .from('demand_forecasts')
    .select('*')
    .eq('demand_level', 'HIGH')
    .order('created_at', { ascending: false })
    .limit(10)

  if (surges) {
    for (const surge of surges) {
      insights.push({
        severity: 'MEDIUM',
        category: 'demand_surge',
        source_table: 'demand_forecasts',
        source_id: surge.id,
        features: { zone: surge.zone_name, expected_orders: surge.expected_orders },
        explanation: `High demand forecasted for ${surge.zone_name} (${surge.expected_orders} expected orders).`,
        recommended_action: 'Increase partner incentives in this zone.'
      })
    }
  }

  // 4. Partner Shortage (proxy: fewer partners available than high demand zones)
  // 5. Merchant Delay (from merchant reliability scores)
  const { data: merchants } = await supabase
    .from('merchant_reliability_scores')
    .select('*')
    .lt('reliability_score', 60)
    .order('created_at', { ascending: false })
    .limit(5)

  if (merchants) {
    for (const merchant of merchants) {
      insights.push({
        severity: 'MEDIUM',
        category: 'merchant_delay',
        source_table: 'merchant_reliability_scores',
        source_id: merchant.id,
        entity_id: merchant.merchant_id,
        features: { score: merchant.reliability_score },
        explanation: `Merchant has a low reliability score of ${merchant.reliability_score}, indicating frequent delays or cancellations.`,
        recommended_action: 'Review merchant operational capacity and temporarily throttle order volume.'
      })
    }
  }

  // 6. High Risk Order
  const { data: risks } = await supabase
    .from('risk_checks')
    .select('*')
    .in('risk_level', ['HIGH', 'CRITICAL'])
    .order('created_at', { ascending: false })
    .limit(5)

  if (risks) {
    for (const risk of risks) {
      insights.push({
        severity: 'HIGH',
        category: 'high_risk_order',
        source_table: 'risk_checks',
        source_id: risk.id,
        entity_id: risk.order_id || risk.customer_id,
        features: { risk_score: risk.risk_score, level: risk.risk_level },
        explanation: `Entity ${risk.order_id?.slice(0, 8) || risk.customer_id?.slice(0, 8) || 'Unknown'} flagged as ${risk.risk_level} risk (Score: ${risk.risk_score}).`,
        recommended_action: 'Hold order or suspend user for manual review.'
      })
    }
  }

  // 7. Low Trust Partner
  const { data: partners } = await supabase
    .from('partner_trust_scores')
    .select('*')
    .lt('trust_score', 50)
    .order('created_at', { ascending: false })
    .limit(5)

  if (partners) {
    for (const partner of partners) {
      insights.push({
        severity: 'HIGH',
        category: 'low_trust_partner',
        source_table: 'partner_trust_scores',
        source_id: partner.id,
        entity_id: partner.partner_id,
        features: { trust_score: partner.trust_score },
        explanation: `Partner trust score fell to ${partner.trust_score}. Potential safety or quality issues.`,
        recommended_action: 'Suspend partner pending manual review.'
      })
    }
  }

  // 8. Data Quality Failures
  const { data: dqChecks } = await supabase
    .from('data_quality_results')
    .select('*')
    .eq('status', 'FAIL')
    .order('created_at', { ascending: false })
    .limit(5)

  if (dqChecks) {
    for (const dq of dqChecks) {
      insights.push({
        severity: 'HIGH',
        category: 'data_quality_failure',
        source_table: 'data_quality_results',
        source_id: dq.id,
        features: { check_name: dq.check_name, failure_count: dq.failure_count },
        explanation: `Data Quality Check '${dq.check_name}' failed with ${dq.failure_count} anomalies.`,
        recommended_action: 'Investigate data pipeline integrity immediately.'
      })
    }
  }

  return insights
}
