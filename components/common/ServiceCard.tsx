import * as React from "react"
import { GlassCard } from "./GlassCard"
import Link from "next/link"
import { cn } from "@/lib/utils"

interface ServiceCardProps {
  title: string
  description?: string
  icon: React.ReactNode
  onClick?: () => void
  href?: string
  gradient?: string
}

export function ServiceCard({ title, description, icon, onClick, href, gradient }: ServiceCardProps) {
  const content = (
    <>
      {gradient && (
        <div className={cn("absolute inset-0 bg-gradient-to-br opacity-0 group-hover:opacity-10 transition-opacity duration-300", gradient)} />
      )}
      <div className="relative z-10 p-3 bg-primary/20 rounded-full mb-3 group-hover:scale-110 transition-transform duration-300">
        {icon}
      </div>
      <div className="relative z-10">
        <h3 className="font-semibold text-lg">{title}</h3>
        {description && <p className="text-sm text-muted-foreground mt-1">{description}</p>}
      </div>
    </>
  )

  const cardClasses = "relative overflow-hidden p-6 h-full cursor-pointer hover:bg-white/5 transition-colors flex flex-col items-center justify-center text-center group"

  if (href) {
    return (
      <Link href={href} className="block w-full h-full">
        <GlassCard className={cardClasses}>
          {content}
        </GlassCard>
      </Link>
    )
  }

  return (
    <GlassCard 
      className={cardClasses}
      onClick={onClick}
    >
      {content}
    </GlassCard>
  )
}
