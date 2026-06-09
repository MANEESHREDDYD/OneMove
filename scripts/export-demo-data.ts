import fs from 'fs';
import path from 'path';

async function exportDemoData() {
    console.log("Exporting synthetic demo data...");
    const dir = path.join(process.cwd(), 'data/demo_exports');
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
    
    // Write synthetic dummy CSVs
    fs.writeFileSync(path.join(dir, 'customers_sample.csv'), 'customer_id,email,signup_date\nCUST-001,synth1@example.com,2026-01-01\nCUST-002,synth2@example.com,2026-02-01\n');
    fs.writeFileSync(path.join(dir, 'merchants_sample.csv'), 'merchant_id,name,category\nMERCH-001,Burger Joint,Food\n');
    fs.writeFileSync(path.join(dir, 'partners_sample.csv'), 'partner_id,vehicle_type,rating\nPART-001,Car,4.9\n');
    fs.writeFileSync(path.join(dir, 'orders_sample.csv'), 'order_id,customer_id,total_amount,status\nORD-001,CUST-001,25.50,COMPLETED\n');
    fs.writeFileSync(path.join(dir, 'payments_sample.csv'), 'payment_id,order_id,amount,status\nPAY-001,ORD-001,25.50,SUCCESS\n');
    fs.writeFileSync(path.join(dir, 'order_items_sample.csv'), 'item_id,order_id,name,price\nITEM-001,ORD-001,Burger,25.50\n');
    fs.writeFileSync(path.join(dir, 'status_events_sample.csv'), 'event_id,order_id,status,timestamp\nEVT-001,ORD-001,COMPLETED,2026-06-01T12:00:00Z\n');
    
    console.log("Export complete.");
}

exportDemoData().catch(console.error);
