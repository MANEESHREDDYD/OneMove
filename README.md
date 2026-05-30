# OneMove: The US-First Super-App Ecosystem

![OneMove](https://img.shields.io/badge/OneMove-Super_App-black?style=for-the-badge&logo=next.js)
![Version](https://img.shields.io/badge/Version-1.0.0-blue?style=for-the-badge)
![Supabase](https://img.shields.io/badge/Supabase-Database-green?style=for-the-badge&logo=supabase)

**OneMove** is a portfolio-grade, zero-cost MVP Progressive Web Application (PWA) designed to simulate a massive scale, US-first gig-economy Super-App. Built entirely on Next.js 15, Tailwind CSS, and Supabase, it consolidates Rides, Eats, Grocery, and Courier services into a single unified platform.

## 🚀 Ecosystem Overview

OneMove is designed with role-based partitioning to support a multi-sided marketplace:

1. **The Customer Hub (`/customer`)**:
   - Order Food (Eats), hail Rides, buy Groceries, or dispatch Couriers.
   - Beautiful, animated cart interactions and live order history routing.
2. **The Partner Fleet (`/driver`)**:
   - Centralized driver dashboard to toggle online status.
   - Integrated mapping (mocked for zero-cost) and live-job acceptance queue.
3. **The Merchant Portal (`/merchant`)**:
   - Storefront command center for restaurants and grocers.
   - Real-time live order queues, history analytics, and store toggles.
4. **The God Mode Command Center (`/admin/command-center`)**:
   - Global view of every order across all 4 verticals.
   - Dynamic KPIs: Platform GMV, Active User calculations, and Order Volume.
   - Includes **Analytics Engine** (Recharts) and **ML/AI Lab** (Simulated GPT-4 Copilot).
   - Includes **Trust & Safety Center** (Compliance management and emergency triggers).

## 🛠 Tech Stack

- **Framework**: Next.js 15 (App Router, Server Actions, Server Components)
- **Styling**: Tailwind CSS (Native dark mode, Glassmorphism design system)
- **UI Components**: `shadcn/ui` core + `lucide-react` + `recharts`
- **Database & Auth**: Supabase (PostgreSQL, Row Level Security)
- **Deployment & Architecture**: Progressive Web App (PWA) configured for mobile installation. Zero-cost serverless Edge runtime.

## 📦 Running Locally

1. **Clone the Repository**
   ```bash
   git clone https://github.com/MANEESHREDDYD/OneMove.git
   cd OneMove
   ```

2. **Install Dependencies**
   ```bash
   npm install
   ```

3. **First-time Supabase Setup**
   The project requires a configured Supabase database. Follow the complete guide in `docs/SUPABASE_SETUP.md`.
   
   Quick checklist:
   ```bash
   cp .env.local.example .env.local
   # (Fill in .env.local with your keys)
   npm run validate:env
   npm run test:supabase
   npm run lint
   npm run typecheck
   npm test
   npm run build
   npm run dev
   ```

## 🛡 Strict QA Pipeline

OneMove enforces a strict zero-warning policy on all code before merges. Our CI/CD pipeline validates:
- `npm run lint`: ESLint rules enforced.
- `npm run typecheck`: Strict TypeScript `tsc --noEmit`.
- `npm run build`: Next.js Turbopack static generation verification.

## 🌐 Security & Trust
- **Role-Based Routing**: Next.js Middleware automatically intercepts routes to protect `/admin`, `/merchant`, and `/driver` portals based on Supabase JWT tokens.
- **Universal SOS**: The platform features a ubiquitous floating SOS button ensuring real-time simulated emergency access for all users.

---

*Designed and engineered iteratively across 19 strict developmental checkpoints.*
