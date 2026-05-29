-- Create Enums
CREATE TYPE user_role AS ENUM ('customer', 'driver', 'merchant', 'admin');
CREATE TYPE merchant_category AS ENUM ('restaurant', 'grocery', 'retail');
CREATE TYPE service_type AS ENUM ('ride', 'eats', 'grocery', 'courier');
CREATE TYPE order_status AS ENUM ('pending', 'accepted', 'preparing', 'ready', 'in_transit', 'completed', 'cancelled');
CREATE TYPE vehicle_type AS ENUM ('car', 'bike', 'scooter');
CREATE TYPE payment_status AS ENUM ('pending', 'processing', 'succeeded', 'failed', 'refunded');

-- Profiles Table (Extends auth.users)
CREATE TABLE profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  role user_role NOT NULL DEFAULT 'customer',
  full_name TEXT NOT NULL,
  phone TEXT,
  avatar_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Merchants Table
CREATE TABLE merchants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  category merchant_category NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  rating NUMERIC(3, 2) DEFAULT 0.00,
  address_line1 TEXT NOT NULL,
  latitude NUMERIC(10, 7) NOT NULL,
  longitude NUMERIC(10, 7) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Products Table (For Eats, Grocery, Retail)
CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  merchant_id UUID NOT NULL REFERENCES merchants(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  price NUMERIC(10, 2) NOT NULL,
  image_url TEXT,
  is_available BOOLEAN NOT NULL DEFAULT true,
  category TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Vehicles Table
CREATE TABLE vehicles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  driver_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  make TEXT NOT NULL,
  model TEXT NOT NULL,
  plate_number TEXT NOT NULL,
  color TEXT NOT NULL,
  type vehicle_type NOT NULL DEFAULT 'car',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Orders Table (Universal for all services)
CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id UUID NOT NULL REFERENCES profiles(id),
  merchant_id UUID REFERENCES merchants(id), -- Null for rides/courier
  driver_id UUID REFERENCES profiles(id), -- Null until accepted
  service_type service_type NOT NULL,
  status order_status NOT NULL DEFAULT 'pending',
  total_amount NUMERIC(10, 2) NOT NULL,
  pickup_location JSONB NOT NULL, -- {lat, lng, address}
  dropoff_location JSONB NOT NULL, -- {lat, lng, address}
  scheduled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Order Items Table
CREATE TABLE order_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id UUID NOT NULL REFERENCES products(id),
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  price_at_time NUMERIC(10, 2) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Payments Table (Stripe Simulator)
CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  customer_id UUID NOT NULL REFERENCES profiles(id),
  amount NUMERIC(10, 2) NOT NULL,
  status payment_status NOT NULL DEFAULT 'pending',
  stripe_payment_intent_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Driver Status / Tracking Table
CREATE TABLE tracking (
  driver_id UUID PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
  is_online BOOLEAN NOT NULL DEFAULT false,
  current_location JSONB, -- {lat, lng, heading}
  last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_merchants_updated_at BEFORE UPDATE ON merchants FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_vehicles_updated_at BEFORE UPDATE ON vehicles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) Setup
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE merchants ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE tracking ENABLE ROW LEVEL SECURITY;

-- Base Policies (MVP permissive rules for demo purposes, restricted by auth.uid)
CREATE POLICY "Public profiles are viewable by everyone." ON profiles FOR SELECT USING (true);
CREATE POLICY "Users can insert their own profile." ON profiles FOR INSERT WITH CHECK (auth.uid() = id);
CREATE POLICY "Users can update own profile." ON profiles FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Merchants are viewable by everyone." ON merchants FOR SELECT USING (true);
CREATE POLICY "Merchant owners can manage their merchants." ON merchants FOR ALL USING (auth.uid() = owner_id);

CREATE POLICY "Products are viewable by everyone." ON products FOR SELECT USING (true);
CREATE POLICY "Merchant owners can manage products." ON products FOR ALL USING (
  EXISTS (SELECT 1 FROM merchants m WHERE m.id = products.merchant_id AND m.owner_id = auth.uid())
);

CREATE POLICY "Users can view their own vehicles." ON vehicles FOR SELECT USING (auth.uid() = driver_id);
CREATE POLICY "Drivers can manage own vehicles." ON vehicles FOR ALL USING (auth.uid() = driver_id);

CREATE POLICY "Users can view their own orders." ON orders FOR SELECT USING (auth.uid() = customer_id OR auth.uid() = driver_id);
CREATE POLICY "Merchant owners can view their orders." ON orders FOR SELECT USING (
  EXISTS (SELECT 1 FROM merchants m WHERE m.id = orders.merchant_id AND m.owner_id = auth.uid())
);
CREATE POLICY "Customers can create orders." ON orders FOR INSERT WITH CHECK (auth.uid() = customer_id);
CREATE POLICY "Involved parties can update orders." ON orders FOR UPDATE USING (auth.uid() = customer_id OR auth.uid() = driver_id);

CREATE POLICY "Users can view own order items." ON order_items FOR SELECT USING (
  EXISTS (SELECT 1 FROM orders o WHERE o.id = order_items.order_id AND (o.customer_id = auth.uid() OR o.driver_id = auth.uid()))
);
CREATE POLICY "Customers can insert order items." ON order_items FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM orders o WHERE o.id = order_items.order_id AND o.customer_id = auth.uid())
);

CREATE POLICY "Users can view own payments." ON payments FOR SELECT USING (auth.uid() = customer_id);
CREATE POLICY "Customers can insert payments." ON payments FOR INSERT WITH CHECK (auth.uid() = customer_id);

CREATE POLICY "Tracking data is public for active orders." ON tracking FOR SELECT USING (true);
CREATE POLICY "Drivers can update own tracking." ON tracking FOR ALL USING (auth.uid() = driver_id);
