import { Client } from 'pg'
import dotenv from 'dotenv'
import path from 'path'

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') })

async function fixEnum() {
  const client = new Client({
    connectionString: process.env.DATABASE_URL
  })

  await client.connect()

  const newStatuses = [
    'requested', 'placed', 'created', 'merchant_accepted', 'preparing', 'ready', 'arrived', 'started', 'picked_up'
  ]

  for (const status of newStatuses) {
    try {
      await client.query(`ALTER TYPE order_status ADD VALUE IF NOT EXISTS '${status}'`)
      console.log(`Added ${status} to order_status enum.`)
    } catch (e: any) {
      console.error(`Failed to add ${status}:`, e.message)
    }
  }

  const newPaymentStatuses = [
    'paid_demo', 'pending_demo', 'failed_demo', 'refunded_demo', 'manual_review_demo'
  ]

  for (const status of newPaymentStatuses) {
    try {
      await client.query(`ALTER TYPE payment_status ADD VALUE IF NOT EXISTS '${status}'`)
      console.log(`Added ${status} to payment_status enum.`)
    } catch (e: any) {
      console.error(`Failed to add ${status} to payment_status:`, e.message)
    }
  }

  await client.end()
}

fixEnum().catch(console.error)
