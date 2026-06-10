import * as dotenv from 'dotenv'
import path from 'path'
import { getSystemHealthSnapshot, type HealthCheck } from '../lib/systemHealth'

dotenv.config({ path: path.resolve(process.cwd(), '.env.local') })

const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'
const REQUIRED_ROUTES = ['/', '/showcase', '/customer/rides', '/admin/command-center']

function icon(status: HealthCheck['status']) {
  if (status === 'pass') return '[PASS]'
  if (status === 'warn') return '[WARN]'
  return '[FAIL]'
}

function printCheck(check: HealthCheck) {
  const suffix = check.value !== undefined ? ` (${check.value})` : ''
  console.log(`${icon(check.status)} ${check.name}${suffix}: ${check.detail}`)
}

async function checkRoutes(): Promise<number> {
  let routeFailures = 0
  console.log('\n--- Route probes ---')

  for (const route of REQUIRED_ROUTES) {
    try {
      const res = await fetch(`${appUrl}${route}`, { redirect: 'manual' })
      if (res.status < 500) {
        console.log(`[PASS] Route ${route} -> ${res.status}`)
      } else {
        console.log(`[FAIL] Route ${route} -> ${res.status}`)
        routeFailures++
      }
    } catch {
      console.log(`[WARN] Route ${route} unreachable (is the server running?)`)
    }
  }

  return routeFailures
}

async function main() {
  console.log('================================================')
  console.log('OneMove Local Healthcheck')
  console.log('================================================')

  const snapshot = await getSystemHealthSnapshot()
  console.log(`Generated: ${snapshot.generatedAt}`)
  console.log(`Commit: ${snapshot.commitHash}`)

  console.log('\n--- Core readiness ---')
  ;[
    snapshot.database,
    snapshot.pipeline,
    snapshot.latestMlRun,
    snapshot.latestDataQuality,
    snapshot.rlsTest,
  ].forEach(printCheck)

  console.log('\n--- Demo auth users ---')
  snapshot.demoUsers.forEach(printCheck)

  console.log('\n--- Required tables ---')
  snapshot.requiredTables.forEach(printCheck)

  console.log('\n--- Local observability placeholders ---')
  snapshot.observability.forEach(printCheck)

  const routeFailures = process.argv.includes('--routes') ? await checkRoutes() : 0
  const failures = snapshot.summary.fail + routeFailures

  console.log('\n================================================')
  if (failures === 0) {
    console.log('Healthcheck PASSED (no failing required checks)')
    console.log('================================================')
    process.exit(0)
  }

  console.log(`Healthcheck FAILED: ${failures} required check(s) failed`)
  console.log('================================================')
  process.exit(1)
}

main().catch((error) => {
  console.error('Healthcheck crashed:', error)
  process.exit(1)
})
