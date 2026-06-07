# OneMove: Demo Recording Outline (3-5 Minutes)

**Pre-requisites:**
- Run `npm run intelligence:refresh` and `npm run experiments:simulate` beforehand so data is populated.
- Have tabs pre-opened for the Showcase, Customer, Merchant, Partner, and Admin views.

**0:00 - 0:30: The Hook & Introduction**
- Start on the `/showcase` page.
- "Welcome to OneMove. This is a full-stack, four-sided marketplace MVP integrating rides, eats, and courier services. It's built with Next.js and Supabase."
- "I'm going to show you the transactional flow, but the real star of the show is the backend data engineering and intelligence platform."

**0:30 - 1:15: Transactional Flow**
- Switch to the Customer tab.
- "A customer browses and places an order. Because of the polymorphic database schema, this easily handles diverse service types."
- Switch to the Merchant tab -> Show order appearing.
- Switch to the Partner tab -> Show dispatch assignment.
- "These state changes trigger realtime-ready refreshes, synchronizing the four-sided marketplace."

**1:15 - 2:00: Data Platform & Analytics**
- Switch to the Admin Data Platform tab.
- "Handling this data requires rigorous pipelines. Here you can see the automated ETL scripts aggregating raw events into daily snapshots."
- Switch to Analytics tab.
- "Because we process this into a custom Metric Store, we get instantaneous, real-time observability over business health."

**2:00 - 3:00: Intelligence & MLOps**
- Switch to the AI Lab / Risk Center.
- "We don't rely on black-box LLMs. I built deterministic, explainable scoring algorithms for Demand Forecasting and Risk Modeling."
- Switch to MLOps tab.
- "Every time these scripts run, they log their execution duration and row counts to an MLOps pipeline for full observability."
- Switch to Experiments tab.
- "We even have a fully functional A/B testing simulator that calculates directional revenue and conversion winners."

**3:00 - 3:45: Security & Architecture**
- Switch to the Architecture page (`/admin/architecture`).
- "None of this works without enterprise-grade security. Every row in the database is isolated using deep PostgreSQL Row Level Security (RLS)."
- "I validate this using rigorous Playwright End-to-End security matrix tests to guarantee data boundaries."

**3:45 - 4:00: Outro**
- Switch back to `/showcase`.
- "OneMove demonstrates portfolio-ready full-stack engineering, from schema design and ETL pipelines to MLOps and strict security enforcement. Thank you."
