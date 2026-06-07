import { spawn } from 'child_process'
import * as path from 'path'

const scripts = [
  'ingest-events.ts',
  'compute-daily-metrics.ts',
  'data-quality-checks.ts',
  'compute-feature-snapshots.ts'
]

async function runScript(scriptName: string) {
  return new Promise<void>((resolve, reject) => {
    console.log(`\n========================================`)
    console.log(`Running ${scriptName}...`)
    console.log(`========================================`)
    const cmd = process.platform === 'win32' ? 'npx.cmd' : 'npx'
    const child = spawn(cmd, ['tsx', path.join(__dirname, scriptName)], { stdio: 'inherit', shell: true })
    
    child.on('close', (code) => {
      if (code === 0) resolve()
      else reject(new Error(`Script ${scriptName} exited with code ${code}`))
    })
  })
}

async function runAll() {
  try {
    for (const script of scripts) {
      await runScript(script)
    }
    console.log('\n✅ All data pipelines completed successfully.')
  } catch (err) {
    console.error('\n❌ Pipeline execution failed:', err)
    process.exit(1)
  }
}

runAll()
