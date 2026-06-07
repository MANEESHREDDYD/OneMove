# OneMove: Portfolio Project Summary

**Private localhost portfolio demo: GO**
**Public production deployment: NOT YET APPROVED**

## One-line Summary
OneMove is a full-stack, four-sided marketplace super-app combining rides, food, grocery, and courier services, powered by a real-time data orchestration and deterministic ML/AI intelligence platform.

## Problem Solved
Managing a multi-vertical marketplace requires orchestrating complex lifecycles across Customers, Merchants, Partners (Drivers), and Admins. OneMove solves this by centralizing role-based access, event-driven data pipelines, and intelligent routing into a single, highly performant platform.

## Why it is Unique
OneMove is not just a UI layer; it is an end-to-end data product. It features a complete metric store, MLOps logging, A/B testing framework, and deterministic AI assistants natively integrated, moving beyond a simple CRUD app to showcase advanced production engineering patterns.

## Marketplace Roles
- **Customer**: Browses services, places polymorphic orders, tracks deliveries, submits AI-routed support tickets.
- **Merchant**: Manages inventory, fulfills orders, views localized analytics and dynamic ML insights.
- **Partner (Courier/Driver)**: Accepts dispatched jobs, updates real-time geolocation, manages active deliveries.
- **Admin**: Has a platform-wide operational view, managing risk, running A/B experiments, reviewing ML pipelines, and acting on Ops Assistant recommendations.

## Advanced Intelligence Features
- **Deterministic ML/AI Intelligence**: Explainable, rule-based logic (no fake LLM APIs) for demand forecasting, dispatch optimization, and risk modeling.
- **MLOps Pipeline Logging**: Every ML run is tracked with execution times, statuses, and performance logs.
- **A/B Experimentation Platform**: Real-time traffic simulation and conversion tracking for multivariate tests.
- **Admin Ops Assistant**: NLP-like interface generating prioritized, actionable insights from the metric store.

## Tech Stack
- **Frontend & Routing**: Next.js 14+ App Router, TypeScript, Tailwind CSS, Shadcn UI
- **Backend & Database**: Supabase PostgreSQL, Supabase Auth, Row Level Security, Next.js Server Actions
- **Security**: Deep Multi-Tenant Row Level Security (RLS)
- **Data Engineering**: Real-time subscriptions, polymorphic schema design, Metric Store
- **Testing**: Playwright (E2E & Security), Vitest (Unit), Artillery (Performance)

## Engineering Skills Demonstrated
- Full-stack product engineering and UI/UX design
- Advanced backend database architecture and RLS
- Data pipelines and Analytics engineering
- ML scoring and deterministic AI system design
- MLOps and Experimentation methodologies
- Secure multi-tenant systems integration
- Rigorous testing discipline (E2E, Unit, Performance)

## Best Demo Routes
1. `/showcase` - The unified landing page and demo hub.
2. `/admin/architecture` - The technical blueprint for engineering deep-dives.
3. `/admin/command-center` - The live operational view of the marketplace.
4. `/admin/experiments` - The active A/B testing and simulation engine.
