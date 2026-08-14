# 13 DEAD CODE AND TECH DEBT AUDIT

## Overview
Analysis of unintegrated polyglot modules and overall codebase bloat.

## 1. Java Risk Service (`java/onemove-risk-service/`)
- **Status**: **DEAD_OR_ORPHANED**
- **Details**: This module is completely unintegrated. Although the Java application exposes REST endpoints for risk scoring, a full codebase search confirms no HTTP requests are made to it (neither on port 8080 nor matching the endpoint routes). 
- **Actual Implementation**: The Next.js frontend handles risk evaluation internally via TypeScript modules (e.g., `lib/ml/fraudRisk.ts`), rendering the Java backend superfluous.

## 2. Fake CI Workflows
- **Status**: **TECH_DEBT**
- **Details**: `.github/workflows/sql-quality.yml` is an explicitly faked pipeline that bypasses real SQL migration linting.

## 3. UI/UX Tech Debt
- The codebase leverages a high degree of hardcoded structural duplication across the 4 major app personas (Customer, Partner, Merchant, Admin) that should ideally share underlying robust server components rather than independent clones.
