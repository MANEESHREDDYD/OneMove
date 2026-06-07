import { scorePartnerTrust } from '../../lib/ml/partnerTrustScore'

async function main() {
  console.log('--- Running Partner Trust Pipeline ---')
  const scores = await scorePartnerTrust()
  console.log(`✅ Successfully scored ${scores.length} partners.`)
  process.exit(0)
}

main().catch(err => {
  console.error('Pipeline failed:', err)
  process.exit(1)
})
