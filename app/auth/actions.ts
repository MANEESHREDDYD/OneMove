'use server'

import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { createClient } from '@/utils/supabase/server'

function getRoleRoute(role: string): string | null {
  switch (role) {
    case 'driver': return '/partner'
    case 'merchant': return '/merchant'
    case 'admin': return '/admin/command-center'
    case 'customer': return '/customer'
    default: return null
  }
}

export async function login(formData: FormData) {
  const supabase = await createClient()
  if (!supabase) {
    redirect('/auth/login?error=Supabase+is+not+configured')
  }

  const email = formData.get('email') as string
  const password = formData.get('password') as string

  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  })

  if (error) {
    return redirect('/auth/login?error=Could+not+authenticate+user')
  }

  // Fetch role from profiles table to determine correct dashboard
  const { data: profile } = await supabase
    .from('profiles')
    .select('role')
    .eq('id', data.user.id)
    .single()

  if (!profile || !profile.role) {
    await supabase.auth.signOut()
    return redirect('/auth/login?error=Role+profile+not+found')
  }

  const route = getRoleRoute(profile.role)
  if (!route) {
    await supabase.auth.signOut()
    return redirect('/auth/login?error=Unknown+role+configuration')
  }

  revalidatePath('/', 'layout')
  redirect(route)
}

export async function demoLogin(email: string, password: string) {
  const supabase = await createClient()
  if (!supabase) {
    redirect('/auth/login?error=Supabase+is+not+configured')
  }

  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  })

  if (error) {
    return redirect('/auth/login?error=Could+not+authenticate+demo+user.+Run+npm+run+seed:auth+first.')
  }

  const { data: profile } = await supabase
    .from('profiles')
    .select('role')
    .eq('id', data.user.id)
    .single()

  if (!profile || !profile.role) {
    await supabase.auth.signOut()
    return redirect('/auth/login?error=Demo+role+profile+not+found.+Run+seed+again.')
  }

  const route = getRoleRoute(profile.role)
  if (!route) {
    await supabase.auth.signOut()
    return redirect('/auth/login?error=Unknown+demo+role+configuration')
  }

  revalidatePath('/', 'layout')
  redirect(route)
}

export async function signup(formData: FormData) {
  const supabase = await createClient()
  if (!supabase) {
    redirect('/auth/register?error=Supabase+is+not+configured')
  }

  const email = formData.get('email') as string
  const password = formData.get('password') as string
  const name = formData.get('name') as string
  const role = formData.get('role') as string || 'customer'

  const { error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: {
        name,
        role
      }
    }
  })

  if (error) {
    return redirect('/auth/register?error=Could+not+create+user')
  }

  const route = getRoleRoute(role)
  if (!route) {
    return redirect('/auth/register?error=Invalid+role+specified')
  }

  revalidatePath('/', 'layout')
  redirect(route)
}

export async function signout() {
  const supabase = await createClient()
  if (!supabase) {
    redirect('/auth/login?error=Supabase+is+not+configured')
  }
  await supabase.auth.signOut()
  revalidatePath('/', 'layout')
  redirect('/')
}
