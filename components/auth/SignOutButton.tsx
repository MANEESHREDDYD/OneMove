'use client'

import { Button } from "@/components/ui/button"
import { LogOut } from "lucide-react"
import { signout } from "@/app/auth/actions"

interface SignOutButtonProps {
  className?: string
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link"
  showLabel?: boolean
}

export function SignOutButton({ className = "", variant = "ghost", showLabel = true }: SignOutButtonProps) {
  const clearBrowserState = () => {
    localStorage.clear()
    sessionStorage.clear()
  }

  return (
    <form action={signout}>
      <Button
        type="submit"
        variant={variant}
        className={className}
        onClick={clearBrowserState}
      >
        <LogOut className={`h-4 w-4 ${showLabel ? 'mr-2' : ''}`} />
        {showLabel && "Sign Out"}
      </Button>
    </form>
  )
}
