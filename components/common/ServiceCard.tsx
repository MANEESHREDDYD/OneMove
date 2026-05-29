import * as React from "react"
import { GlassCard } from "./GlassCard"
import { LucideIcon } from "lucide-react"
import Link from "next/link"

interface ServiceCardProps {
  title: string
  description?: string
  icon: LucideIcon
  onClick?: () => void
  href?: string
}

export function ServiceCard({ title, description, icon: Icon, onClick, href }: ServiceCardProps) {
  const content = (
    <>
      <div className="p-3 bg-primary/20 rounded-full">
        <Icon className="w-8 h-8 text-primary" />
      </div>
      <div>
        <h3 className="font-semibold text-lg">{title}</h3>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
    </>
  )

  if (href) {
    return (
      <Link href={href} className="block w-full h-full">
        <GlassCard className="p-6 h-full cursor-pointer hover:bg-white/10 transition-colors flex flex-col items-center justify-center text-center space-y-3">
          {content}
        </GlassCard>
      </Link>
    )
  }

  return (
    <GlassCard 
      className="p-6 h-full cursor-pointer hover:bg-white/10 transition-colors flex flex-col items-center justify-center text-center space-y-3"
      onClick={onClick}
    >
      {content}
    </GlassCard>
  )
}
