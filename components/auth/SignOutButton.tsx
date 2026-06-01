'use client'

import { Button } from "@/components/ui/button"
import { LogOut } from "lucide-react"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { signout } from "@/app/auth/actions"

interface SignOutButtonProps {
  className?: string
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link"
  showLabel?: boolean
}

export function SignOutButton({ className = "", variant = "ghost", showLabel = true }: SignOutButtonProps) {
  const [loading, setLoading] = useState(false)

  const handleSignOut = async () => {
    setLoading(true)
    try {
      // Clear localStorage (e.g. cartStore)
      localStorage.clear()
      sessionStorage.clear()
      
      // Call the server action to clear Supabase cookies
      await signout()
      
      // The server action redirects, but as a fallback/hard reload:
      window.location.href = '/auth/login'
    } catch (e) {
      console.error("Sign out failed", e)
      window.location.href = '/auth/login'
    } finally {
      setLoading(false)
    }
  }

  return (
    <Button 
      variant={variant} 
      className={className} 
      onClick={handleSignOut}
      disabled={loading}
    >
      <LogOut className={`h-4 w-4 ${showLabel ? 'mr-2' : ''}`} />
      {showLabel && "Sign Out"}
    </Button>
  )
}
