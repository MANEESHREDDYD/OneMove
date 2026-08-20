import { PageHeader } from "@/components/common/PageHeader"
import { SetupRequired } from "@/components/common/SetupRequired"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { requireAdmin } from "@/lib/auth/dal"
import Link from "next/link"
import { ArrowLeft, PlugZap } from "lucide-react"

/**
 * Compliance & Safety.
 *
 * There is no incident-reporting or background-check service backing this route:
 * no `incidents` / `background_checks` table exists in supabase/, no API route
 * serves them, and no service in services/ produces them. This page previously
 * rendered invented incidents (INC-88921, INC-88910), invented named individuals
 * with criminal and traffic findings, and live-looking Ban Partner / Issue Strike /
 * Approve Partner controls that were wired to nothing.
 *
 * Until a real source exists, this route reports FEATURE_NOT_CONNECTED and exposes
 * no actionable controls. Do not reintroduce sample data here: an operator acting on
 * a fabricated safety incident can ban a real partner over an event that never happened.
 */
export default async function CompliancePage() {
  if (!(await requireAdmin())) {
    return <SetupRequired />
  }

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <PageHeader
          title="Compliance & Safety"
          description="Background checks and safety incidents"
        />
        <Link href="/admin/command-center">
          <Button variant="ghost" className="rounded-full text-xs">
            <ArrowLeft className="w-3 h-3 mr-1" /> Back to Command Center
          </Button>
        </Link>
      </div>

      <GlassCard className="p-8 flex flex-col items-center justify-center min-h-[320px] text-center space-y-4">
        <div className="p-4 bg-muted rounded-full">
          <PlugZap className="w-12 h-12 text-muted-foreground" />
        </div>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
          Feature Not Connected
        </p>
        <h2 className="text-xl font-semibold">No compliance data source is wired up</h2>
        <p className="text-muted-foreground max-w-lg text-sm leading-relaxed">
          Safety incidents and partner background checks are not produced by any system
          in this deployment. There is no incident store, no background-check provider
          integration, and no partner enforcement pipeline behind this screen.
        </p>
        <p className="text-muted-foreground max-w-lg text-sm leading-relaxed">
          Partner enforcement actions (ban, strike, approval) are intentionally
          unavailable here. Enabling them before a real incident record exists would let
          an operator penalise a partner over an event no system recorded.
        </p>
      </GlassCard>
    </div>
  )
}
