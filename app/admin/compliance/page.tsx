import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import Link from "next/link"
import { ArrowLeft, ShieldAlert, CheckCircle, FileWarning, Search, UserX } from "lucide-react"

export default async function CompliancePage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <PageHeader 
          title="Compliance & Safety" 
          description="Manage background checks and safety incidents"
        />
        <Link href="/admin/command-center">
          <Button variant="ghost" className="rounded-full text-xs">
            <ArrowLeft className="w-3 h-3 mr-1" /> Back to Command Center
          </Button>
        </Link>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        
        {/* Incident Reports */}
        <div className="space-y-4">
          <h2 className="text-lg font-bold flex items-center gap-2 text-destructive">
            <ShieldAlert className="w-5 h-5" /> Active Incidents
          </h2>
          
          {/* Mock Incident 1 */}
          <GlassCard className="p-5 border-l-4 border-l-destructive">
            <div className="flex justify-between items-start mb-3">
              <div className="flex items-center gap-2">
                <span className="px-2 py-1 bg-destructive/20 text-destructive text-[10px] font-bold uppercase rounded tracking-wider">
                  High Priority
                </span>
                <p className="text-xs text-muted-foreground font-mono">INC-88921</p>
              </div>
              <p className="text-xs text-muted-foreground">14 mins ago</p>
            </div>
            <h3 className="font-bold mb-1">Customer reported unsafe driving</h3>
            <p className="text-sm text-muted-foreground mb-4">
              During Ride #772-A, the customer reported that the partner was swerving and ran a red light. Partner account currently auto-suspended pending manual review.
            </p>
            <div className="flex gap-2">
              <Button size="sm" variant="destructive" className="flex-1">Ban Partner</Button>
              <Button size="sm" variant="secondary" className="flex-1 text-xs">Review Telematics</Button>
            </div>
          </GlassCard>

          {/* Mock Incident 2 */}
          <GlassCard className="p-5 border-l-4 border-l-orange-500">
            <div className="flex justify-between items-start mb-3">
              <div className="flex items-center gap-2">
                <span className="px-2 py-1 bg-orange-500/20 text-orange-500 text-[10px] font-bold uppercase rounded tracking-wider">
                  Medium Priority
                </span>
                <p className="text-xs text-muted-foreground font-mono">INC-88910</p>
              </div>
              <p className="text-xs text-muted-foreground">2 hours ago</p>
            </div>
            <h3 className="font-bold mb-1">Wrong Grocery Order Delivered</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Customer received order #112 instead of #114. Refund issued automatically by ML agent. Requires manual strike assignment to courier.
            </p>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" className="flex-1 border-orange-500 text-orange-500 hover:bg-orange-500/10">Issue Strike</Button>
              <Button size="sm" variant="ghost" className="flex-1">Dismiss</Button>
            </div>
          </GlassCard>
        </div>

        {/* Background Checks */}
        <div className="space-y-4">
          <h2 className="text-lg font-bold flex items-center gap-2 text-primary">
            <Search className="w-5 h-5" /> Background Checks Pending
          </h2>

          <GlassCard className="p-4 flex items-center justify-between hover:bg-primary/5 transition-colors cursor-pointer">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-primary/20 rounded-full flex items-center justify-center text-primary font-bold">
                JD
              </div>
              <div>
                <p className="font-bold">John Doe</p>
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <FileWarning className="w-3 h-3" /> Flagged: Traffic Violation (2024)
                </p>
              </div>
            </div>
            <Button size="sm">Review Docs</Button>
          </GlassCard>

          <GlassCard className="p-4 flex items-center justify-between hover:bg-primary/5 transition-colors cursor-pointer">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-primary/20 rounded-full flex items-center justify-center text-primary font-bold">
                SM
              </div>
              <div>
                <p className="font-bold">Sarah Miller</p>
                <p className="text-xs text-muted-foreground flex items-center gap-1 text-emerald-500">
                  <CheckCircle className="w-3 h-3" /> Clear: Ready for Approval
                </p>
              </div>
            </div>
            <Button size="sm" variant="secondary" className="bg-emerald-500/20 text-emerald-500 hover:bg-emerald-500/30">Approve Partner</Button>
          </GlassCard>
          
          <GlassCard className="p-4 flex items-center justify-between hover:bg-primary/5 transition-colors cursor-pointer opacity-50">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-destructive/20 rounded-full flex items-center justify-center text-destructive font-bold">
                RB
              </div>
              <div>
                <p className="font-bold text-destructive line-through">Richard Roe</p>
                <p className="text-xs text-destructive flex items-center gap-1">
                  <UserX className="w-3 h-3" /> Rejected: Criminal Record Match
                </p>
              </div>
            </div>
            <span className="text-xs font-bold text-destructive uppercase tracking-wider">Auto-Declined</span>
          </GlassCard>

        </div>

      </div>
    </div>
  )
}
