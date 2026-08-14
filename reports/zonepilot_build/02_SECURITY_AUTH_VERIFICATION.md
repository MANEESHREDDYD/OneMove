# 02 SECURITY & AUTH VERIFICATION

## Execution Log

```text
> node tests/test_fr2_security.js

--- STARTING FR-2 SECURITY TESTS ---

1. Testing role minting via signup...
Profile: { role: 'customer' }
ProfileErr: null
[PASS] User created with customer role despite admin metadata injection

2. Testing cross-tenant profile reads...
All Profiles: [
  {
    id: '7aec2909-4b7e-40bc-9a24-9f6a47232648',
    role: 'customer',
    full_name: 'Hacker User',
    phone: null,
    avatar_url: null,
    created_at: '2026-08-07T17:27:27.607519+00:00',
    updated_at: '2026-08-07T17:27:27.607519+00:00'
  }
]
[PASS] Ordinary user can only read their own profile

3. Testing privilege escalation via UPDATE...
[PASS] Ordinary user blocked from updating own role to admin

4. Testing tracking visibility...
Tracking Data: []
[PASS] Tracking data is not globally readable by default customer

5. Testing financial mutations...
[PASS] User blocked from altering order total_amount

--- RESULTS: 5 Passed, 0 Failed ---
```

## Before/After Security Model

- **Before**: 
  - `auth_trigger.sql` blindly accepted `new.raw_user_meta_data->>'role'` allowing anyone to sign up as an admin.
  - Profile tracking data was completely public via permissive RLS policies.
  - Profiles could be read cross-tenant via a simple `USING (true)` policy.
  - Orders had loose financial constraints where parties could mutate fields arbitrarily.
- **After**:
  - `auth_trigger.sql` securely hardcodes the `customer` role for all new signups, ignoring injected metadata. Role elevation requires an existing admin or a privileged machine job.
  - Added a `SECURITY DEFINER` function `public.is_admin()` and replaced naive recursive RLS policies on `profiles` to strictly limit cross-tenant reads while avoiding infinite loop execution paths.
  - Financial mutation of orders (`total_amount`) by customers/riders is strictly blocked via a `WITH CHECK` constraint ensuring they can only update operational fields.
  - Tracking data is locked behind RLS limited to the participant themselves or an authorized administrator/study-owner.

## Human vs Machine Access
- All human sessions use user JWTs and are subject to Postgres RLS.
- Only the secret machine client has Service Role access for collectors and migration tasks.

## Unresolved Risks
- **None block Experiment A.** ZonePilot data collection paths are now properly isolated.
- **Environment Status**: Local Supabase running flawlessly. Remote environment blocked until deployment phase.
