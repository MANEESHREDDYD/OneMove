-- Allow participants to insert their own volunteer orders
CREATE POLICY "Participants can insert own orders" ON volunteer_orders FOR INSERT
WITH CHECK (participant_id = auth.uid());

CREATE POLICY "Participants can read own orders" ON volunteer_orders FOR SELECT
USING (participant_id = auth.uid());

-- Allow participants to insert events for their own orders
CREATE POLICY "Participants can insert own events" ON volunteer_order_events FOR INSERT
WITH CHECK (
  EXISTS (SELECT 1 FROM volunteer_orders WHERE id = order_id AND participant_id = auth.uid())
);

CREATE POLICY "Participants can read own events" ON volunteer_order_events FOR SELECT
USING (
  EXISTS (SELECT 1 FROM volunteer_orders WHERE id = order_id AND participant_id = auth.uid())
);