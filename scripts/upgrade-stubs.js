const fs = require('fs');
const path = require('path');

const generatePage = (title, iconName, description, tableHeaders, tableRows) => `import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { ${iconName} } from "lucide-react"

export default function ${title.replace(/\s+/g, '')}Page() {
  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="${title}" 
        description="${description}"
      />
      <GlassCard className="p-8 flex flex-col items-center justify-center min-h-[300px] text-center space-y-4">
        <div className="p-4 bg-primary/10 rounded-full">
          <${iconName} className="w-12 h-12 text-primary" />
        </div>
        <h3 className="text-xl font-semibold">Active ${title}</h3>
        <p className="text-muted-foreground max-w-md">
          This is a functional MVP placeholder. Live data integration for this module is scheduled for the next iteration.
        </p>
        
        <div className="w-full max-w-3xl mt-8 overflow-x-auto">
          <table className="w-full text-sm text-left border">
            <thead className="bg-muted text-muted-foreground uppercase text-xs">
              <tr>
                ${tableHeaders.map(h => `<th className="px-4 py-3">${h}</th>`).join('\n                ')}
              </tr>
            </thead>
            <tbody className="divide-y">
              ${tableRows.map(row => `
                <tr className="hover:bg-muted/50">
                  ${row.map(cell => `<td className="px-4 py-3">${cell}</td>`).join('\n                  ')}
                </tr>
              `).join('')}
              {${tableRows.length === 0} && (
                <tr>
                  <td colSpan={${tableHeaders.length}} className="px-4 py-8 text-center text-muted-foreground">
                    No records found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  )
}
`

const pages = {
  'customer/support': { title: 'Support Tickets', icon: 'LifeBuoy', headers: ['Ticket ID', 'Status', 'Date'], rows: [] },
  'customer/safety': { title: 'Safety & SOS', icon: 'ShieldAlert', headers: ['Incident ID', 'Type', 'Status'], rows: [] },
  'customer/profile': { title: 'Customer Profile', icon: 'User', headers: ['Setting', 'Value'], rows: [['Name', 'Customer Demo'], ['Email', 'customer@onemove.demo']] },
  
  'partner/jobs': { title: 'Available Jobs', icon: 'Briefcase', headers: ['Job ID', 'Type', 'Est. Payout'], rows: [['J-101', 'Ride', '$14.50'], ['J-102', 'Delivery', '$8.00']] },
  'partner/earnings': { title: 'Earnings', icon: 'DollarSign', headers: ['Date', 'Amount', 'Status'], rows: [['Today', '$45.00', 'Pending']] },
  'partner/heatmap': { title: 'Demand Heatmap', icon: 'Map', headers: ['Zone', 'Multiplier', 'Status'], rows: [['Times Square', '1.5x', 'High Demand']] },
  'partner/documents': { title: 'Verification Documents', icon: 'FileText', headers: ['Document', 'Status'], rows: [['Driver License', 'Verified'], ['Insurance', 'Pending']] },
  'partner/profile': { title: 'Partner Profile', icon: 'User', headers: ['Setting', 'Value'], rows: [['Name', 'Partner Demo'], ['Vehicle', 'Toyota Camry']] },

  'merchant/menu': { title: 'Menu Management', icon: 'Menu', headers: ['Item', 'Price', 'Status'], rows: [['Burger', '$12.00', 'Available'], ['Fries', '$4.00', 'Available']] },
  'merchant/inventory': { title: 'Inventory', icon: 'Package', headers: ['SKU', 'Stock', 'Status'], rows: [['SKU-01', '45', 'In Stock']] },
  'merchant/orders': { title: 'Order History', icon: 'ShoppingBag', headers: ['Order ID', 'Amount', 'Status'], rows: [] },
  'merchant/analytics': { title: 'Analytics', icon: 'LineChart', headers: ['Metric', 'Value'], rows: [['Today Sales', '$450.00'], ['Orders', '24']] },
  'merchant/payouts': { title: 'Payouts', icon: 'CreditCard', headers: ['Date', 'Amount', 'Status'], rows: [['Yesterday', '$1,200.00', 'Processed']] },
  'merchant/profile': { title: 'Store Profile', icon: 'Store', headers: ['Setting', 'Value'], rows: [['Store Name', 'Demo Merchant']] },

  'admin/users': { title: 'User Management', icon: 'Users', headers: ['User', 'Role', 'Status'], rows: [['Customer 1', 'Customer', 'Active']] },
  'admin/partners': { title: 'Partner Fleet', icon: 'Car', headers: ['Partner', 'Vehicle', 'Status'], rows: [['Partner 1', 'Car', 'Online']] },
  'admin/merchants': { title: 'Merchant Directory', icon: 'Store', headers: ['Merchant', 'Type', 'Status'], rows: [['Demo Store', 'Restaurant', 'Active']] },
  'admin/rides': { title: 'Global Rides', icon: 'Car', headers: ['Ride ID', 'Status', 'Driver'], rows: [] },
  'admin/orders': { title: 'Global Orders', icon: 'ShoppingBag', headers: ['Order ID', 'Status', 'Merchant'], rows: [] },
  'admin/courier': { title: 'Courier Network', icon: 'Package', headers: ['Job ID', 'Status', 'Courier'], rows: [] },
  'admin/sos': { title: 'Active SOS Alerts', icon: 'ShieldAlert', headers: ['Alert ID', 'Severity', 'Status'], rows: [] },
  'admin/complaints': { title: 'Customer Complaints', icon: 'MessageSquare', headers: ['Complaint ID', 'User', 'Status'], rows: [] },
  'admin/data-platform': { title: 'Data Platform', icon: 'Database', headers: ['Dataset', 'Rows', 'Health'], rows: [['Profiles', '4', 'Healthy']] },
  'admin/settings': { title: 'Global Settings', icon: 'Settings', headers: ['Setting', 'Value'], rows: [['Maintenance Mode', 'Off']] },
  
  'auth/role-select': { title: 'Role Selection', icon: 'Users', headers: ['Role', 'Description'], rows: [['Customer', 'Order rides and food'], ['Partner', 'Drive and earn']] }
}

for (const [route, config] of Object.entries(pages)) {
  const dir = path.join(__dirname, '../app', route);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  
  const content = generatePage(config.title, config.icon, `Manage ${config.title.toLowerCase()}`, config.headers, config.rows);
  fs.writeFileSync(path.join(dir, 'page.tsx'), content);
}
console.log('Upgraded all stubs!');
