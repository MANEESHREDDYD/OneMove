# Supabase Setup Guide

This guide covers the complete step-by-step process for setting up the Supabase database for the OneMove project.

## 1. Create Supabase Project

1. Go to [Supabase](https://supabase.com).
2. Create a free account or log in.
3. Click **New Project**.
4. Set the project name to **OneMove**.
5. Choose the **Free tier**.
6. Select the **closest region** to you.
7. Set a strong **Database Password** and **save it safely**.
8. Wait a few minutes for the project to finish provisioning.

## 2. Get API Keys

Once the project is ready:
1. Go to **Project Settings** (the gear icon) → **API**.
2. Locate your **Project URL** and copy it.
3. Locate the **Project API keys** and copy the `anon` / `public` key.
4. Locate the `service_role` key and copy it.

**IMPORTANT KEY MAPPING:**
* `NEXT_PUBLIC_SUPABASE_URL` = Supabase Project URL
* `NEXT_PUBLIC_SUPABASE_ANON_KEY` = Supabase `anon` / `public` key
* `SUPABASE_SERVICE_ROLE_KEY` = Supabase `service_role` key

> [!WARNING]
> * Never commit `.env.local`.
> * Never expose `SUPABASE_SERVICE_ROLE_KEY` in browser/client code.
> * Only use the service role key server-side.

## 3. Set Up Local Environment

You need to map the copied keys to a local `.env.local` file.

**Windows PowerShell:**
```powershell
Copy-Item .env.local.example .env.local
notepad .env.local
```

**Mac/Linux:**
```bash
cp .env.local.example .env.local
nano .env.local
```

Replace the placeholder values with the exact keys you copied from the Supabase dashboard. Your file should look like this:
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhb...
SUPABASE_SERVICE_ROLE_KEY=eyJhb...
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_DEFAULT_REGION=US
NEXT_PUBLIC_DEFAULT_CITY=NYC
```

## 4. How to apply SQL in Supabase

Next, you need to apply the database schema. 

1. Go to **Supabase Dashboard** → **SQL Editor** → **New Query**.
2. Run the SQL files from the `supabase/` directory **in the exact order below**.

For each file:
* Copy all SQL from the file.
* Paste it into the SQL Editor.
* Click **Run**.
* Confirm there are no errors in the results panel.
* Continue to the next file.

**Execution Order:**
1. `supabase/schema.sql`
2. `supabase/functions.sql`
3. `supabase/views.sql`
4. `supabase/policies.sql`
5. `supabase/seed.sql`

## 5. Create Demo Auth Users

Because Supabase Auth relies on cryptographically hashed passwords and encrypted fields, SQL alone cannot easily mock working login accounts with known passwords.

Option A: Run the server-side auth seed script.
```bash
npm run seed:auth
```
*(Requires `ts-node` and valid `.env.local` keys. This creates the users and assigns them the required roles and database merchant rows).*

Option B: Manual Creation in Dashboard.
1. Go to **Supabase Dashboard** → **Authentication** → **Users** → **Add User**.
2. Create the following four users exactly:
   * `customer@onemove.demo` / `Demo@12345`
   * `partner@onemove.demo` / `Demo@12345`
   * `merchant@onemove.demo` / `Demo@12345`
   * `admin@onemove.demo` / `Demo@12345`

*(Note: Creating them manually will give them random UUIDs, so the `merchant@onemove.demo` user will not be assigned a merchant profile by the SQL seed script. Running Option A (`npm run seed:auth`) is recommended for the most complete local experience).*

## 6. (Optional) Supabase CLI Setup

If you prefer to use the Supabase CLI instead of the dashboard, you can push the schema directly:

```bash
supabase login
supabase link --project-ref YOUR_PROJECT_REF
supabase db push
```
*(This assumes you have placed the SQL files into `supabase/migrations` and configured the CLI. The primary method should be the Supabase Dashboard SQL Editor).*

## 7. Next Steps

After completing this setup, refer to `docs/SUPABASE_VERIFICATION.md` to ensure everything is working perfectly.
