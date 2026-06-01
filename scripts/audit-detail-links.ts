import fs from 'fs'
import path from 'path'

function walkDir(dir: string, callback: (filepath: string) => void) {
  fs.readdirSync(dir).forEach(f => {
    const dirPath = path.join(dir, f)
    const isDirectory = fs.statSync(dirPath).isDirectory()
    if (isDirectory) {
      walkDir(dirPath, callback)
    } else {
      callback(path.join(dir, f))
    }
  })
}

function auditLinks() {
  console.log('=== Auditing Detail Links ===')
  
  let errors = 0
  const appDir = path.resolve(process.cwd(), 'app')
  
  walkDir(appDir, (filepath) => {
    if (!filepath.endsWith('.tsx') && !filepath.endsWith('.ts')) return
    
    const content = fs.readFileSync(filepath, 'utf8')
    const relPath = path.relative(process.cwd(), filepath)
    
    // Check for hardcoded href="#"
    if (content.includes('href="#"')) {
      console.error(`❌ [${relPath}] Found hardcoded href="#"`)
      errors++
    }
    
    // Check for hardcoded /details that doesn't have an ID
    if (content.match(/href="\/[a-z]+\/details"/)) {
      console.error(`❌ [${relPath}] Found static details link without ID`)
      errors++
    }
  })
  
  if (errors > 0) {
    console.error(`\nFound ${errors} invalid links.`)
    process.exit(1)
  } else {
    console.log('✅ All links look dynamic and properly formed.')
  }
}

auditLinks()
