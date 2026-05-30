#!/usr/bin/env node

/**
 * OneMove Preflight Environment Validator
 * 
 * Validates that all required environment variables are set and valid
 * before allowing a build or deployment to proceed.
 * 
 * Usage: npm run validate:env
 */

/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require('fs')
const path = require('path')

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

function isPlaceholder(value) {
  return PLACEHOLDER_VALUES.some(p => value.toLowerCase().includes(p.toLowerCase()))
}

// Load .env.local manually since this runs outside Next.js
const envPath = path.join(process.cwd(), '.env.local')
const envVars = {}

if (fs.existsSync(envPath)) {
  const lines = fs.readFileSync(envPath, 'utf-8').split('\n')
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eqIdx = trimmed.indexOf('=')
    if (eqIdx === -1) continue
    const key = trimmed.substring(0, eqIdx).trim()
    const value = trimmed.substring(eqIdx + 1).trim()
    envVars[key] = value
  }
}

const errors = []
const warnings = []
const passes = []

console.log('')
console.log('╔══════════════════════════════════════════════════╗')
console.log('║        OneMove Preflight Environment Check       ║')
console.log('╚══════════════════════════════════════════════════╝')
console.log('')

// Check 1: .env.local file exists
if (!fs.existsSync(envPath)) {
  errors.push('.env.local file not found. Copy .env.local.example to .env.local and fill in your values.')
} else {
  passes.push('.env.local file exists')
}

// Check 2: NEXT_PUBLIC_SUPABASE_URL
const supabaseUrl = envVars['NEXT_PUBLIC_SUPABASE_URL'] || ''
if (!supabaseUrl) {
  errors.push('NEXT_PUBLIC_SUPABASE_URL is missing or empty.')
} else if (isPlaceholder(supabaseUrl)) {
  errors.push('NEXT_PUBLIC_SUPABASE_URL contains a placeholder value. Replace with your real URL.')
} else {
  try {
    const url = new URL(supabaseUrl)
    if (url.protocol !== 'https:') {
      errors.push('NEXT_PUBLIC_SUPABASE_URL must start with https://')
    } else if (!url.hostname.includes('supabase.co')) {
      errors.push('NEXT_PUBLIC_SUPABASE_URL must contain supabase.co')
    } else {
      passes.push('NEXT_PUBLIC_SUPABASE_URL is a valid Supabase URL')
    }
  } catch {
    errors.push('NEXT_PUBLIC_SUPABASE_URL is not a valid URL.')
  }
}

// Check 3: NEXT_PUBLIC_SUPABASE_ANON_KEY
const anonKey = envVars['NEXT_PUBLIC_SUPABASE_ANON_KEY'] || ''
if (!anonKey) {
  errors.push('NEXT_PUBLIC_SUPABASE_ANON_KEY is missing or empty.')
} else if (isPlaceholder(anonKey)) {
  errors.push('NEXT_PUBLIC_SUPABASE_ANON_KEY contains a placeholder value.')
} else if (anonKey.length < 30) {
  errors.push('NEXT_PUBLIC_SUPABASE_ANON_KEY appears too short.')
} else {
  passes.push('NEXT_PUBLIC_SUPABASE_ANON_KEY is present and valid length')
}

// Check 4: NEXT_PUBLIC_APP_URL
const appUrl = envVars['NEXT_PUBLIC_APP_URL'] || ''
if (!appUrl) {
  warnings.push('NEXT_PUBLIC_APP_URL is not set. Defaulting to http://localhost:3000.')
} else {
  passes.push('NEXT_PUBLIC_APP_URL is set: ' + appUrl)
}

// Check 5: NEXT_PUBLIC_DEFAULT_REGION
const region = envVars['NEXT_PUBLIC_DEFAULT_REGION'] || ''
if (!region) {
  warnings.push('NEXT_PUBLIC_DEFAULT_REGION is not set. Defaulting to US.')
} else {
  passes.push('NEXT_PUBLIC_DEFAULT_REGION is set: ' + region)
}

// Check 6: NEXT_PUBLIC_DEFAULT_CITY
const city = envVars['NEXT_PUBLIC_DEFAULT_CITY'] || ''
if (!city) {
  warnings.push('NEXT_PUBLIC_DEFAULT_CITY is not set. Defaulting to NYC.')
} else {
  passes.push('NEXT_PUBLIC_DEFAULT_CITY is set: ' + city)
}

// Check 7: SUPABASE_SERVICE_ROLE_KEY
const serviceKey = envVars['SUPABASE_SERVICE_ROLE_KEY'] || ''
if (!serviceKey) {
  errors.push('SUPABASE_SERVICE_ROLE_KEY is missing or empty.')
} else if (isPlaceholder(serviceKey)) {
  errors.push('SUPABASE_SERVICE_ROLE_KEY contains a placeholder value.')
} else {
  passes.push('SUPABASE_SERVICE_ROLE_KEY is present')
}

// Check 8: Production placeholder detection
if (process.env.NODE_ENV === 'production') {
  for (const [key, value] of Object.entries(envVars)) {
    if (typeof value === 'string' && isPlaceholder(value)) {
      errors.push(`PRODUCTION BUILD ERROR: ${key} still contains a placeholder value!`)
    }
  }
}

// Output results
console.log('  ✅ PASSED:')
for (const p of passes) {
  console.log('     • ' + p)
}
console.log('')

if (warnings.length > 0) {
  console.log('  ⚠️  WARNINGS:')
  for (const w of warnings) {
    console.log('     • ' + w)
  }
  console.log('')
}

if (errors.length > 0) {
  console.log('  ❌ ERRORS:')
  for (const e of errors) {
    console.log('     • ' + e)
  }
  console.log('')
  console.log('  ────────────────────────────────────────────────')
  console.log('  ────────────────────────────────────────────────')
  console.log('  PREFLIGHT CHECK FAILED')
  console.log('  Supabase is not configured yet. Follow docs/SUPABASE_SETUP.md.')
  console.log('  ────────────────────────────────────────────────')
  console.log('')
  process.exit(1)
} else {
  console.log('  ────────────────────────────────────────────────')
  console.log('  ✅ PREFLIGHT CHECK PASSED')
  console.log('  Supabase environment is configured. You can continue localhost validation.')
  console.log('  ────────────────────────────────────────────────')
  console.log('')
  process.exit(0)
}
