import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { signout } from "@/app/auth/actions"

export default function MerchantDashboard() {
  return (
    <div className="space-y-6">
      <PageHeader 
        title="Merchant Dashboard" 
        description="Manage your store, inventory, and orders."
      >
        <form action={signout}>
          <Button variant="outline">Sign Out</Button>
        </form>
      </PageHeader>
      
      <GlassCard className="p-8">
        <h2 className="text-xl font-bold">Active Orders</h2>
        <p className="text-muted-foreground mt-2">Placeholder for order management, inventory updates, and performance metrics.</p>
      </GlassCard>
    </div>
  )
}
