import { PageHeader } from "@/components/common/PageHeader"
import { Button } from "@/components/ui/button"
import { createClient } from "@/utils/supabase/server"
import { redirect } from "next/navigation"
import Link from "next/link"
import { ArrowLeft } from "lucide-react"
import { AILabClient } from "./AILabClient"

export default async function AILabPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  return (
    <div className="space-y-8 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <PageHeader 
          title="ML / AI Lab" 
          description="Generative intelligence & forecasting"
        />
        <Link href="/admin/command-center">
          <Button variant="ghost" className="rounded-full text-xs">
            <ArrowLeft className="w-3 h-3 mr-1" /> Back to Command Center
          </Button>
        </Link>
      </div>

      <AILabClient />
    </div>
  )
}
