import { GlassCard } from '@/components/common/GlassCard'
import { AlertTriangle } from 'lucide-react'

/**
 * Displays a developer-friendly setup screen when Supabase
 * environment variables are not configured.
 */
export function SetupRequired() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <GlassCard className="max-w-lg w-full p-8 border-t-4 border-t-orange-500">
        <div className="flex items-center gap-3 mb-6">
          <div className="bg-orange-500/20 p-2 rounded-lg">
            <AlertTriangle className="w-6 h-6 text-orange-500" />
          </div>
          <h1 className="text-xl font-bold">Setup Required</h1>
        </div>

        <p className="text-muted-foreground mb-4">
          OneMove needs Supabase credentials to run. Your <code className="bg-muted px-1.5 py-0.5 rounded text-xs font-mono">.env.local</code> file is missing or incomplete.
        </p>

        <div className="bg-muted/50 rounded-lg p-4 mb-6 font-mono text-xs space-y-1">
          <p className="text-orange-500 font-bold mb-2"># .env.local</p>
          <p>NEXT_PUBLIC_SUPABASE_URL=https://&lt;your-ref&gt;.supabase.co</p>
          <p>NEXT_PUBLIC_SUPABASE_ANON_KEY=&lt;your-anon-key&gt;</p>
          <p className="text-muted-foreground">SUPABASE_SERVICE_ROLE_KEY=&lt;optional&gt;</p>
          <p className="text-muted-foreground">NEXT_PUBLIC_APP_URL=http://localhost:3000</p>
          <p className="text-muted-foreground">NEXT_PUBLIC_DEFAULT_REGION=US</p>
          <p className="text-muted-foreground">NEXT_PUBLIC_DEFAULT_CITY=NYC</p>
        </div>

        <div className="space-y-3 text-sm">
          <h2 className="font-bold">How to fix this:</h2>
          <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
            <li>Copy <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">.env.local.example</code> to <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">.env.local</code></li>
            <li>Go to <strong>Supabase Dashboard → Project Settings → API</strong></li>
            <li>Copy your <strong>Project URL</strong> and <strong>anon/public key</strong></li>
            <li>Paste them into your <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">.env.local</code></li>
            <li>Restart the dev server: <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">npm run dev</code></li>
          </ol>
        </div>

        <p className="text-xs text-muted-foreground mt-6 border-t border-primary/10 pt-4">
          For detailed instructions, see <code className="font-mono">docs/LOCAL_SETUP.md</code>
        </p>
      </GlassCard>
    </div>
  )
}
