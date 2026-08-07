# 10 SECURITY FINDINGS

## P0 FINDINGS: CRITICAL SECURITY & DATA INTEGRITY RISKS

### 1. Privilege Escalation via User Metadata (Insecure RPC)
- **Vulnerability**: In `supabase/functions.sql`, the `handle_new_user()` trigger sets the user role based on unverified input from `new.raw_user_meta_data->>'role'`. 
- **Impact**: Any user can sign up and pass `{"role": "admin"}` in their metadata, immediately granting them administrative privileges across the application.

### 2. Privilege Escalation via Profile Updates
- **Vulnerability**: The RLS policy `"Users can update own profile."` on the `profiles` table allows users to update any column of their own row (`FOR UPDATE USING (auth.uid() = id)`).
- **Impact**: Even if a user signs up as a customer, they can execute an update query to change their `role` column to `'admin'` or `'merchant'`. Column-level restrictions or a restricted `WITH CHECK` are required.

### 3. Financial Manipulation via Insecure Order Updates
- **Vulnerability**: The policy `"Involved parties can update orders."` on the `orders` table allows customers or drivers to perform uncontrolled `UPDATE` operations (`USING (auth.uid() = customer_id OR auth.uid() = driver_id)`).
- **Impact**: A customer or driver can arbitrarily change the `total_amount` to $0, modify the `status` to bypass payments, or tamper with the metadata. 

### 4. Cross-Tenant PII Leakage (Profiles)
- **Vulnerability**: The policy `"Profiles are viewable by authenticated users."` grants universal read access to the `profiles` table (`FOR SELECT USING (auth.role() = 'authenticated')`).
- **Impact**: Any authenticated user can scrape the entire user base's real names, roles, and phone numbers.

### 5. Mass Location Data Leakage (Tracking)
- **Vulnerability**: The policy `"Tracking data is public for active orders."` on the `tracking` table is extremely permissive (`FOR SELECT USING (true)`).
- **Impact**: Unauthenticated (public) users can query the real-time locations (`current_location`) of all active drivers, representing a significant privacy and safety risk.

## CONCLUSION
The current Database RLS layer provides only UI-level isolation. It is highly vulnerable to privilege escalation, data scraping, and financial manipulation via direct API calls. These policies must be rewritten before any public production deployment or real monetary transactions occur.
