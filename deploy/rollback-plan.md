# Rollback Plan

1. Revert Git commit to last known good SHA.
2. Vercel: Click "Promote to Production" on previous deployment.
3. Supabase: Restore Database snapshot if migration caused corruption.
