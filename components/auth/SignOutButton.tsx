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
      {/*
        With showLabel={false} this rendered as an icon with no text at all,
        leaving the button nameless. aria-label is applied only in that case, so
        when the visible text is present it stays the accessible name (and
        remains speakable for voice control).
      */}
      <Button
        type="submit"
        variant={variant}
        aria-label={showLabel ? undefined : "Sign out"}
        className={className}
        onClick={clearBrowserState}
      >
        <LogOut aria-hidden="true" focusable="false" className={`h-4 w-4 ${showLabel ? 'mr-2' : ''}`} />
        {showLabel && "Sign Out"}
      </Button>
    </form>
  )
}
