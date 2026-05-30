import { EmptyState } from "@/components/common/EmptyState"
import { Construction } from "lucide-react"

export default function StubPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh]">
      <EmptyState 
        icon={Construction}
        title="Coming Soon"
        description="This feature is actively being developed."
      />
    </div>
  )
}
