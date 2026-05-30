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
