import { PageHeader } from "@/components/common/PageHeader"
import { GlassCard } from "@/components/common/GlassCard"
import Link from "next/link"
import { Button } from "@/components/ui/button"

export default function AuthErrorPage() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-background p-4">
      <GlassCard className="w-full max-w-md p-8 text-center space-y-6">
        <PageHeader 
          title="Authentication Error" 
          description="We could not sign you in." 
        />
        <p className="text-muted-foreground text-sm">
          There was a problem verifying your authentication code. Please try again or use a different login method.
        </p>
        <Link href="/auth/login" className="block w-full">
          <Button className="w-full">Return to Login</Button>
        </Link>
      </GlassCard>
    </div>
  )
}
