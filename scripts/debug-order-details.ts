 
import { Client } from 'pg';
import dotenv from 'dotenv';
import path from 'path';

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

async function checkOrderDetails() {
  const client = new Client({ connectionString: process.env.DIRECT_URL });
  await client.connect();

  console.log('======================================================================');
  console.log('DEBUG: ORDER DETAILS JOINS & REFERENTIAL INTEGRITY');
  console.log('======================================================================');

  // Verify that an order detail page can correctly fetch an order WITH its merchant, customer, and items
  const query = `
    SELECT 
      o.id, 
      o.service_type,
      o.status,
      m.name as merchant_name,
      p.full_name as customer_name,
      (SELECT COUNT(*) FROM order_items oi WHERE oi.order_id = o.id) as item_count,
      (SELECT COUNT(*) FROM payments pay WHERE pay.order_id = o.id) as payment_count
    FROM orders o
    LEFT JOIN merchants m ON o.merchant_id = m.id
    LEFT JOIN profiles p ON o.customer_id = p.id
    WHERE o.is_demo = true
    LIMIT 20
  `;

  try {
    const { rows } = await client.query(query);
    
    let badJoins = 0;
    console.log(`Auditing ${rows.length} sample orders for valid joins:`);
    for (const row of rows) {
      const needsMerchant = ['eats', 'grocery'].includes(row.service_type);
      const isMissingMerchant = needsMerchant && !row.merchant_name;
      const isMissingCustomer = !row.customer_name;
      const isMissingPayment = parseInt(row.payment_count, 10) === 0;
      const isMissingItems = needsMerchant && parseInt(row.item_count, 10) === 0;

      if (isMissingMerchant || isMissingCustomer || isMissingPayment || isMissingItems) {
        badJoins++;
        console.error(`❌ Order ${row.id.substring(0,8)} [${row.service_type}]: Failed relational constraint checks.`);
        if (isMissingMerchant) console.error('   -> Missing Merchant Join');
        if (isMissingCustomer) console.error('   -> Missing Customer Join');
        if (isMissingPayment) console.error('   -> Missing Payment Record');
        if (isMissingItems) console.error('   -> Missing Order Items (Eats/Grocery requires items)');
      } else {
        console.log(`✅ Order ${row.id.substring(0,8)} [${row.service_type}]: Fully resolved relationships.`);
      }
    }

    if (badJoins > 0) {
      console.error(`\n❌ Validation Failed: ${badJoins} orders are disconnected or orphaned. Details pages will crash or show empty states.`);
      process.exit(1);
    } else {
      console.log('\n✅ Details relationships validated.');
    }
  } catch (e: any) {
    console.error(`❌ Failed to query order details: ${e.message}`);
    process.exit(1);
  } finally {
    await client.end();
  }
}

checkOrderDetails().catch(console.error);
