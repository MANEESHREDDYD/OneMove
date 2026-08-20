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
  /** Marks a turn reporting a failed request, so it is announced assertively. */
  isError?: boolean
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
      setMessages(prev => [...prev, { id: Date.now().toString(), role: 'assistant', content: `Error: ${res.error}`, isError: true }])
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
            <Sparkles aria-hidden="true" focusable="false" className="w-5 h-5 text-purple-500" />
          </div>
          <div>
            <h2 className="font-bold">OneMove Intelligence</h2>
            <p className="text-xs text-muted-foreground">GPT-4 Class Forecasting Engine</p>
          </div>
        </div>

        {/*
          Chat History.

          role="log" with aria-live="polite" so each new turn is announced as it
          arrives rather than silently appearing. The speaker is otherwise
          conveyed only by avatar icon, colour and left/right alignment — none of
          which reach a screen reader — so each turn also carries a
          visually-hidden speaker label. A turn that reports a failed request is
          marked role="alert" instead, because it is something the operator has
          to act on.
        */}
        <div
          ref={scrollRef}
          role="log"
          aria-live="polite"
          aria-label="Conversation with OneMove Intelligence"
          className="flex-1 overflow-y-auto p-4 space-y-6"
        >
          {messages.map((msg) => (
            <div
              key={msg.id}
              role={msg.isError ? 'alert' : undefined}
              className={`flex gap-3 max-w-[85%] ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}
            >
              <div aria-hidden="true" className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${msg.role === 'user' ? 'bg-primary/20 text-primary' : 'bg-purple-500/20 text-purple-500'}`}>
                {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>
              <div className={`p-3 rounded-2xl text-sm ${msg.role === 'user' ? 'bg-primary text-primary-foreground rounded-tr-none' : 'bg-background/80 border border-primary/10 rounded-tl-none text-foreground leading-relaxed shadow-sm'}`}>
                <span className="sr-only">
                  {msg.role === 'user'
                    ? 'You said: '
                    : msg.isError
                      ? 'Error from OneMove Intelligence: '
                      : 'OneMove Intelligence said: '}
                </span>
                {msg.content}
              </div>
            </div>
          ))}
          {loading && (
            <div role="status" className="flex gap-3 max-w-[85%]">
              <div aria-hidden="true" className="shrink-0 w-8 h-8 rounded-full bg-purple-500/20 text-purple-500 flex items-center justify-center">
                <Bot className="w-4 h-4" />
              </div>
              <div className="p-4 rounded-2xl bg-background/80 border border-primary/10 rounded-tl-none flex items-center gap-1">
                <span aria-hidden="true" className="w-2 h-2 bg-purple-500/50 rounded-full animate-bounce"></span>
                <span aria-hidden="true" className="w-2 h-2 bg-purple-500/50 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
                <span aria-hidden="true" className="w-2 h-2 bg-purple-500/50 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></span>
                <span className="sr-only">OneMove Intelligence is generating a response.</span>
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-primary/10 bg-background/50 backdrop-blur-sm">
          <div className="relative flex items-center">
            {/*
              The placeholder was doing duty as the label. Placeholder text is
              not an accessible name and disappears as soon as the field has
              content, so the field gets a real <label>; it is visually hidden
              because the surrounding card already reads as a chat composer.
            */}
            <label htmlFor="ai-lab-prompt" className="sr-only">
              Ask OneMove Intelligence
            </label>
            <input
              id="ai-lab-prompt"
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if(e.key === 'Enter') handleSend() }}
              placeholder="Ask the AI about revenue, drivers, or users..."
              aria-describedby="ai-lab-disclaimer"
              className="w-full bg-background border border-primary/20 rounded-full py-3 pl-4 pr-12 focus:outline-none focus:ring-2 focus:ring-purple-500/50 text-foreground shadow-inner"
              disabled={loading}
            />
            <Button
              type="button"
              size="icon"
              variant="ghost"
              /* Icon-only control: without a name it announces as just "button". */
              aria-label="Send message"
              className="absolute right-1 w-10 h-10 rounded-full text-purple-500 hover:bg-purple-500/10 hover:text-purple-600 disabled:opacity-50"
              onClick={handleSend}
              disabled={loading || !input.trim()}
            >
              <Send aria-hidden="true" focusable="false" className="w-4 h-4" />
            </Button>
          </div>
          <p id="ai-lab-disclaimer" className="text-center text-[10px] text-muted-foreground mt-2">
            AI can make mistakes. Verify important platform decisions.
          </p>
        </div>

      </GlassCard>

    </div>
  )
}
