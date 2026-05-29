'use client'

import { useState, useRef, useEffect } from 'react'
import { GlassCard } from "@/components/common/GlassCard"
import { Button } from "@/components/ui/button"
import { askAI } from "./actions"
import { Sparkles, Send, User, Bot } from "lucide-react"

type Message = {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export function AILabClient() {
  const [messages, setMessages] = useState<Message[]>([{
    id: '1',
    role: 'assistant',
    content: "Welcome to the OneMove ML/AI Lab. I am your generative Copilot. Ask me to analyze platform metrics, predict fleet trends, or assess user churn."
  }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, loading])

  async function handleSend() {
    if (!input.trim() || loading) return

    const userMsg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { id: Date.now().toString(), role: 'user', content: userMsg }])
    
    setLoading(true)
    
    const res = await askAI(userMsg)
    
    setLoading(false)
    if (res.error) {
      setMessages(prev => [...prev, { id: Date.now().toString(), role: 'assistant', content: `Error: ${res.error}` }])
    } else if (res.response) {
      setMessages(prev => [...prev, { id: Date.now().toString(), role: 'assistant', content: res.response }])
    }
  }

  return (
    <div className="space-y-6 pb-20 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      <GlassCard className="flex flex-col h-[600px] max-h-[70vh] border-t-4 border-t-purple-500 overflow-hidden relative">
        <div className="absolute top-0 right-0 w-64 h-64 bg-purple-500/10 rounded-bl-full -z-10" />
        
        {/* Chat Header */}
        <div className="p-4 border-b border-primary/10 flex items-center gap-3">
          <div className="bg-purple-500/20 p-2 rounded-lg">
            <Sparkles className="w-5 h-5 text-purple-500" />
          </div>
          <div>
            <h2 className="font-bold">OneMove Intelligence</h2>
            <p className="text-xs text-muted-foreground">GPT-4 Class Forecasting Engine</p>
          </div>
        </div>

        {/* Chat History */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-6">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-3 max-w-[85%] ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}>
              <div className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${msg.role === 'user' ? 'bg-primary/20 text-primary' : 'bg-purple-500/20 text-purple-500'}`}>
                {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>
              <div className={`p-3 rounded-2xl text-sm ${msg.role === 'user' ? 'bg-primary text-primary-foreground rounded-tr-none' : 'bg-background/80 border border-primary/10 rounded-tl-none text-foreground leading-relaxed shadow-sm'}`}>
                {msg.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex gap-3 max-w-[85%]">
              <div className="shrink-0 w-8 h-8 rounded-full bg-purple-500/20 text-purple-500 flex items-center justify-center">
                <Bot className="w-4 h-4" />
              </div>
              <div className="p-4 rounded-2xl bg-background/80 border border-primary/10 rounded-tl-none flex items-center gap-1">
                <span className="w-2 h-2 bg-purple-500/50 rounded-full animate-bounce"></span>
                <span className="w-2 h-2 bg-purple-500/50 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                <span className="w-2 h-2 bg-purple-500/50 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></span>
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-primary/10 bg-background/50 backdrop-blur-sm">
          <div className="relative flex items-center">
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if(e.key === 'Enter') handleSend() }}
              placeholder="Ask the AI about revenue, drivers, or users..." 
              className="w-full bg-background border border-primary/20 rounded-full py-3 pl-4 pr-12 focus:outline-none focus:ring-2 focus:ring-purple-500/50 text-foreground shadow-inner"
              disabled={loading}
            />
            <Button 
              size="icon" 
              variant="ghost" 
              className="absolute right-1 w-10 h-10 rounded-full text-purple-500 hover:bg-purple-500/10 hover:text-purple-600 disabled:opacity-50"
              onClick={handleSend}
              disabled={loading || !input.trim()}
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
          <p className="text-center text-[10px] text-muted-foreground mt-2">
            AI can make mistakes. Verify important platform decisions.
          </p>
        </div>

      </GlassCard>

    </div>
  )
}
