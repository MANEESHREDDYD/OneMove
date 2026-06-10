import { spawnSync } from 'node:child_process'
import path from 'node:path'

const skipIntelligence = process.argv.includes('--skip-intelligence')
const dryRun = process.argv.includes('--dry-run')

type Step = {
  command: string
  args: string[]
  label: string
}

function bin(name: string) {
  return process.platform === 'win32' ? `${name}.cmd` : name
}

function tsxStep(label: string, scriptPath: string, args: string[] = []): Step {
  return {
    command: process.execPath,
    args: [path.join(process.cwd(), 'node_modules', 'tsx', 'dist', 'cli.mjs'), scriptPath, ...args],
    label,
  }
}

function npmScriptStep(label: string, scriptName: string): Step {
  const npmExecPath = process.env.npm_execpath
  if (npmExecPath) {
    return {
      command: process.execPath,
      args: [npmExecPath, 'run', scriptName],
      label,
    }
  }

  return {
    command: bin('npm'),
    args: ['run', scriptName],
    label,
  }
}

const steps: Step[] = dryRun
  ? [
      tsxStep('Preview demo data reset', 'scripts/generate-production-demo-data.ts', [
        '--reset',
        '--dry-run',
      ]),
    ]
  : [
      tsxStep('Delete rows explicitly marked is_demo=true', 'scripts/generate-production-demo-data.ts', [
        '--reset',
      ]),
      tsxStep('Recreate primary and generated demo auth users', 'scripts/seed-auth-users.ts'),
      tsxStep('Recreate synthetic marketplace demo data', 'scripts/generate-production-demo-data.ts'),
    ]

if (!skipIntelligence && !dryRun) {
  steps.push(npmScriptStep('Refresh metric, ML, experiment, and ops-intelligence outputs', 'intelligence:refresh'))
}

console.log('OneMove demo reset')
console.log('Scope: synthetic rows marked is_demo=true and demo auth accounts only.')
console.log('Non-demo rows are not targeted by this command.')

for (const [index, step] of steps.entries()) {
  console.log(`\n[${index + 1}/${steps.length}] ${step.label}`)
  const result = spawnSync(step.command, step.args, { stdio: 'inherit' })

  if (result.status !== 0) {
    if (result.error) {
      console.error(result.error.message)
    }
    console.error(`Demo reset failed during step: ${step.label}`)
    process.exit(result.status ?? 1)
  }
}

console.log('\nDemo reset completed.')
