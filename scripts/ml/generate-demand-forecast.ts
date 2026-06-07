import { generateDemandForecast } from '../../lib/ml/demandForecast'

async function main() {
  console.log('--- Running Demand Forecast Engine ---')
  try {
    const forecasts = await generateDemandForecast()
    console.log(`Successfully generated ${forecasts.length} forecasts.`)
    console.table(forecasts.map(f => ({
      Zone: f.zone_name,
      Level: f.predicted_demand_level,
      ExpectedOrders: f.expected_orders_next_hour,
      Confidence: f.confidence_score
    })))
  } catch (err) {
    console.error('Failed to run demand forecast:', err)
  }
}

main()
