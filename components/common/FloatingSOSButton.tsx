'use client'

import { useState } from 'react'
import { AlertTriangle, PhoneCall, X } from 'lucide-react'
import { Button } from '../ui/button'

export function FloatingSOSButton() {
  const [isOpen, setIsOpen] = useState(false)
  const [sosTriggered, setSosTriggered] = useState(false)

  if (sosTriggered) {
    return (
      <div className="fixed bottom-6 right-6 z-50 animate-in slide-in-from-bottom-5">
        {/*
          An emergency call being placed is the single most important state
          change in the app. role="alert" makes it interrupt whatever the
          screen reader is currently saying.
        */}
        <div role="alert" className="bg-destructive text-destructive-foreground p-4 rounded-2xl shadow-2xl shadow-destructive/50 flex flex-col items-center gap-3 w-64 border border-destructive-foreground/20">
          <div aria-hidden="true" className="bg-destructive-foreground/20 p-3 rounded-full animate-pulse">
            <PhoneCall className="w-8 h-8 text-white" />
          </div>
          <div className="text-center">
            <p className="font-black text-lg">911 Contacted</p>
            <p className="text-xs opacity-90">Live location sharing active. Help is on the way.</p>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="w-full mt-2 bg-transparent border-white/30 hover:bg-white/10 text-white"
            onClick={() => {
              setSosTriggered(false)
              setIsOpen(false)
            }}
          >
            Cancel Alert
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {isOpen && (
        <div
          id="sos-toolkit"
          role="group"
          aria-labelledby="sos-toolkit-heading"
          className="absolute bottom-16 right-0 mb-4 bg-background/95 backdrop-blur-md p-4 rounded-2xl shadow-2xl border border-destructive/20 w-64 animate-in slide-in-from-bottom-2 fade-in"
        >
          <div className="flex items-center justify-between mb-3">
            <h3 id="sos-toolkit-heading" className="font-bold text-destructive flex items-center gap-2">
              <AlertTriangle aria-hidden="true" focusable="false" className="w-4 h-4" /> Safety Toolkit
            </h3>
            {/* Icon-only: announced as an unnamed "button" without this. */}
            <button
              type="button"
              aria-label="Close safety toolkit"
              onClick={() => setIsOpen(false)}
              className="text-muted-foreground hover:text-foreground"
            >
              <X aria-hidden="true" focusable="false" className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-muted-foreground mb-4">
            If you feel unsafe or have been involved in an incident, swipe to trigger an emergency response.
          </p>
          <Button
            type="button"
            className="w-full bg-destructive hover:bg-destructive/90 text-white font-bold h-12 text-lg animate-pulse"
            onClick={() => setSosTriggered(true)}
          >
            SOS EMERGENCY
          </Button>
        </div>
      )}

      {/*
        The only trigger for the safety toolkit, and it was an unnamed icon
        button — a screen reader user had no way to find the emergency control.
        aria-expanded/aria-controls describe the disclosure it operates.
      */}
      <button
        type="button"
        aria-label="Safety toolkit and emergency SOS"
        aria-expanded={isOpen}
        aria-controls="sos-toolkit"
        onClick={() => setIsOpen(!isOpen)}
        className="w-14 h-14 bg-destructive text-white rounded-full flex items-center justify-center shadow-lg shadow-destructive/30 hover:bg-destructive/90 transition-transform hover:scale-105 active:scale-95"
      >
        <AlertTriangle aria-hidden="true" focusable="false" className="w-6 h-6" />
      </button>
    </div>
  )
}
