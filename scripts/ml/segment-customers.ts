import { segmentCustomers } from '../../lib/ml/customerSegmentation'

async function main() {
  console.log('--- Running Customer Segmentation Pipeline ---')
  const segments = await segmentCustomers()
  console.log(`✅ Successfully generated segments for ${segments.length} customers.`)
  process.exit(0)
}

main().catch(err => {
  console.error('Pipeline failed:', err)
  process.exit(1)
})
