'use client'

import { useTransition } from 'react'
import { demoLogin } from '@/app/auth/actions'
import { User, Truck, Store, Shield, Loader2 } from 'lucide-react'

const DEMO_ACCOUNTS = [
  { email: 'customer@onemove.demo', password: 'Demo@12345', label: 'Login as Customer', icon: User, color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/30 hover:bg-blue-500/20' },
  { email: 'partner@onemove.demo', password: 'Demo@12345', label: 'Login as Partner / Driver', icon: Truck, color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/30 hover:bg-green-500/20' },
  { email: 'merchant@onemove.demo', password: 'Demo@12345', label: 'Login as Merchant', icon: Store, color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/30 hover:bg-orange-500/20' },
  { email: 'admin@onemove.demo', password: 'Demo@12345', label: 'Login as Admin', icon: Shield, color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/30 hover:bg-purple-500/20' },
]

export function DemoLoginPanel() {
  const [isPending, startTransition] = useTransition()

  const handleDemoLogin = (email: string, password: string) => {
    startTransition(async () => {
      await demoLogin(email, password)
    })
  }

  return (
    <div className="space-y-3">
      <div className="text-center">
        <p className="text-xs uppercase tracking-widest font-bold text-muted-foreground mb-1">Quick Demo Access</p>
        <div className="h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" />
      </div>
      <div className="grid grid-cols-2 gap-2">
        {DEMO_ACCOUNTS.map(acct => {
          const Icon = acct.icon
          return (
            <button
              key={acct.email}
              onClick={() => handleDemoLogin(acct.email, acct.password)}
              disabled={isPending}
              className={`p-3 rounded-xl border text-left transition-all duration-200 ${acct.bg} disabled:opacity-50 group`}
            >
              <Icon className={`w-5 h-5 mb-2 ${acct.color} group-hover:scale-110 transition-transform`} />
              <p className="text-xs font-bold leading-tight">{acct.label}</p>
            </button>
          )
        })}
      </div>
      {isPending && (
        <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" /> Signing in...
        </div>
      )}
    </div>
  )
}
