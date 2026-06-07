# Project Limitations and Roadmap

To maintain honesty and technical integrity, the following limitations and planned architectural improvements are explicitly documented for the OneMove platform.

## Current Limitations

1. **Deployment Status:** The application is currently functioning purely as a **Private localhost portfolio demo**. It is not yet approved or configured for public production deployment.
2. **Intelligence Capabilities:** The AI Assistants, Risk Center, and Demand Forecasting models are powered by **deterministic, rule-based scripts**. They are highly explainable MVPs and do not utilize trained Neural Networks or paid LLM APIs.
3. **Real-time Synchronization:** The platform relies on a **realtime-ready refresh and fallback behavior** for state updates across user sessions, rather than maintaining full end-to-end Supabase WebSocket connections.
4. **Testing Constraints:** The Playwright-based A/B Experiment "Simulate Traffic" tests are extremely resource-intensive. They may occasionally timeout (>30s) when run on heavily constrained local machines or CI workers.
5. **Payment Processing:** Financial transactions and wallet deductions are currently mocked and do not connect to a real payment gateway.

## Future Roadmap

If this project were to evolve toward production, the following architectural upgrades would be prioritized:

1. **Python Microservices:** Extract the deterministic intelligence scripts into dedicated Python/FastAPI microservices, allowing integration with robust ML libraries like `scikit-learn` or `PyTorch` for trained inference.
2. **Caching Layer:** Introduce Redis (e.g., via Upstash) to cache high-velocity, read-heavy queries such as the Customer Eats and Grocery menus to reduce database load.
3. **Containerization:** Dockerize the Next.js frontend and background chron workers for deployment via Kubernetes orchestration.
4. **Vercel Previews:** Integrate Vercel for automated CI/CD branch preview environments tied to GitHub PRs.
5. **Production Observability:** Replace local terminal logging with a dedicated observability stack (e.g., Datadog or Sentry) to monitor Server Action failures and edge latency.
6. **Stripe Integration:** Implement a full Stripe Connect integration for complex multi-party marketplace payouts.
