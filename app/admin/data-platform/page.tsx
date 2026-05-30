import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import { Database } from "lucide-react"

export default function DataPlatformPage() {
  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <PageHeader 
        title="Data Platform" 
        description="Manage data platform"
      />
      <GlassCard className="p-8 flex flex-col items-center justify-center min-h-[300px] text-center space-y-4">
        <div className="p-4 bg-primary/10 rounded-full">
          <Database className="w-12 h-12 text-primary" />
        </div>
        <h3 className="text-xl font-semibold">Active Data Platform</h3>
        <p className="text-muted-foreground max-w-md">
          This is a functional MVP placeholder. Live data integration for this module is scheduled for the next iteration.
        </p>
        
        <div className="w-full max-w-3xl mt-8 overflow-x-auto">
          <table className="w-full text-sm text-left border">
            <thead className="bg-muted text-muted-foreground uppercase text-xs">
              <tr>
                <th className="px-4 py-3">Dataset</th>
                <th className="px-4 py-3">Rows</th>
                <th className="px-4 py-3">Health</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              
                <tr className="hover:bg-muted/50">
                  <td className="px-4 py-3">Profiles</td>
                  <td className="px-4 py-3">4</td>
                  <td className="px-4 py-3">Healthy</td>
                </tr>
              
              {false && (
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
