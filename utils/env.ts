/**
 * Environment Variable Validation System for OneMove
 * 
 * This module provides a centralized, fail-fast validation layer for all
 * required environment variables. It prevents cryptic runtime crashes by
 * providing clear, developer-friendly error messages when configuration
 * is missing or invalid.
 */

type EnvVar = {
  key: string
  required: boolean
  /** If true, this var is only required server-side (not exposed to browser) */
  serverOnly?: boolean
  /** Optional validation function */
  validate?: (value: string) => string | null
}

const PLACEHOLDER_VALUES = [
  'your-project-url',
  'your-anon-key',
  'your-service-role-key',
  'YOUR_SUPABASE_URL',
  'YOUR_ANON_KEY',
  'placeholder',
  'CHANGE_ME',
  'xxx',
]

function isPlaceholder(value: string): boolean {
  return PLACEHOLDER_VALUES.some(p => value.toLowerCase().includes(p.toLowerCase()))
}

function validateSupabaseUrl(value: string): string | null {
  if (isPlaceholder(value)) {
    return 'NEXT_PUBLIC_SUPABASE_URL contains a placeholder value. Replace it with your real Supabase project URL from: Supabase Dashboard → Project Settings → API.'
  }
  try {
    const url = new URL(value)
    if (!url.hostname.includes('supabase')) {
      return 'NEXT_PUBLIC_SUPABASE_URL does not appear to be a valid Supabase URL. Expected format: https://<project-ref>.supabase.co'
    }
  } catch {
    return 'NEXT_PUBLIC_SUPABASE_URL is not a valid URL. Expected format: https://<project-ref>.supabase.co'
  }
  return null
}

function validateSupabaseKey(value: string): string | null {
  if (isPlaceholder(value)) {
    return 'NEXT_PUBLIC_SUPABASE_ANON_KEY contains a placeholder value. Replace it with your real anon key from: Supabase Dashboard → Project Settings → API.'
  }
  if (value.length < 30) {
    return 'NEXT_PUBLIC_SUPABASE_ANON_KEY appears too short to be a valid Supabase anon key.'
  }
  return null
}

const ENV_VARS: EnvVar[] = [
  {
    key: 'NEXT_PUBLIC_SUPABASE_URL',
    required: true,
    validate: validateSupabaseUrl,
  },
  {
    key: 'NEXT_PUBLIC_SUPABASE_ANON_KEY',
    required: true,
    validate: validateSupabaseKey,
  },
  {
    key: 'SUPABASE_SERVICE_ROLE_KEY',
    required: false,
    serverOnly: true,
  },
  {
    key: 'NEXT_PUBLIC_APP_URL',
    required: false,
  },
  {
    key: 'NEXT_PUBLIC_DEFAULT_REGION',
    required: false,
  },
  {
    key: 'NEXT_PUBLIC_DEFAULT_CITY',
    required: false,
  },
]

export type EnvValidationResult = {
  valid: boolean
  errors: string[]
  warnings: string[]
}

/**
 * Validates all required environment variables.
 * Returns a result object with errors and warnings.
 */
export function validateEnv(): EnvValidationResult {
  const errors: string[] = []
  const warnings: string[] = []

  for (const envVar of ENV_VARS) {
    const value = process.env[envVar.key]

    if (!value || value.trim() === '') {
      if (envVar.required) {
        errors.push(
          `Missing required environment variable: ${envVar.key}\n` +
          `  → Add it to your .env.local file.\n` +
          `  → See .env.local.example for the expected format.\n` +
          (envVar.key.includes('SUPABASE')
            ? `  → Get this value from: Supabase Dashboard → Project Settings → API.\n`
            : '')
        )
      } else {
        warnings.push(`Optional environment variable not set: ${envVar.key}`)
      }
      continue
    }

    if (envVar.validate) {
      const error = envVar.validate(value)
      if (error) {
        errors.push(error)
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  }
}

/**
 * Returns true if the critical Supabase env vars are present and non-empty.
 * This is a lightweight check used at runtime to decide whether to
 * create a Supabase client or show a setup screen.
 */
export function hasSupabaseConfig(): boolean {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  return Boolean(url && url.trim() !== '' && key && key.trim() !== '')
}

/**
 * Returns a developer-friendly error message for missing Supabase config.
 */
export function getMissingEnvMessage(): string {
  return [
    '╔══════════════════════════════════════════════════════════════╗',
    '║           OneMove: Environment Configuration Missing        ║',
    '╠══════════════════════════════════════════════════════════════╣',
    '║                                                             ║',
    '║  Your .env.local file is missing or incomplete.             ║',
    '║                                                             ║',
    '║  Required variables:                                        ║',
    '║    NEXT_PUBLIC_SUPABASE_URL=https://<ref>.supabase.co       ║',
    '║    NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-anon-key>            ║',
    '║                                                             ║',
    '║  Steps:                                                     ║',
    '║    1. Copy .env.local.example to .env.local                 ║',
    '║    2. Go to: Supabase Dashboard → Project Settings → API    ║',
    '║    3. Copy your Project URL and anon/public key             ║',
    '║    4. Paste them into .env.local                            ║',
    '║    5. Restart the dev server: npm run dev                   ║',
    '║                                                             ║',
    '║  For detailed instructions, see: docs/LOCAL_SETUP.md        ║',
    '║                                                             ║',
    '╚══════════════════════════════════════════════════════════════╝',
  ].join('\n')
}
