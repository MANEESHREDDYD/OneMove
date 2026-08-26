'use client'

import * as React from "react"
import { GlassCard } from "@/components/common/GlassCard"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, LineChart, Line
} from 'recharts'
import { PieChart as PieChartIcon, BarChart3, TrendingUp } from "lucide-react"

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6']

/**
 * A chart's meaning lives entirely in the geometry and colour of an SVG. None
 * of that reaches a screen reader, and the colour-to-series mapping is not
 * available to a user who cannot distinguish the hues. Each chart is therefore
 * paired with the same numbers as a real table, exposed to assistive technology
 * but hidden visually (WCAG 1.1.1).
 *
 * The chart itself is deliberately NOT `aria-hidden`: Recharts 3 renders its
 * charts with `accessibilityLayer` on by default, which puts a focusable
 * `tabIndex={0}` element inside. Hiding a focusable element from the
 * accessibility tree is itself a serious violation (`aria-hidden-focus`).
 */
function ChartDataTable({
  id,
  caption,
  columns,
  rows,
}: {
  id: string
  caption: string
  columns: [string, string]
  rows: Array<[string, string]>
}) {
  return (
    <table id={id} className="sr-only">
      <caption>{caption}</caption>
      <thead>
        <tr>
          <th scope="col">{columns[0]}</th>
          <th scope="col">{columns[1]}</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([label, value]) => (
          <tr key={label}>
            <th scope="row">{label}</th>
            <td>{value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

const currency = (value: number) =>
  `$${Number(value ?? 0).toLocaleString('en-US', { maximumFractionDigits: 2 })}`

export function AnalyticsClient({
  trendData,
  revenueData,
  volumeData
}: {
  trendData: { date: string, gmv: number, orders: number }[],
  revenueData: { name: string, revenue: number }[],
  volumeData: { name: string, value: number }[]
}) {
  const volumeTotal = volumeData.reduce((sum, entry) => sum + Number(entry.value ?? 0), 0)

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">

      {/* 7 Day Trend */}
      <GlassCard className="p-6">
        <figure className="m-0" aria-labelledby="chart-gmv-title">
          <figcaption className="flex items-center gap-2 mb-6">
            <TrendingUp aria-hidden="true" focusable="false" className="w-5 h-5 text-primary" />
            <h2 id="chart-gmv-title" className="text-lg font-bold">7-Day GMV Trend</h2>
          </figcaption>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                <XAxis dataKey="date" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#888888" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(value) => `$${value}`} />
                <RechartsTooltip
                  contentStyle={{ backgroundColor: 'rgba(0,0,0,0.9)', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '8px' }}
                  itemStyle={{ color: '#fff', fontWeight: 'bold' }}
                />
                <Line type="monotone" dataKey="gmv" stroke="#10b981" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 8 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <ChartDataTable
            id="chart-gmv-table"
            caption="7-day GMV trend, by date"
            columns={['Date', 'GMV']}
            rows={trendData.map((point) => [point.date, currency(point.gmv)])}
          />
        </figure>
      </GlassCard>

      <div className="grid gap-8 lg:grid-cols-2">
        {/* Revenue Bar Chart */}
        <GlassCard className="p-6">
          <figure className="m-0" aria-labelledby="chart-revenue-title">
            <figcaption className="flex items-center gap-2 mb-6">
              <BarChart3 aria-hidden="true" focusable="false" className="w-5 h-5 text-primary" />
              <h2 id="chart-revenue-title" className="text-lg font-bold">Revenue by Service</h2>
            </figcaption>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={revenueData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                  <XAxis dataKey="name" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#888888" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(value) => `$${value}`} />
                  <RechartsTooltip
                    cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }}
                    contentStyle={{ backgroundColor: 'rgba(0,0,0,0.9)', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '8px' }}
                    itemStyle={{ color: '#fff', fontWeight: 'bold' }}
                  />
                  <Bar dataKey="revenue" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <ChartDataTable
              id="chart-revenue-table"
              caption="Revenue by service"
              columns={['Service', 'Revenue']}
              rows={revenueData.map((entry) => [entry.name, currency(entry.revenue)])}
            />
          </figure>
        </GlassCard>

        {/* Volume Donut Chart */}
        <GlassCard className="p-6">
          <figure className="m-0" aria-labelledby="chart-volume-title">
            <figcaption className="flex items-center gap-2 mb-6">
              <PieChartIcon aria-hidden="true" focusable="false" className="w-5 h-5 text-primary" />
              <h2 id="chart-volume-title" className="text-lg font-bold">Order Volume Distribution</h2>
            </figcaption>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={volumeData}
                    cx="50%"
                    cy="50%"
                    innerRadius={80}
                    outerRadius={110}
                    paddingAngle={5}
                    dataKey="value"
                    stroke="none"
                  >
                    {volumeData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip
                    contentStyle={{ backgroundColor: 'rgba(0,0,0,0.9)', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '8px' }}
                    itemStyle={{ color: '#fff', fontWeight: 'bold' }}
                  />
                  {/*
                    Recharts colours each legend label with its series colour.
                    #8b5cf6 on this card is 4.3:1 — under AA for 12px text — so
                    the label text is rendered in the foreground colour and the
                    series colour is left to the legend swatch, which only has to
                    clear the 3:1 non-text threshold.
                  */}
                  <Legend
                    iconType="circle"
                    wrapperStyle={{ fontSize: '12px', paddingTop: '20px' }}
                    formatter={(value) => <span className="text-foreground">{value}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <ChartDataTable
              id="chart-volume-table"
              caption="Order volume distribution by service"
              columns={['Service', 'Orders']}
              rows={volumeData.map((entry) => [
                entry.name,
                volumeTotal > 0
                  ? `${entry.value} (${((Number(entry.value ?? 0) / volumeTotal) * 100).toFixed(1)}%)`
                  : String(entry.value),
              ])}
            />
          </figure>
        </GlassCard>
      </div>

    </div>
  )
}
