const fs = require('fs');
const path = require('path');

const routes = [
  'auth/role-select',
  'customer/support',
  'customer/safety',
  'partner/jobs',
  'partner/earnings',
  'partner/heatmap',
  'partner/documents',
  'partner/profile',
  'merchant/menu',
  'merchant/inventory',
  'merchant/orders',
  'merchant/analytics',
  'merchant/payouts',
  'merchant/profile',
  'admin/users',
  'admin/partners',
  'admin/merchants',
  'admin/rides',
  'admin/orders',
  'admin/courier',
  'admin/sos',
  'admin/complaints',
  'admin/data-platform',
  'admin/settings'
];

for (const route of routes) {
  const dir = path.join(__dirname, '../app', route);
  fs.mkdirSync(dir, { recursive: true });
  const content = `import { EmptyState } from "@/components/common/EmptyState"
import { Construction } from "lucide-react"

export default function StubPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh]">
      <EmptyState 
        icon={Construction}
        title="Coming Soon"
        description="This feature is actively being developed."
      />
    </div>
  )
}
`;
  fs.writeFileSync(path.join(dir, 'page.tsx'), content);
}
console.log("Created all stubs!");
