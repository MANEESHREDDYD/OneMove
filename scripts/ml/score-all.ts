import { spawn } from 'child_process'
import path from 'path'

const scripts = [
  'generate-demand-forecast.ts',
  'run-dispatch-simulation.ts',
  'score-fraud-risk.ts'
]

async function runScript(scriptName: string) {
  return new Promise<void>((resolve, reject) => {
    const scriptPath = path.join(__dirname, scriptName)
    console.log(`\n================================================`)
    console.log(`🚀 Executing ML Pipeline: ${scriptName}`)
    console.log(`================================================`)
    
    const cmd = process.platform === 'win32' ? 'npx.cmd' : 'npx'
    const child = spawn(cmd, ['tsx', scriptPath], { stdio: 'inherit', shell: true })

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
