import * as React from "react"
import { GlassCard } from "./GlassCard"

interface MetricCardProps {
  title: string
  value: string | number
  trend?: {
    value: string | number
    isPositive: boolean
  }
}

export function MetricCard({ title, value, trend }: MetricCardProps) {
  return (
    <GlassCard className="p-6 flex flex-col space-y-2">
      <h4 className="text-sm font-medium text-muted-foreground">{title}</h4>
      <div className="text-2xl font-bold">{value}</div>
      {trend && (
        <div className={`text-xs ${trend.isPositive ? "text-green-500" : "text-red-500"}`}>
          {trend.isPositive ? "+" : "-"}{trend.value} from last period
        </div>
      )}
    </GlassCard>
  )
}
