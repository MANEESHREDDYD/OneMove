const fs = require('fs');
const path = require('path');

function walkDir(dir, callback) {
  fs.readdirSync(dir).forEach(f => {
    const dirPath = path.join(dir, f);
    const isDirectory = fs.statSync(dirPath).isDirectory();
    if (isDirectory) {
      if (f !== 'node_modules' && f !== '.next' && f !== '.git') {
        walkDir(dirPath, callback);
      }
    } else if (dirPath.endsWith('.tsx') || dirPath.endsWith('.ts')) {
      callback(path.join(dir, f));
    }
  });
}

const badPatterns = [
  { regex: /href="#"/g, name: 'href="#" dead link' },
  { regex: /onClick=\{\(\) => \{\}\}/g, name: 'empty onClick handler' },
  { regex: /Map Preview/g, name: 'Map Preview placeholder' },
  { regex: /<EmptyState\s+[^>]*title="Coming Soon"/g, name: 'Generic Coming Soon EmptyState' }
];

let errorsFound = 0;

walkDir(path.join(__dirname, '../app'), (filePath) => {
  const content = fs.readFileSync(filePath, 'utf-8');
  
  badPatterns.forEach(pattern => {
    const matches = content.match(pattern.regex);
    if (matches) {
      console.error(`❌ [AUDIT FAILURE] ${pattern.name} found in ${filePath}`);
      errorsFound += matches.length;
    }
  });
});

walkDir(path.join(__dirname, '../components'), (filePath) => {
  const content = fs.readFileSync(filePath, 'utf-8');
  
  badPatterns.forEach(pattern => {
    const matches = content.match(pattern.regex);
    if (matches) {
      console.error(`❌ [AUDIT FAILURE] ${pattern.name} found in ${filePath}`);
      errorsFound += matches.length;
    }
  });
});

if (errorsFound > 0) {
  console.error(`\nAudit failed with ${errorsFound} interactive UI issues.`);
  process.exit(1);
} else {
  console.log('\n✅ Audit passed. No dead links or placeholders found.');
  process.exit(0);
}
