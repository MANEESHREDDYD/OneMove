import Link from 'next/link'
import { ArrowRight, ShieldCheck, Database, BrainCircuit, Activity, Smartphone, Server, TestTube, Target, FileText } from 'lucide-react'

export default function ShowcasePage() {
  return (
    <div className="min-h-screen bg-slate-50">
      {/* Navigation */}
      <nav className="bg-white border-b sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="text-2xl font-black bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">
              OneMove
            </div>
            <div className="flex gap-4">
              <Link href="/auth/login" className="text-gray-600 hover:text-gray-900 px-3 py-2 text-sm font-medium">Sign In</Link>
              <Link href="/admin/command-center" className="bg-purple-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple-700 transition">Command Center</Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="relative overflow-hidden bg-white pt-16 pb-32 border-b">
        <div className="absolute inset-y-0 right-0 w-1/2 bg-gray-50 rounded-l-full transform translate-x-1/3 -translate-y-1/4 opacity-20"></div>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="text-center max-w-3xl mx-auto">
            <span className="px-3 py-1 rounded-full bg-indigo-100 text-indigo-800 text-xs font-bold uppercase tracking-wide mb-6 inline-block">
              Private Localhost Portfolio Demo: GO
            </span>
            <h1 className="text-5xl font-black text-gray-900 tracking-tight mb-6">
              The Next-Generation <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-indigo-600">Marketplace Intelligence</span> Platform
            </h1>
            <p className="text-xl text-gray-600 mb-10 leading-relaxed">
              OneMove is not just a UI. It's a full-stack, four-sided marketplace powered by a real-time data orchestration engine, an MLOps platform, and deterministic AI intelligence.
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <Link href="/admin/architecture" className="bg-gray-900 text-white px-8 py-3 rounded-lg font-bold hover:bg-gray-800 transition flex items-center shadow-lg">
                View Architecture <ArrowRight className="ml-2 w-5 h-5" />
              </Link>
              <Link href="#demo-credentials" className="bg-white text-gray-900 border-2 border-gray-200 px-8 py-3 rounded-lg font-bold hover:border-gray-300 transition shadow-sm">
                Get Demo Credentials
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        
        {/* Value Proposition Grid */}
        <div className="grid md:grid-cols-3 gap-8 mb-20">
          <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
            <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center mb-6">
              <Database className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold mb-3">Data Engineering</h3>
            <p className="text-gray-600">Real-time event streams, automated quality checks, and a comprehensive Metric Store built directly on top of Postgres.</p>
          </div>
          <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
            <div className="w-12 h-12 bg-purple-100 text-purple-600 rounded-xl flex items-center justify-center mb-6">
              <BrainCircuit className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold mb-3">ML/AI Intelligence</h3>
            <p className="text-gray-600">Deterministic scoring algorithms for demand forecasting, dispatch routing, and automated Ops insights.</p>
          </div>
          <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-100">
            <div className="w-12 h-12 bg-green-100 text-green-600 rounded-xl flex items-center justify-center mb-6">
              <TestTube className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold mb-3">MLOps & Experiments</h3>
            <p className="text-gray-600">Full A/B multivariate testing simulation platform and comprehensive pipeline logging for total system observability.</p>
          </div>
        </div>

        {/* Feature Deep Dives */}
        <div className="space-y-24 mb-24">
          
          {/* Marketplace */}
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <span className="text-purple-600 font-bold tracking-wider uppercase text-sm mb-2 block">Four-Sided Dynamics</span>
              <h2 className="text-3xl font-bold mb-4">Role-Based Marketplace</h2>
              <p className="text-gray-600 text-lg mb-6">A single unified backend handling diverse entities securely. From a polymorphic <code>orders.service_type</code> system handling food, rides, and courier jobs, to localized merchant dashboards and real-time partner geolocation tracking.</p>
              <ul className="space-y-3 mb-8">
                <li className="flex items-center text-gray-700"><Smartphone className="w-5 h-5 text-purple-500 mr-3" /> Customer B2C Interface</li>
                <li className="flex items-center text-gray-700"><Server className="w-5 h-5 text-purple-500 mr-3" /> Merchant B2B Fulfillment</li>
                <li className="flex items-center text-gray-700"><Activity className="w-5 h-5 text-purple-500 mr-3" /> Partner Gig-Economy Dispatch</li>
                <li className="flex items-center text-gray-700"><Target className="w-5 h-5 text-purple-500 mr-3" /> Admin God-View Governance</li>
              </ul>
            </div>
            <div className="bg-gradient-to-tr from-purple-100 to-indigo-50 rounded-2xl p-8 shadow-inner border border-purple-100 h-full flex flex-col justify-center space-y-4">
              <Link href="/customer" className="bg-white p-4 rounded-xl shadow-sm border hover:shadow-md transition flex justify-between items-center group">
                <span className="font-bold">Open Customer Demo</span>
                <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-purple-600" />
              </Link>
              <Link href="/merchant" className="bg-white p-4 rounded-xl shadow-sm border hover:shadow-md transition flex justify-between items-center group">
                <span className="font-bold">Open Merchant Demo</span>
                <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-purple-600" />
              </Link>
              <Link href="/driver" className="bg-white p-4 rounded-xl shadow-sm border hover:shadow-md transition flex justify-between items-center group">
                <span className="font-bold">Open Partner Demo</span>
                <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-purple-600" />
              </Link>
            </div>
          </div>

          {/* Architecture & Intelligence */}
          <div className="grid md:grid-cols-2 gap-12 items-center flex-row-reverse">
            <div className="md:order-2">
              <span className="text-indigo-600 font-bold tracking-wider uppercase text-sm mb-2 block">Enterprise Grade</span>
              <h2 className="text-3xl font-bold mb-4">Security, QA & Analytics</h2>
              <p className="text-gray-600 text-lg mb-6">Built with zero-trust principles. Every row of data is protected by deep PostgreSQL Row Level Security (RLS). The application is hardened by extensive Playwright End-to-End flows, security matrix tests, and Vitest unit coverage.</p>
              <div className="flex gap-4">
                <Link href="/admin/command-center" className="bg-indigo-600 text-white px-6 py-3 rounded-lg font-bold hover:bg-indigo-700 transition">
                  Open Admin Command Center
                </Link>
                <Link href="/admin/mlops" className="bg-white border-2 border-indigo-100 text-indigo-700 px-6 py-3 rounded-lg font-bold hover:bg-indigo-50 transition">
                  View Intelligence Platform
                </Link>
              </div>
            </div>
            <div className="bg-slate-900 rounded-2xl p-8 text-slate-300 shadow-xl md:order-1 font-mono text-sm">
              <div className="mb-4 flex items-center text-slate-400"><ShieldCheck className="w-4 h-4 mr-2"/> Stack Highlights</div>
              <ul className="space-y-3">
                <li><span className="text-blue-400">Framework:</span> Next.js 14 App Router (TS)</li>
                <li><span className="text-blue-400">Database:</span> Supabase PostgreSQL</li>
                <li><span className="text-blue-400">Auth:</span> Supabase JWT + Middleware</li>
                <li><span className="text-blue-400">Styling:</span> Tailwind CSS + Shadcn</li>
                <li><span className="text-blue-400">Testing:</span> Playwright, Vitest, Artillery</li>
                <li><span className="text-blue-400">Data:</span> Metric Store + Cron Jobs</li>
              </ul>
            </div>
          </div>

        </div>

        {/* Demo Credentials Section */}
        <div id="demo-credentials" className="bg-white rounded-3xl shadow-xl border border-gray-200 overflow-hidden">
          <div className="bg-gray-900 px-8 py-6 flex items-center">
            <FileText className="w-6 h-6 text-yellow-400 mr-3" />
            <h2 className="text-2xl font-bold text-white">Demo Credentials</h2>
          </div>
          <div className="p-8">
            <p className="text-gray-600 mb-8">Use the following predefined credentials to explore the different facets of the OneMove marketplace. Do not use real personal information.</p>
            
            <div className="grid md:grid-cols-2 gap-6">
              <div className="border rounded-xl p-5 bg-gray-50">
                <h3 className="font-bold text-gray-900 mb-4 border-b pb-2">Customer Account</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-gray-500">Email:</span> <code className="bg-white px-2 py-1 rounded border">customer@onemove.demo</code></div>
                  <div className="flex justify-between"><span className="text-gray-500">Password:</span> <code className="bg-white px-2 py-1 rounded border">Demo@12345</code></div>
                </div>
              </div>

              <div className="border rounded-xl p-5 bg-gray-50">
                <h3 className="font-bold text-gray-900 mb-4 border-b pb-2">Merchant Account</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-gray-500">Email:</span> <code className="bg-white px-2 py-1 rounded border">merchant@onemove.demo</code></div>
                  <div className="flex justify-between"><span className="text-gray-500">Password:</span> <code className="bg-white px-2 py-1 rounded border">Demo@12345</code></div>
                </div>
              </div>

              <div className="border rounded-xl p-5 bg-gray-50">
                <h3 className="font-bold text-gray-900 mb-4 border-b pb-2">Partner Account</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-gray-500">Email:</span> <code className="bg-white px-2 py-1 rounded border">partner@onemove.demo</code></div>
                  <div className="flex justify-between"><span className="text-gray-500">Password:</span> <code className="bg-white px-2 py-1 rounded border">Demo@12345</code></div>
                </div>
              </div>

              <div className="border rounded-xl p-5 bg-purple-50 border-purple-100">
                <h3 className="font-bold text-purple-900 mb-4 border-b border-purple-200 pb-2">Admin Account</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-gray-500">Email:</span> <code className="bg-white px-2 py-1 rounded border">admin@onemove.demo</code></div>
                  <div className="flex justify-between"><span className="text-gray-500">Password:</span> <code className="bg-white px-2 py-1 rounded border">Demo@12345</code></div>
                </div>
              </div>
            </div>

            <div className="mt-8 p-4 bg-yellow-50 text-yellow-800 text-sm rounded-lg flex items-start border border-yellow-200">
              <ShieldCheck className="w-5 h-5 mr-3 flex-shrink-0 mt-0.5" />
              <p><strong>Note:</strong> Public production deployment is not yet approved. This environment is running as a private localhost portfolio demo. Synthetic data generated by ML pipelines and experiments may occasionally be refreshed.</p>
            </div>
          </div>
        </div>

      </div>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-8 text-center border-t border-gray-800">
        <p>OneMove Intelligence Platform © {new Date().getFullYear()}</p>
      </footer>
    </div>
  )
}
