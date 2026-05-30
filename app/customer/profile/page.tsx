import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { SetupRequired } from "@/components/common/SetupRequired"
import { createClient } from "@/utils/supabase/server"

export default async function CustomerProfile() {
  const supabase = await createClient()
  if (!supabase) {
    return <SetupRequired />
  }
  const { data: { user } } = await supabase.auth.getUser()

  return (
    <div className="space-y-6">
      <PageHeader title="Profile" description="Manage your account" />
      <GlassCard className="p-6">
        <h2 className="text-xl font-bold mb-4">Account Information</h2>
        <div className="space-y-4">
          <div>
            <label className="text-sm text-muted-foreground">Email</label>
            <p className="font-medium">{user?.email || 'Unknown'}</p>
          </div>
          <div>
            <label className="text-sm text-muted-foreground">User ID</label>
            <p className="font-mono text-sm">{user?.id || 'Unknown'}</p>
          </div>
        </div>
      </GlassCard>
    </div>
  )
}
