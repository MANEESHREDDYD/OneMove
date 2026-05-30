# Master Bug Log

| Bug ID | Title | Severity | Layer | Route/File | Steps to reproduce | Expected | Actual | Root cause | Fix applied | Retest result | Final status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BUG-001 | Vitest Mock Errors | Medium | Backend | `__tests__/backend.test.ts` | Run `npm run test:backend` | Tests run against server actions. | Tests crash due to `next/headers` alias. | Vitest JS-DOM environment misses node aliases and server action mocks. | Switched to `node` env, mocked Next.js modules, explicitly replaced function calls to match actions. | Passed | Fixed |
| BUG-002 | Unauthenticated RLS Data Leak | High | RLS / Database | `supabase/policies.sql` | Run `test-rls-security.js` with Anon credentials | Returns 0 rows for `profiles` | Returns seeded profiles | `USING (true)` applied globally for MVP permissive setup. | Replaced `USING (true)` with `USING (auth.role() = 'authenticated')` for profiles, merchants, products via `apply-policies.js`. | Passed | Fixed |

*Note: Frontend UI and Database DQ checks revealed 0 bugs during the initial sweep due to prior QA iterations successfully stripping out "Coming Soon" placeholders and `href="#"` dead links.*
