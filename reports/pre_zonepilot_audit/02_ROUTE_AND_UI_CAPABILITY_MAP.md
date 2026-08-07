# 02 ROUTE AND UI CAPABILITY MAP

## Route Inventory

### Customer Persona (`/customer`)
- `/customer/checkout`: Cart checkout flow. (VERIFIED_WORKING_WITH_EXTERNAL_DEPENDENCY)
- `/customer/courier`: Peer-to-peer delivery requests. (VERIFIED_PARTIAL)
- `/customer/eats`: Restaurant food ordering. (VERIFIED_WORKING)
- `/customer/grocery`: Grocery delivery. (VERIFIED_WORKING)
- `/customer/orders`: Order history and live map tracking. (SIMULATED_DEMO)
- `/customer/profile`: User account management. (VERIFIED_WORKING)
- `/customer/recommendations`: ML-driven suggestions. (SIMULATED_DEMO)
- `/customer/rides`: Ride-hailing booking form. (VERIFIED_WORKING)
- `/customer/safety`: Emergency and trust features. (UI_ONLY)
- `/customer/support`: Customer help desk. (VERIFIED_WORKING)

### Merchant Persona (`/merchant`)
- `/merchant/analytics`: Sales and performance dashboards. (SIMULATED_DEMO)
- `/merchant/insights`: Store intelligence and traffic data. (SIMULATED_DEMO)
- `/merchant/inventory`: Product and stock management. (VERIFIED_WORKING)
- `/merchant/menu`: Restaurant menu editor. (VERIFIED_WORKING)
- `/merchant/orders`: Active order pipeline and POS. (VERIFIED_WORKING)
- `/merchant/payouts`: Financial reconciliation. (SIMULATED_DEMO)
- `/merchant/profile`: Storefront configurations. (VERIFIED_WORKING)

### Partner / Driver Persona (`/partner`)
- `/partner/documents`: Compliance and vehicle registration. (UI_ONLY)
- `/partner/earnings`: Revenue breakdown. (SIMULATED_DEMO)
- `/partner/heatmap`: Live demand and surge pricing zones. (SIMULATED_DEMO)
- `/partner/insights`: Driver rating and feedback. (SIMULATED_DEMO)
- `/partner/jobs`: Live job dispatch terminal. (VERIFIED_WORKING)
- `/partner/profile`: Driver account settings. (VERIFIED_WORKING)

### Admin / Backoffice Persona (`/admin`)
- Contains 20+ specialized modules for global oversight.
- Features like `/admin/dispatch-optimizer` and `/admin/ml-lab` represent UI_ONLY or SIMULATED_DEMO interactions.

### System Routes
- `/auth`: Login and session management. (VERIFIED_WORKING)
- `/showcase`: Demonstration endpoints. (VERIFIED_WORKING)

## UI Capability Map Execution Summary
Most UI routes correctly execute database operations for simple CRUD (orders, catalogs, basic profiles). However, analytical, tracking, routing, and intelligence capabilities rely heavily on generated static or mock data.
