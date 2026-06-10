import { createClient } from '@/utils/supabase/server'
import { SetupRequired } from '@/components/common/SetupRequired'
import { Layers, Server, Shield, Activity, Database, BrainCircuit, GitMerge, AlertCircle, TrendingUp, CheckCircle2 } from 'lucide-react'

export default async function ArchitecturePage() {
  const supabase = await createClient()
  if (!supabase) return <SetupRequired />

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-12">
      <div className="flex items-center mb-8">
        <Layers className="w-8 h-8 text-indigo-600 mr-3" />
        <div>
          <h1 className="text-3xl font-bold">Technical Architecture Overview</h1>
          <p className="text-gray-500">System blueprint and data orchestration flows.</p>
        </div>
      </div>

      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-r-md">
        <div className="flex">
          <div className="flex-shrink-0">
            <AlertCircle className="h-5 w-5 text-yellow-400" />
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-800">Deployment Status</h3>
            <div className="mt-2 text-sm text-yellow-700">
              <p>Private localhost portfolio demo: <strong>GO</strong></p>
              <p>Public production deployment: <strong>NOT YET APPROVED</strong></p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Marketplace Flow */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h2 className="text-xl font-bold flex items-center mb-6">
            <GitMerge className="w-5 h-5 mr-2 text-blue-500" /> Marketplace Orchestration Flow
          </h2>
          <div className="space-y-4">
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 text-sm">
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-blue-700">1. Customer</span>
                <span className="text-xs text-gray-500">Places Polymorphic Order (Food/Ride/Courier)</span>
              </div>
              <div className="h-6 border-l-2 border-dashed border-blue-300 ml-4 my-1"></div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-purple-700">2. Supabase DB</span>
                <span className="text-xs text-gray-500">Realtime-ready refresh/fallback behavior</span>
              </div>
              <div className="h-6 border-l-2 border-dashed border-blue-300 ml-4 my-1"></div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-green-700">3. Merchant</span>
                <span className="text-xs text-gray-500">Accepts & Prepares Order</span>
              </div>
              <div className="h-6 border-l-2 border-dashed border-blue-300 ml-4 my-1"></div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-orange-700">4. Partner</span>
                <span className="text-xs text-gray-500">Dispatched via ML Engine, Completes Delivery</span>
              </div>
              <div className="h-6 border-l-2 border-dashed border-blue-300 ml-4 my-1"></div>
              <div className="flex items-center justify-between">
                <span className="font-bold text-indigo-700">5. Admin / Data</span>
                <span className="text-xs text-gray-500">Metrics aggregated, MLOps logged</span>
              </div>
            </div>
          </div>
        </div>

        {/* Security & RLS */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h2 className="text-xl font-bold flex items-center mb-6">
            <Shield className="w-5 h-5 mr-2 text-red-500" /> Deep Multi-Tenant Security (RLS)
          </h2>
          <p className="text-sm text-gray-600 mb-4">PostgreSQL Row Level Security ensures data isolation at the DB layer, eliminating application-layer leakage risks.</p>
          <div className="space-y-3">
            <div className="flex justify-between items-center p-3 bg-red-50 rounded text-sm">
              <span className="font-semibold">Customer Policy</span>
              <span className="text-gray-600">Read/Write: ONLY `auth.uid() = customer_id`</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-red-50 rounded text-sm">
              <span className="font-semibold">Merchant Policy</span>
              <span className="text-gray-600">Read/Write: ONLY `auth.uid() = merchant_id`</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-red-50 rounded text-sm">
              <span className="font-semibold">Partner Policy</span>
              <span className="text-gray-600">Read: Dispatched Jobs | Write: Location</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-gray-800 text-white rounded text-sm">
              <span className="font-semibold">Admin Policy</span>
              <span className="text-gray-300">Bypass RLS (`role = &apos;admin&apos;`)</span>
            </div>
          </div>
        </div>

        {/* Data Pipeline & Metric Store */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h2 className="text-xl font-bold flex items-center mb-6">
            <Database className="w-5 h-5 mr-2 text-indigo-500" /> Data Pipeline & Metric Store
          </h2>
          <div className="relative pt-4">
            <div className="flex items-center justify-between bg-indigo-50 p-3 rounded mb-4 text-sm">
              <span className="font-semibold">Raw Events</span>
              <span className="text-gray-500">Orders, Tickets, Sessions</span>
            </div>
            <div className="text-center text-indigo-300 mb-2">↓ Aggregation Scripts (Cron)</div>
            <div className="flex items-center justify-between bg-indigo-100 p-3 rounded mb-4 text-sm">
              <span className="font-semibold">Metric Store</span>
              <span className="text-gray-500">Daily Snapshots, LTV, AOV</span>
            </div>
            <div className="text-center text-indigo-300 mb-2">↓ Data Quality Assertions</div>
            <div className="flex items-center justify-between bg-indigo-200 p-3 rounded text-sm">
              <span className="font-semibold">Analytics UI</span>
              <span className="text-gray-700">Admin Command Center Views</span>
            </div>
          </div>
        </div>

        {/* ML & Intelligence Platform */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h2 className="text-xl font-bold flex items-center mb-6">
            <BrainCircuit className="w-5 h-5 mr-2 text-purple-500" /> Deterministic Intelligence Flow
          </h2>
          <p className="text-sm text-gray-600 mb-4">Rule-based scoring, explainable outputs, and tracked execution.</p>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="bg-purple-50 p-3 rounded border border-purple-100">
                <span className="font-bold block mb-1">Inputs</span>
                <ul className="text-gray-600 list-disc list-inside">
                  <li>Metric Store Data</li>
                  <li>Live Geolocation</li>
                  <li>Order Velocity</li>
                </ul>
              </div>
              <div className="bg-purple-50 p-3 rounded border border-purple-100">
                <span className="font-bold block mb-1">Scoring Models</span>
                <ul className="text-gray-600 list-disc list-inside">
                  <li>Demand Forecasting</li>
                  <li>Dispatch Optimizer</li>
                  <li>Risk / Fraud Scoring</li>
                </ul>
              </div>
            </div>
            <div className="bg-gray-900 text-purple-200 p-3 rounded text-sm text-center">
              ↓ Logs to <code>ml_pipeline_runs</code> for MLOps tracking
            </div>
          </div>
        </div>
      </div>

      {/* QA, Performance, and Roadmap */}
      <div className="grid lg:grid-cols-3 gap-8">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h3 className="font-bold text-lg mb-4 flex items-center"><CheckCircle2 className="w-4 h-4 mr-2 text-green-500"/> QA & Testing Matrix</h3>
          <ul className="space-y-2 text-sm text-gray-600">
            <li><strong>End-to-End:</strong> Playwright multi-role smoke tests covering core transaction paths.</li>
            <li><strong>Security:</strong> Playwright RLS boundary validation tests.</li>
            <li><strong>Unit:</strong> Vitest suite for business logic utilities.</li>
            <li><strong>Performance:</strong> Artillery load tests for concurrent `/auth` and `/api/dispatch` endpoints.</li>
          </ul>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h3 className="font-bold text-lg mb-4 flex items-center"><TrendingUp className="w-4 h-4 mr-2 text-blue-500"/> Known Limitations</h3>
          <ul className="space-y-2 text-sm text-gray-600">
            <li>Playwright <code>Simulate Traffic</code> test can time out (&gt;30s) on low-end CI workers due to intense synthetic data generation.</li>
            <li>Intelligence is currently deterministic (rule-based scripts) rather than a trained neural network.</li>
            <li>PostgREST schema cache occasionally requires manual reload after complex CLI migrations.</li>
          </ul>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
          <h3 className="font-bold text-lg mb-4 flex items-center"><Server className="w-4 h-4 mr-2 text-indigo-500"/> Future Roadmap</h3>
          <ul className="space-y-2 text-sm text-gray-600">
            <li>Migrate deterministic scoring to Python/FastAPI microservices.</li>
            <li>Implement Redis cache layer for high-velocity reads (showcase menu loading).</li>
            <li>Containerize frontend application using Docker for Kubernetes orchestration.</li>
            <li>Add full Stripe payment gateway integration (currently mocked).</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
