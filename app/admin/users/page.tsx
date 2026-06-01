import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { createClient } from "@/utils/supabase/server"
import { SetupRequired } from "@/components/common/SetupRequired"

export const dynamic = "force-dynamic"

export default async function AdminUsersPage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />

  // Fetch profiles
  const { data: profiles, error } = await supabase
    .from('profiles')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(100)

  if (error) {
    console.error('Error fetching users:', error)
  }

  const users = profiles || []

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="Demo Users Directory" 
        description="View generated demo accounts across all roles."
      />

      <GlassCard className="p-6 border-blue-500/20 bg-blue-500/5">
        <h3 className="font-bold text-lg mb-2">Local Private Credentials</h3>
        <p className="text-muted-foreground text-sm">
          Passwords are NOT shown here for security. To view the exact login credentials for all generated demo users, please check the local file: <code className="bg-muted px-1.5 py-0.5 rounded text-primary">private/DEMO_LOGIN_CREDENTIALS.local.md</code> or <code className="bg-muted px-1.5 py-0.5 rounded text-primary">private/demo-login-credentials.csv</code> in your project repository.
        </p>
      </GlassCard>

      <GlassCard className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-muted-foreground uppercase bg-muted/50">
              <tr>
                <th className="px-6 py-4 font-medium">Name</th>
                <th className="px-6 py-4 font-medium">Role</th>
                <th className="px-6 py-4 font-medium">Expected Route</th>
                <th className="px-6 py-4 font-medium">Demo Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {users.map((user) => {
                let route = '/customer'
                if (user.role === 'driver') route = '/partner'
                if (user.role === 'merchant') route = '/merchant'
                if (user.role === 'admin') route = '/admin/command-center'

                return (
                  <tr key={user.id} className="hover:bg-muted/50 transition-colors">
                    <td className="px-6 py-4 font-medium">{user.full_name}</td>
                    <td className="px-6 py-4">
                      <span className="bg-primary/20 text-primary px-2 py-1 rounded-full text-xs font-bold uppercase tracking-wider">
                        {user.role === 'driver' ? 'partner' : user.role}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-xs">{route}</td>
                    <td className="px-6 py-4">
                      {user.is_demo ? (
                        <span className="text-green-500 font-medium">True</span>
                      ) : (
                        <span className="text-muted-foreground">False</span>
                      )}
                    </td>
                  </tr>
                )
              })}
              {users.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-muted-foreground">
                    No demo users found. Run <code className="bg-muted px-1 rounded">npm run seed:auth</code>.
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
