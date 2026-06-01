import * as fs from 'fs';
import * as path from 'path';

const privateDir = path.resolve(process.cwd(), 'private');
if (!fs.existsSync(privateDir)) {
  fs.mkdirSync(privateDir, { recursive: true });
}

const csvPath = path.join(privateDir, 'demo-login-credentials.csv');
const mdPath = path.join(privateDir, 'DEMO_LOGIN_CREDENTIALS.local.md');

const PRIMARY_DEMO = [
  { role: 'customer', name: 'Demo Customer', email: 'customer@onemove.demo', password: 'Demo@12345', route: '/customer' },
  { role: 'partner', name: 'Demo Partner', email: 'partner@onemove.demo', password: 'Demo@12345', route: '/partner' },
  { role: 'merchant', name: 'Demo Merchant', email: 'merchant@onemove.demo', password: 'Demo@12345', route: '/merchant' },
  { role: 'admin', name: 'Demo Admin', email: 'admin@onemove.demo', password: 'Demo@12345', route: '/admin/command-center' }
];

function generateUsers(prefix: string, roleName: string, route: string, count: number) {
  const users = [];
  for (let i = 1; i <= count; i++) {
    const num = String(i).padStart(3, '0');
    users.push({
      role: roleName,
      name: `Demo ${prefix.charAt(0).toUpperCase() + prefix.slice(1)} ${num}`,
      email: `${prefix}${num}@onemove.demo`,
      password: `${prefix.charAt(0).toUpperCase() + prefix.slice(1)}@${num}Move`,
      route: route
    });
  }
  return users;
}

const allUsers = [
  ...PRIMARY_DEMO,
  ...generateUsers('customer', 'customer', '/customer', 50),
  ...generateUsers('partner', 'partner', '/partner', 50),
  ...generateUsers('merchant', 'merchant', '/merchant', 50),
  ...generateUsers('admin', 'admin', '/admin/command-center', 2)
];

// CSV Export
const csvHeader = "role,name,email,password,expected_route\n";
const csvRows = allUsers.map(u => `${u.role},"${u.name}",${u.email},${u.password},${u.route}`).join("\n");
fs.writeFileSync(csvPath, csvHeader + csvRows);

// MD Export
let mdContent = `# Demo Login Credentials\n\n`;
mdContent += `> **IMPORTANT:** These credentials are demo-only and must not be used in production. Do not commit this file.\n\n`;

mdContent += `## Primary Accounts\n\n`;
mdContent += `| Role | Name | Email | Password | Route |\n`;
mdContent += `|------|------|-------|----------|-------|\n`;
PRIMARY_DEMO.forEach(u => {
  mdContent += `| ${u.role} | ${u.name} | ${u.email} | ${u.password} | ${u.route} |\n`;
});

mdContent += `\n## Generated Accounts\n\n`;
mdContent += `| Role | Name | Email | Password | Route |\n`;
mdContent += `|------|------|-------|----------|-------|\n`;
allUsers.slice(4).forEach(u => {
  mdContent += `| ${u.role} | ${u.name} | ${u.email} | ${u.password} | ${u.route} |\n`;
});

fs.writeFileSync(mdPath, mdContent);

console.log(`Successfully exported credentials to:\n - ${csvPath}\n - ${mdPath}`);
