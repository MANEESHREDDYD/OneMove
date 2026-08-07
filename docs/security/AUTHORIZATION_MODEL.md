# Authorization Model
- **Human Sessions**: Always use RLS (`get_user_db(jwt)`).
- **Machine Jobs**: Use secret client (`get_service_db()`) strictly for cron jobs, collectors, and exports.
- **Roles**: CUSTOMER, MERCHANT, RIDER, SYSTEM, UNKNOWN. Managed safely.
