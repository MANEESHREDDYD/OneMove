import Link from "next/link"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { login } from "../actions"
import { DemoLoginPanel } from "@/components/auth/DemoLoginPanel"

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>
}) {
  const { error } = await searchParams

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        <GlassCard className="p-8 space-y-6">
          <div className="space-y-2 text-center">
            <h1 className="text-3xl font-bold tracking-tight">Welcome back</h1>
            <p className="text-muted-foreground">Enter your credentials to sign in to OneMove</p>
          </div>

          <form className="space-y-4" action={login}>
            {/*
              A sign-in failure was rendered as a coloured box with no role, so
              nothing was announced and the fields gave no indication that they
              were the ones rejected. role="alert" announces it, and
              aria-invalid + aria-describedby tie the message to both fields —
              the server cannot tell which of the two was wrong, so both are
              marked rather than guessing.
            */}
            {error && (
              <div id="login-error" role="alert" className="text-sm font-medium text-red-400 bg-red-500/10 p-3 rounded-md">
                {error}
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder="name@example.com"
                required
                aria-invalid={error ? true : undefined}
                aria-describedby={error ? "login-error" : undefined}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                aria-invalid={error ? true : undefined}
                aria-describedby={error ? "login-error" : undefined}
              />
            </div>
            <Button type="submit" className="w-full">Sign In</Button>
          </form>

          <div className="text-center text-sm">
            Don&apos;t have an account?{" "}
            <Link href="/auth/register" className="text-primary hover:underline font-medium">
              Register here
            </Link>
          </div>
        </GlassCard>

        {/* One-Click Demo Login Panel */}
        <GlassCard className="p-6">
          <DemoLoginPanel />
        </GlassCard>
      </div>
    </div>
  )
}
