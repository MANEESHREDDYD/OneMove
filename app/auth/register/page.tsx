import Link from "next/link"
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { signup } from "../actions"

export default async function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>
}) {
  const { error } = await searchParams

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <GlassCard className="w-full max-w-md p-8 space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-bold tracking-tight">Create an Account</h1>
          <p className="text-muted-foreground">Join OneMove and explore your city</p>
        </div>

        <form className="space-y-4" action={signup}>
          {/* See the matching comment in app/auth/login/page.tsx. */}
          {error && (
            <div id="register-error" role="alert" className="text-sm font-medium text-red-400 bg-red-500/10 p-3 rounded-md">
              {error}
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="name">Full Name</Label>
            <Input
              id="name"
              name="name"
              autoComplete="name"
              placeholder="John Doe"
              required
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? "register-error" : undefined}
            />
          </div>
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
              aria-describedby={error ? "register-error" : undefined}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              name="password"
              type="password"
              autoComplete="new-password"
              required
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? "register-error" : undefined}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="role">I want to</Label>
            {/*
              focus-visible:outline-none here removes the outline and replaces it
              with a ring-1, which is a weaker indicator than the browser default.
              Widened to ring-2 with an offset so the focused control is
              unambiguous (WCAG 2.4.7).
            */}
            <select
              id="role"
              name="role"
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50"
              required
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? "register-error" : undefined}
            >
              <option value="customer" className="bg-background text-foreground">Order & Ride</option>
              <option value="driver" className="bg-background text-foreground">Drive & Deliver</option>
              <option value="merchant" className="bg-background text-foreground">Sell on OneMove</option>
            </select>
          </div>
          <Button type="submit" className="w-full">Create Account</Button>
        </form>

        <div className="text-center text-sm">
          Already have an account?{" "}
          <Link href="/auth/login" className="text-primary hover:underline font-medium">
            Sign In
          </Link>
        </div>
      </GlassCard>
    </div>
  )
}
