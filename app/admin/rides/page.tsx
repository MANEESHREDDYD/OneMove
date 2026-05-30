import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { Car } from "lucide-react"

export default function GlobalRidesPage() {
  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="Global Rides" 
        description="Manage global rides"
      />
      <GlassCard className="p-8 flex flex-col items-center justify-center min-h-[300px] text-center space-y-4">
        <div className="p-4 bg-primary/10 rounded-full">
          <Car className="w-12 h-12 text-primary" />
        </div>
        <h3 className="text-xl font-semibold">Active Global Rides</h3>
        <p className="text-muted-foreground max-w-md">
          This is a functional MVP placeholder. Live data integration for this module is scheduled for the next iteration.
        </p>
        
        <div className="w-full max-w-3xl mt-8 overflow-x-auto">
          <table className="w-full text-sm text-left border">
            <thead className="bg-muted text-muted-foreground uppercase text-xs">
              <tr>
                <th className="px-4 py-3">Ride ID</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Driver</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              
              {true && (
                <tr>
                  <td colSpan={3} className="px-4 py-8 text-center text-muted-foreground">
                    No records found.
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
