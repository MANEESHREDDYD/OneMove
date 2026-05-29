import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { signout } from "@/app/auth/actions"

export default function CustomerDashboard() {
  return (
    <div className="space-y-6">
      <PageHeader 
        title="Customer Dashboard" 
        description="Welcome to your OneMove portal. Order rides, food, and groceries."
      >
        <form action={signout}>
          <Button variant="outline">Sign Out</Button>
        </form>
      </PageHeader>
      
      <GlassCard className="p-8">
        <h2 className="text-xl font-bold">Your Activity</h2>
        <p className="text-muted-foreground mt-2">Placeholder for customer activity metrics, active orders, and quick actions.</p>
      </GlassCard>
    </div>
  )
}
