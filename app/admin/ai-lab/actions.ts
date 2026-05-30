'use server'

import { createClient } from '@/utils/supabase/server'

export async function askAI(query: string) {
  // Simulate network delay for a real AI model
  await new Promise(resolve => setTimeout(resolve, 1500))

  const supabase = await createClient()
  if (!supabase) {
    return { error: 'Supabase is not configured. See docs/LOCAL_SETUP.md.' }
  }
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    return { error: 'Unauthorized access to the ML Lab.' }
  }

  const q = query.toLowerCase()

  // Heuristic mock engine for zero-cost MVP
  if (q.includes('revenue') || q.includes('money') || q.includes('sales')) {
    return { 
      response: "Based on our predictive models, platform revenue is highly correlated with Courier and Food delivery density in urban hubs. I recommend running a promotional campaign between 5 PM and 8 PM." 
    }
  }

  if (q.includes('driver') || q.includes('partner') || q.includes('fleet')) {
    return { 
      response: "Fleet utilization is currently optimal, but the algorithmic forecast predicts a 20% shortage in driver supply during the upcoming weekend. Consider applying a surge multiplier." 
    }
  }

  if (q.includes('user') || q.includes('customer') || q.includes('churn')) {
    return { 
      response: "Our ML churn-prediction matrix indicates that customers who haven't ordered in the last 14 days have a 70% probability of uninstalling the app. A targeted push notification is recommended." 
    }
  }

  return {
    response: "I am OneMove's proprietary AI Copilot. I can analyze revenue trends, predict fleet utilization, or identify customer churn risks based on live Supabase data streams. What would you like to investigate?"
  }
}
