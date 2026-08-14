# 01 REPOSITORY ARCHITECTURE

## Overview
The OneMove repository is a monolithic full-stack application built with **Next.js (App Router)** and backed by **Supabase** for database, auth, and real-time operations. 

## Core Structure (As-Built)
- **/app**: Next.js App Router frontend, strictly isolated by user personas (`admin`, `customer`, `merchant`, `partner`).
- **/components**: Shared UI library components, mapping integrations (Leaflet), and glass-morphism aesthetic cards.
- **/scripts**: Comprehensive database administration toolkit focusing on schema setup, RLS policy application, and extensive synthetic demo data generation.
- **/supabase**: Holds the underlying database definitions and migrations.
- **/utils**: Contains shared utility logic (e.g., pricing engines, determinism helpers).

## Findings
**SIMULATED_DEMO / UI_ONLY**
The repository reflects a "demo-first" architectural pattern. It prioritizes the ability to easily seed, reset, and project a fully functional multi-persona marketplace without relying on live organic data streams. The architecture is primarily focused on frontend demonstration rather than deep backend processing logic natively integrated via APIs.
