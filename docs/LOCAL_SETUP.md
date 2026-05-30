# OneMove: Local Development Setup Guide

This guide walks you through setting up OneMove on your local machine from scratch.

## Prerequisites

- **Node.js**: v20.x or later
- **npm**: v10.x or later
- **Git**: Latest version
- **Supabase Account**: Free tier at [supabase.com](https://supabase.com)

## Step 1: Clone the Repository

```bash
git clone https://github.com/MANEESHREDDYD/OneMove.git
cd OneMove
```

## Step 2: Install Dependencies

```bash
npm install
```

## Step 3: Configure Environment Variables

### 3a. Create your `.env.local` file

```bash
cp .env.local.example .env.local
```

### 3b. Get your Supabase credentials

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project (or create a new one)
3. Navigate to **Project Settings → API**
4. Copy the following values:

| Dashboard Field | Environment Variable |
|---|---|
| **Project URL** | `NEXT_PUBLIC_SUPABASE_URL` |
| **anon / public** key | `NEXT_PUBLIC_SUPABASE_ANON_KEY` |
| **service_role** key (optional) | `SUPABASE_SERVICE_ROLE_KEY` |

### 3c. Fill in your `.env.local`

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIs...your-anon-key...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIs...your-service-key...
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_DEFAULT_REGION=US
NEXT_PUBLIC_DEFAULT_CITY=NYC
```

> **⚠️ NEVER commit `.env.local` to version control.** It is already listed in `.gitignore`.

> **⚠️ NEVER expose `SUPABASE_SERVICE_ROLE_KEY` to the frontend.** Only use it in server-side code.

## Step 4: Validate Your Environment

Run the preflight check to verify your configuration:

```bash
npm run validate:env
```

This will check:
- ✅ `.env.local` file exists
- ✅ Supabase URL format is valid
- ✅ Anon key exists and is not a placeholder
- ✅ App URL is configured
- ✅ No placeholder values are present

If any checks fail, the script will tell you exactly what to fix.

## Step 5: Set Up the Database

Run the SQL seed file to create the required tables in your Supabase project:

1. Go to your Supabase Dashboard → **SQL Editor**
2. Open and run the contents of `supabase/seed.sql`

Or use the CLI:

```bash
npm run seed:demo
```

## Step 6: Start the Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Step 7: Run the Full QA Pipeline (Optional)

```bash
npm run lint          # ESLint checks
npm run typecheck     # TypeScript strict checks
npm run build         # Production build verification
npm run validate:env  # Environment variable checks
```

Or run the full preflight in one command:

```bash
npm run preflight
```

## Available Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start development server |
| `npm run build` | Create production build |
| `npm run start` | Start production server |
| `npm run lint` | Run ESLint |
| `npm run typecheck` | TypeScript strict check |
| `npm run validate:env` | Validate environment variables |
| `npm run preflight` | Full validation (env + lint + typecheck + build) |
| `npm run seed:demo` | Seed demo data into Supabase |

## Troubleshooting

### "Your project's URL and Key are required to create a Supabase client!"

This means your `.env.local` is missing or the Supabase variables are empty. Follow Steps 3-4 above.

### The app shows a "Setup Required" screen

Same cause as above. The app now shows a friendly setup screen instead of crashing. Follow the instructions on the screen.

### "supabase" command not found

Install the Supabase CLI: `npm install -g supabase`

### Build fails with TypeScript errors

Run `npm run typecheck` to see detailed error output, then fix the reported issues.

## Security Checklist

- [ ] `.env.local` is NOT committed to Git
- [ ] `SUPABASE_SERVICE_ROLE_KEY` is only used in server-side code
- [ ] All admin routes are protected by middleware role checks
- [ ] RLS (Row Level Security) is enabled on all Supabase tables
