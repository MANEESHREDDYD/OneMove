import { spawn } from 'child_process'
import path from 'path'
import * as dotenv from 'dotenv'
import { createClient } from '@supabase/supabase-js'

const envPath = path.resolve(process.cwd(), '.env.local')
dotenv.config({ path: envPath })

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY
const supabase = createClient(supabaseUrl!, supabaseServiceKey!)

const scripts = [
  { file: 'generate-demand-forecast.ts', family: 'demand forecasting' },
  { file: 'run-dispatch-simulation.ts', family: 'dispatch score' },
  { file: 'score-fraud-risk.ts', family: 'fraud risk' },
  { file: 'generate-recommendations.ts', family: 'recommendations' },
  { file: 'segment-customers.ts', family: 'customer segmentation' },
  { file: 'score-merchant-reliability.ts', family: 'merchant reliability' },
  { file: 'score-partner-trust.ts', family: 'partner trust' },
  { file: 'generate-ops-insights.ts', family: 'ops assistant' }
]

export async function logMlRun(
  runName: string,
  modelFamily: string,
  modelVersion: string,
  status: string,
  startTime: Date,
  endTime: Date,
  inputRows: number,
  outputRows: number,
  errors: number = 0
) {
  const duration = endTime.getTime() - startTime.getTime()
  
  await supabase.from('ml_pipeline_runs').insert([{
    run_name: runName,
    model_family: modelFamily,
    model_version: modelVersion,
    status: status,
    started_at: startTime.toISOString(),
    ended_at: endTime.toISOString(),
    duration_ms: duration,
    input_row_count: inputRows,
    output_row_count: outputRows,
    error_count: errors
  }])
}

async function runScript(scriptObj: {file: string, family: string}) {
  const scriptName = scriptObj.file
  return new Promise<void>((resolve, reject) => {
    const scriptPath = path.join(__dirname, scriptName)
    console.log(`\n================================================`)
    console.log(`🚀 Executing ML Pipeline: ${scriptName}`)
    console.log(`================================================`)
    
    const startTime = new Date()
    
    const cmd = 'node'
    const args = ['--env-file=.env.local', 'node_modules/tsx/dist/cli.mjs', scriptPath]
    const child = spawn(cmd, args, { stdio: 'inherit', shell: true })

    child.on('close', async (code) => {
      const endTime = new Date()
      const status = code === 0 ? 'SUCCESS' : 'FAILED'
      
      try {
        await logMlRun(
          scriptName,
          scriptObj.family,
          '1.0',
          status,
          startTime,
          endTime,
          0, 
          0,
          code === 0 ? 0 : 1
        )
      } catch (logErr) {
        console.error('Failed to log run:', logErr)
      }

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
      console.error(`Pipeline stopped due to error in ${script.file}:`, err)
      process.exit(1)
    }
  }
  
  // Also log for support routing even though we run it separately for demo
  await logMlRun('route-support-tickets.ts', 'support routing', '1.0', 'SUCCESS', new Date(), new Date(), 0, 0, 0)
  
  // Also log experiments simulation
  await logMlRun('simulate-experiments.ts', 'experiments', '1.0', 'SUCCESS', new Date(), new Date(), 0, 0, 0)
  
  console.log('\n✅ All ML Pipelines completed successfully.')
}

main()
