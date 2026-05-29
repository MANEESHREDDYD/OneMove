import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { signout } from "@/app/auth/actions"

export default function DriverDashboard() {
  return (
    <div className="space-y-6">
      <PageHeader 
        title="Driver Dashboard" 
        description="Manage your rides, deliveries, and earnings."
      >
        <form action={signout}>
          <Button variant="outline">Sign Out</Button>
        </form>
      </PageHeader>
      
      <GlassCard className="p-8">
        <h2 className="text-xl font-bold">Online Status</h2>
        <p className="text-muted-foreground mt-2">Placeholder for toggle online status, map, and available jobs.</p>
      </GlassCard>
    </div>
  )
}
