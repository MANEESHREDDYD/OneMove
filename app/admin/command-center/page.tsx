import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { signout } from "@/app/auth/actions"

export default function AdminDashboard() {
  return (
    <div className="space-y-6">
      <PageHeader 
        title="Admin Command Center" 
        description="Global platform overview, live tracking, and system health."
      >
        <form action={signout}>
          <Button variant="outline">Sign Out</Button>
        </form>
      </PageHeader>
      
      <GlassCard className="p-8">
        <h2 className="text-xl font-bold">Live Network Map</h2>
        <p className="text-muted-foreground mt-2">Placeholder for global operations, trust and safety alerts, and demand zones.</p>
      </GlassCard>
    </div>
  )
}
