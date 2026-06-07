import { scoreMerchantReliability } from '../../lib/ml/merchantReliability'

async function main() {
  console.log('--- Running Merchant Reliability Pipeline ---')
  const scores = await scoreMerchantReliability()
  console.log(`✅ Successfully scored ${scores.length} merchants.`)
  process.exit(0)
}

main().catch(err => {
  console.error('Pipeline failed:', err)
  process.exit(1)
})
