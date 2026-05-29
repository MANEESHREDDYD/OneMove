import * as React from "react"
import { Badge } from "@/components/ui/badge"

interface StatusBadgeProps {
  status: string
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "active":
      case "completed":
      case "delivered":
      case "online":
      case "ready":
        return "bg-green-500/20 text-green-400 hover:bg-green-500/30"
      case "pending":
      case "preparing":
      case "in_transit":
        return "bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30"
      case "cancelled":
      case "failed":
      case "offline":
        return "bg-red-500/20 text-red-400 hover:bg-red-500/30"
      default:
        return "bg-gray-500/20 text-gray-400 hover:bg-gray-500/30"
    }
  }

  return (
    <Badge variant="outline" className={`border-none ${getStatusColor(status)}`}>
      {status.replace("_", " ").toUpperCase()}
    </Badge>
  )
}
