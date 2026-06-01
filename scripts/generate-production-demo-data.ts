/* eslint-disable @typescript-eslint/no-require-imports */
import { Client } from 'pg';
import { faker } from '@faker-js/faker';
import * as path from 'path';
import * as fs from 'fs';

// Minimal dotenv parsing
const envPath = path.join(process.cwd(), '.env.local');
const envVars: Record<string, string> = {};

if (fs.existsSync(envPath)) {
  const lines = fs.readFileSync(envPath, 'utf-8').split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIdx = trimmed.indexOf('=');
    if (eqIdx === -1) continue;
    const key = trimmed.substring(0, eqIdx).trim();
    let value = trimmed.substring(eqIdx + 1).trim();
    if (value.startsWith('"') && value.endsWith('"')) {
      value = value.substring(1, value.length - 1);
    }
    envVars[key] = value;
  }
}

const directUrl = envVars['DIRECT_URL'];

if (!directUrl) {
  console.error("Missing DIRECT_URL in .env.local");
  process.exit(1);
}

const client = new Client({ connectionString: directUrl });

const args = process.argv.slice(2);
const isDryRun = args.includes('--dry-run');
const isReset = args.includes('--reset');

const SEED_RUN_ID = `demo_run_${Date.now()}`;

// NYC Bounding Box
const NYC_BOUNDS = {
  minLat: 40.6, maxLat: 40.9,
  minLng: -74.05, maxLng: -73.8
};

function randomLocation() {
  return {
    lat: faker.location.latitude({ min: NYC_BOUNDS.minLat, max: NYC_BOUNDS.maxLat }),
    lng: faker.location.longitude({ min: NYC_BOUNDS.minLng, max: NYC_BOUNDS.maxLng }),
    address: faker.location.streetAddress() + ", New York, NY"
  };
}

function randomDateLast30Days() {
  return faker.date.recent({ days: 30 }).toISOString();
}

// Realistic grocery product names
const GROCERY_PRODUCTS = [
  'Organic Bananas', 'Whole Milk 1 Gallon', 'Free Range Eggs (12)', 'Sourdough Bread Loaf',
  'Atlantic Salmon Fillet', 'Baby Spinach 5oz', 'Greek Yogurt Plain', 'Avocados (3 pack)',
  'Chicken Breast Boneless', 'Cheddar Cheese Block', 'Olive Oil Extra Virgin', 'Brown Rice 2lb',
  'Honeycrisp Apples (4)', 'Ground Turkey 93/7', 'Almond Milk Unsweetened', 'Mixed Berries 12oz',
  'Pasta Penne 16oz', 'Marinara Sauce 24oz', 'Fresh Broccoli Crown', 'Sweet Potatoes (3)',
  'Orange Juice 52oz', 'Butter Unsalted', 'Sliced Turkey Deli', 'Tortilla Chips',
  'Hummus Classic', 'Frozen Pizza Margherita', 'Ice Cream Vanilla Pint', 'Sparkling Water (12pk)',
  'Paper Towels 6 Roll', 'Dish Soap'
];

const GROCERY_CATEGORIES = ['Produce', 'Dairy & Eggs', 'Meat & Seafood', 'Bakery', 'Pantry', 'Beverages', 'Frozen', 'Snacks', 'Household', 'Deli'];

// Realistic restaurant menu items
const RESTAURANT_MENUS: Record<string, { items: string[], category: string }> = {
  'American': { items: ['Classic Cheeseburger', 'BBQ Bacon Burger', 'Truffle Fries', 'Caesar Salad', 'Chicken Tenders', 'Milkshake Vanilla', 'Onion Rings', 'Grilled Chicken Sandwich', 'Mac & Cheese', 'Buffalo Wings'], category: 'American' },
  'Italian': { items: ['Margherita Pizza', 'Pepperoni Pizza', 'Pasta Carbonara', 'Lasagna', 'Garlic Bread', 'Tiramisu', 'Bruschetta', 'Fettuccine Alfredo', 'Minestrone Soup', 'Cannoli'], category: 'Italian' },
  'Japanese': { items: ['Spicy Tuna Roll', 'Dragon Roll', 'Miso Soup', 'Edamame', 'Teriyaki Chicken', 'Ramen Tonkotsu', 'Tempura Shrimp', 'Salmon Sashimi', 'Gyoza (6pc)', 'Matcha Ice Cream'], category: 'Japanese' },
  'Mexican': { items: ['Chicken Burrito', 'Steak Tacos (3)', 'Guacamole & Chips', 'Quesadilla', 'Nachos Supreme', 'Churros', 'Elote', 'Carnitas Bowl', 'Chicken Enchiladas', 'Horchata'], category: 'Mexican' },
  'Chinese': { items: ['Kung Pao Chicken', 'Fried Rice', 'Lo Mein', 'Spring Rolls (4)', 'Orange Chicken', 'Wonton Soup', 'General Tso Chicken', 'Dumplings (8)', 'Mapo Tofu', 'Bubble Tea'], category: 'Chinese' },
};

const RESTAURANT_NAMES = [
  'Burger Forge', 'Tokyo Sushi Express', 'Pizza Napoli', 'Green Bowl Co.', 'El Fuego Tacos',
  'Golden Wok', 'The Pasta House', 'Sakura Ramen', 'Smoke & Grill BBQ', 'Fresh Kitchen',
  'Pho Palace', 'Mumbai Bites', 'The Mediterranean Grill', 'Dragon Palace', 'Little Italy Deli',
  'Taco Republic', 'Seoul Kitchen', 'Blue Fin Sushi', 'The Rustic Oven', 'Noodle Bar'
];

const GROCERY_STORE_NAMES = [
  'Fresh Market Plus', 'City Supermarket', 'Corner Deli & Mart', 'Green Grocer NYC',
  'Urban Pantry', 'FreshDirect Express', 'The Local Market', 'Organic Basket',
  'Downtown Grocery', 'Metro Fresh', 'Village Market', 'Brooklyn Bodega',
  'Queens Fresh Mart', 'Harlem Health Foods', 'SoHo Provisions'
];

async function run() {
  await client.connect();
  console.log("✅ Connected to database.");

  if (isDryRun) {
    console.log("\n[DRY RUN MODE]");
    if (isReset) {
      const { rows } = await client.query("SELECT COUNT(*) FROM profiles WHERE is_demo = true");
      console.log(`Would delete ${rows[0].count} demo profiles (and cascading auth.users and all related records).`);
    } else {
      console.log("Would generate 50 customers, 50 partners, 20 restaurants, 15 grocery stores, 200 orders, 500+ products.");
    }
    await client.end();
    return;
  }

  if (isReset) {
    console.log("\n🧹 Resetting existing demo data...");
    const queries = [
      "DELETE FROM ml_score_logs WHERE is_demo = true;",
      "DELETE FROM analytics_events WHERE is_demo = true;",
      "DELETE FROM merchant_payouts WHERE is_demo = true;",
      "DELETE FROM partner_earnings WHERE is_demo = true;",
      "DELETE FROM ratings_reviews WHERE is_demo = true;",
      "DELETE FROM support_tickets WHERE is_demo = true;",
      "DELETE FROM order_status_events WHERE is_demo = true;",
      "DELETE FROM tracking WHERE driver_id IN (SELECT id FROM profiles WHERE is_demo = true);",
      "DELETE FROM payments WHERE is_demo = true;",
      "DELETE FROM order_items WHERE is_demo = true;",
      "DELETE FROM orders WHERE is_demo = true;",
      "DELETE FROM vehicles WHERE is_demo = true;",
      "DELETE FROM products WHERE is_demo = true;",
      "DELETE FROM merchants WHERE is_demo = true;",
      "DELETE FROM auth.users WHERE id IN (SELECT id FROM profiles WHERE is_demo = true);"
    ];
    for (const q of queries) {
      try { await client.query(q); } catch(e) { /* ignore if table doesn't exist */ }
    }
    console.log("✅ Reset complete.");
    await client.end();
    return;
  }

  console.log(`\n🌱 Starting production demo generation [Run ID: ${SEED_RUN_ID}]...`);
  
  // 1. Generate Auth Users and Profiles
  const numCustomers = 50;
  const numPartners = 50;
  const numRestaurantOwners = 20;
  const numGroceryOwners = 15;

  const users: string[] = [];
  const profiles: any[] = [];
  
  const emailTs = Date.now().toString(36);
  
  const generateUsers = (count: number, role: string, prefix: string) => {
    const list = [];
    for (let i = 0; i < count; i++) {
      const id = faker.string.uuid();
      const email = `${prefix}_${emailTs}_${i}@example.com`;
      const encrypted_password = `$2a$10$wT0E8u0nBwK9bO5rL7G/OuJ6z1P7Xp4w9f7Wj4L9vG2e8b6z5r/4O`; // mock hash
      
      users.push(`('${id}', '${id}', 'authenticated', 'authenticated', '${email}', '${encrypted_password}', now(), now(), now(), '{"provider":"email","providers":["email"]}', '{"role":"${role}"}', false, now(), now(), null)`);
      
      profiles.push({id, role, name: faker.person.fullName(), phone: `+1555${String(i).padStart(4, '0')}${Math.floor(Math.random() * 1000)}`});
      list.push(id);
    }
    return list;
  };

  const customerIds = generateUsers(numCustomers, 'customer', 'cust');
  const partnerIds = generateUsers(numPartners, 'driver', 'part');
  const restaurantOwnerIds = generateUsers(numRestaurantOwners, 'merchant', 'rest');
  const groceryOwnerIds = generateUsers(numGroceryOwners, 'merchant', 'groc');

  // Insert Users
  if (users.length > 0) {
    const chunk = 50;
    for(let i=0; i<users.length; i+=chunk) {
      await client.query(`
        INSERT INTO auth.users (instance_id, id, aud, role, email, encrypted_password, email_confirmed_at, recovery_sent_at, last_sign_in_at, raw_app_meta_data, raw_user_meta_data, is_super_admin, created_at, updated_at, phone)
        VALUES ${users.slice(i, i+chunk).join(',')}
        ON CONFLICT (id) DO NOTHING
      `);
    }
    // Profiles are created by trigger. Update them with demo fields.
    for(let i=0; i<profiles.length; i++) {
      const p = profiles[i];
      await client.query(`UPDATE profiles SET full_name = $1, phone = $2, role = $3, is_demo = true, seed_run_id = $4 WHERE id = $5`, [p.name, p.phone, p.role, SEED_RUN_ID, p.id]);
    }
  }

  console.log(`  ✅ Users: ${users.length} (${numCustomers} customers, ${numPartners} partners, ${numRestaurantOwners + numGroceryOwners} merchants)`);

  // 2. Generate Restaurants (20)
  const restaurantMerchantIds: { id: string, cuisine: string }[] = [];
  const restaurantRows: string[] = [];
  const productRows: string[] = [];
  
  const cuisines = Object.keys(RESTAURANT_MENUS);
  
  for (let i = 0; i < numRestaurantOwners; i++) {
    const id = faker.string.uuid();
    const cuisine = cuisines[i % cuisines.length];
    const name = RESTAURANT_NAMES[i % RESTAURANT_NAMES.length];
    const loc = randomLocation();
    const rating = faker.number.float({min: 3.5, max: 5.0, fractionDigits: 1});
    const desc = `${cuisine} cuisine • Free delivery over $25`;
    
    restaurantMerchantIds.push({ id, cuisine });
    restaurantRows.push(`('${id}', '${restaurantOwnerIds[i]}', '${name.replace(/'/g, "''")}', '${desc.replace(/'/g, "''")}', 'restaurant', 'active', ${rating}, '${loc.address.replace(/'/g, "''")}', ${loc.lat}, ${loc.lng}, true, '${SEED_RUN_ID}')`);
    
    // Generate menu items for this restaurant
    const menuData = RESTAURANT_MENUS[cuisine];
    for (let j = 0; j < menuData.items.length; j++) {
      const price = faker.number.float({min: 5, max: 30, fractionDigits: 2});
      productRows.push(`('${faker.string.uuid()}', '${id}', '${menuData.items[j].replace(/'/g, "''")}', '${menuData.category} specialty', ${price}, null, true, '${menuData.category}', true, '${SEED_RUN_ID}')`);
    }
  }

  // 3. Generate Grocery Stores (15)
  const groceryMerchantIds: string[] = [];
  
  for (let i = 0; i < numGroceryOwners; i++) {
    const id = faker.string.uuid();
    const name = GROCERY_STORE_NAMES[i % GROCERY_STORE_NAMES.length];
    const loc = randomLocation();
    const rating = faker.number.float({min: 3.5, max: 5.0, fractionDigits: 1});
    const desc = `Fresh groceries & essentials • 30-50 min delivery`;
    
    groceryMerchantIds.push(id);
    restaurantRows.push(`('${id}', '${groceryOwnerIds[i]}', '${name.replace(/'/g, "''")}', '${desc.replace(/'/g, "''")}', 'grocery', 'active', ${rating}, '${loc.address.replace(/'/g, "''")}', ${loc.lat}, ${loc.lng}, true, '${SEED_RUN_ID}')`);
    
    // Generate grocery products
    for (let j = 0; j < GROCERY_PRODUCTS.length; j++) {
      const price = faker.number.float({min: 0.99, max: 15.99, fractionDigits: 2});
      const cat = GROCERY_CATEGORIES[j % GROCERY_CATEGORIES.length];
      productRows.push(`('${faker.string.uuid()}', '${id}', '${GROCERY_PRODUCTS[j].replace(/'/g, "''")}', '${cat}', ${price}, null, true, '${cat}', true, '${SEED_RUN_ID}')`);
    }
  }

  if (restaurantRows.length > 0) {
    await client.query(`INSERT INTO merchants (id, owner_id, name, description, category, status, rating, address_line1, latitude, longitude, is_demo, seed_run_id) VALUES ${restaurantRows.join(',')}`);
  }
  
  if (productRows.length > 0) {
    const chunk = 200;
    for(let i=0; i<productRows.length; i+=chunk) {
      await client.query(`INSERT INTO products (id, merchant_id, name, description, price, image_url, is_available, category, is_demo, seed_run_id) VALUES ${productRows.slice(i, i+chunk).join(',')}`);
    }
  }

  console.log(`  ✅ Merchants: ${restaurantRows.length} (${restaurantMerchantIds.length} restaurants, ${groceryMerchantIds.length} grocery stores)`);
  console.log(`  ✅ Products: ${productRows.length}`);

  // 4. Generate Vehicles
  const vehicles: string[] = [];
  for (const pid of partnerIds) {
    vehicles.push(`('${faker.string.uuid()}', '${pid}', '${faker.vehicle.manufacturer()}', '${faker.vehicle.model()}', '${faker.vehicle.vrm()}', '${faker.vehicle.color()}', '${faker.helpers.arrayElement(['car', 'bike', 'scooter'])}', true, '${SEED_RUN_ID}')`);
  }
  if (vehicles.length > 0) {
    await client.query(`INSERT INTO vehicles (id, driver_id, make, model, plate_number, color, type, is_demo, seed_run_id) VALUES ${vehicles.join(',')}`);
  }
  console.log(`  ✅ Vehicles: ${vehicles.length}`);

  // 5. Generate Orders
  const orders: string[] = [];
  const payments: string[] = [];
  const allOrderItems: string[] = [];
  const analytics: string[] = [];
  const mlLogs: string[] = [];

  const createOrder = async (service: string, merchantId: string | null) => {
    const id = faker.string.uuid();
    const custId = faker.helpers.arrayElement(customerIds);
    const partId = faker.datatype.boolean({ probability: 0.8 }) ? faker.helpers.arrayElement(partnerIds) : null;
    const merchIdStr = merchantId ? `'${merchantId}'` : 'null';
    const driverIdStr = partId ? `'${partId}'` : 'null';
    
    const status = faker.helpers.arrayElement(['completed', 'completed', 'completed', 'in_transit', 'pending', 'cancelled']);
    const amount = faker.number.float({min: 15, max: 200, fractionDigits: 2});
    const date = randomDateLast30Days();
    
    const pickup = JSON.stringify(randomLocation()).replace(/'/g, "''");
    const dropoff = JSON.stringify(randomLocation()).replace(/'/g, "''");

    orders.push(`('${id}', '${custId}', ${merchIdStr}, ${driverIdStr}, '${service}', '${status}', ${amount}, '${pickup}', '${dropoff}', true, '${SEED_RUN_ID}', '${date}')`);

    payments.push(`('${faker.string.uuid()}', '${id}', '${custId}', ${amount}, '${status === 'cancelled' ? 'refunded' : 'succeeded'}', 'card', true, '${SEED_RUN_ID}', '${date}')`);
    
    analytics.push(`('${faker.string.uuid()}', 'order_placed', '${custId}', '{"service": "${service}"}', true, '${SEED_RUN_ID}', '${date}')`);
    
    mlLogs.push(`('${faker.string.uuid()}', 'dispatch_score', '${id}', ${faker.number.float({min: 60, max: 100, fractionDigits: 1})}, '{}', true, '${SEED_RUN_ID}', '${date}')`);

    // Order items for food/grocery orders
    if (merchantId) {
      const { rows } = await client.query(`SELECT id, price FROM products WHERE merchant_id = '${merchantId}' LIMIT 5`);
      for (const r of rows) {
        allOrderItems.push(`('${faker.string.uuid()}', '${id}', '${r.id}', ${faker.number.int({min: 1, max: 4})}, ${r.price}, true, '${SEED_RUN_ID}', '${date}')`);
      }
    }
  };

  // 50 rides
  for(let i=0; i<50; i++) await createOrder('ride', null);
  // 50 eats orders  
  for(let i=0; i<50; i++) await createOrder('eats', restaurantMerchantIds[i % restaurantMerchantIds.length].id);
  // 50 grocery orders
  for(let i=0; i<50; i++) await createOrder('grocery', groceryMerchantIds[i % groceryMerchantIds.length]);
  // 50 courier
  for(let i=0; i<50; i++) await createOrder('courier', null);

  if (orders.length > 0) {
    await client.query(`INSERT INTO orders (id, customer_id, merchant_id, driver_id, service_type, status, total_amount, pickup_location, dropoff_location, is_demo, seed_run_id, created_at) VALUES ${orders.join(',')}`);
  }
  if (payments.length > 0) {
    await client.query(`INSERT INTO payments (id, order_id, customer_id, amount, status, method, is_demo, seed_run_id, created_at) VALUES ${payments.join(',')}`);
  }
  if (allOrderItems.length > 0) {
    const chunk = 500;
    for(let i=0; i<allOrderItems.length; i+=chunk) {
      await client.query(`INSERT INTO order_items (id, order_id, product_id, quantity, price_at_time, is_demo, seed_run_id, created_at) VALUES ${allOrderItems.slice(i, i+chunk).join(',')}`);
    }
  }
  if (analytics.length > 0) {
    await client.query(`INSERT INTO analytics_events (id, event_type, user_id, metadata, is_demo, seed_run_id, created_at) VALUES ${analytics.join(',')}`);
  }
  if (mlLogs.length > 0) {
    await client.query(`INSERT INTO ml_score_logs (id, score_type, target_id, score_value, metadata, is_demo, seed_run_id, created_at) VALUES ${mlLogs.join(',')}`);
  }

  console.log(`  ✅ Orders: ${orders.length} (50 rides, 50 eats, 50 grocery, 50 courier)`);
  console.log(`  ✅ Order Items: ${allOrderItems.length}`);
  console.log(`  ✅ Payments: ${payments.length}`);
  console.log(`  ✅ Analytics Events: ${analytics.length}`);
  console.log(`  ✅ ML Score Logs: ${mlLogs.length}`);

  console.log(`\n✅ Demo data generation complete.`);
  
  await client.end();
}

run().catch(err => {
  console.error(err);
  process.exit(1);
});
