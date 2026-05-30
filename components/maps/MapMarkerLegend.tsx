"use client"

import React from 'react'

export function MapMarkerLegend() {
  return (
    <div className="absolute bottom-4 right-4 bg-background/90 backdrop-blur-md p-4 rounded-lg shadow-lg border text-sm z-[1000] space-y-2">
      <h4 className="font-semibold mb-2">Live Map Legend</h4>
      <div className="grid grid-cols-2 gap-x-4 gap-y-2">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-blue-500 border border-white"></div>
          <span>Active Drivers</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500 border border-white"></div>
          <span>Active Rides</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-orange-500 border border-white"></div>
          <span>Eats Orders</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-purple-500 border border-white"></div>
          <span>Grocery Orders</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-cyan-500 border border-white"></div>
          <span>Courier Jobs</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500 opacity-50"></div>
          <span>High Demand</span>
        </div>
      </div>
    </div>
  )
}
