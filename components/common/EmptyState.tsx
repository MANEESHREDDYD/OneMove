import * as React from "react"
import { LucideIcon } from "lucide-react"

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  action?: React.ReactNode
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center space-y-4">
      <div className="p-4 bg-primary/10 rounded-full">
        <Icon className="w-12 h-12 text-muted-foreground" />
      </div>
      <div className="max-w-md space-y-2">
        <h3 className="text-xl font-semibold">{title}</h3>
        {description && <p className="text-muted-foreground">{description}</p>}
      </div>
      {action && <div className="pt-4">{action}</div>}
    </div>
  )
}
