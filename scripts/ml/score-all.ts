import { spawn } from 'child_process'
import path from 'path'

const scripts = [
  'generate-demand-forecast.ts',
  'run-dispatch-simulation.ts',
  'score-fraud-risk.ts',
  'generate-recommendations.ts',
  'segment-customers.ts',
  'score-merchant-reliability.ts',
  'score-partner-trust.ts'
]

async function runScript(scriptName: string) {
  return new Promise<void>((resolve, reject) => {
    const scriptPath = path.join(__dirname, scriptName)
    console.log(`\n================================================`)
    console.log(`🚀 Executing ML Pipeline: ${scriptName}`)
    console.log(`================================================`)
    
    const cmd = 'node'
    const args = ['--env-file=.env.local', 'node_modules/tsx/dist/cli.mjs', scriptPath]
    const child = spawn(cmd, args, { stdio: 'inherit', shell: true })

    child.on('close', (code) => {
      if (code === 0) {
        resolve()
      } else {
        reject(new Error(`Script ${scriptName} exited with code ${code}`))
      }
    })
  })
}

async function main() {
  console.log('Starting Master ML Pipeline execution...\n')
  
  for (const script of scripts) {
    try {
      await runScript(script)
    } catch (err) {
      console.error(`Pipeline stopped due to error in ${script}:`, err)
      process.exit(1)
    }
  }
  
  console.log('\n✅ All ML Pipelines completed successfully.')
}

main()
