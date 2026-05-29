# QA and Testing Strategy

## Checkpoint Test Strategy
For every checkpoint, we follow a rigorous QA loop before pushing to GitHub:
1. Build the checkpoint feature.
2. Run automated validation (`lint`, `typecheck`, `test`, `build`).
3. Act like a senior QA architect and perform 100+ manual tests.
4. Log bugs, fix them, and retest until no Critical/High/Medium bugs remain.
5. Push to GitHub only when all checks pass.

## 100+ Test Scenario Categories
1. **Happy Paths**: Basic successful workflows.
2. **Edge Cases**: Missing fields, weird inputs, time zone issues.
3. **Invalid Inputs**: SQL injection tests, XSS attempts, massive strings.
4. **Mobile Responsiveness**: UI scaling on small devices, bottom nav interaction.
5. **Desktop Responsiveness**: Sidebar behavior, large table scaling.
6. **Role-based Access**: Users accessing wrong portals, RLS verifications.
7. **Broken/Empty Data States**: Missing profile pics, zero active jobs.
8. **Loading States**: Skeletons, button disabled states during submit.
9. **Error States**: Network failure, 404 pages, Supabase errors.
10. **Database Failures**: Connection timeouts, transaction rollbacks.
11. **Supabase Auth Issues**: Expired sessions, incorrect passwords.
12. **Pricing Mistakes**: Negative numbers, rounding errors.
13. **Status Transition Mistakes**: Skipping states, invalid transitions.
14. **Security/RLS Risks**: RLS bypass attempts.
15. **Accessibility**: Tab navigation, ARIA labels, contrast.
16. **PWA Behavior**: Offline access, install prompt.
17. **Navigation Issues**: Broken links, incorrect redirects.
18. **Cross-Role Workflow**: Order created by Customer, seen by Merchant, accepted by Partner.

## Bug Log Format
- **Bug ID**: #XX
- **Severity**: Critical / High / Medium / Low
- **Area Affected**: Frontend/Backend/DB/Auth
- **Reproduction Steps**: 1. 2. 3.
- **Root Cause**: Explanation
- **Fix Applied**: Description of fix
- **Retest Result**: Pass/Fail

## Regression Testing Process
After fixing a bug, re-run all automated tests and at least 3 related happy paths to ensure the fix did not break existing functionality.

## Final QA Checklist
- [ ] No secrets in code
- [ ] No console.error in critical paths
- [ ] Mobile/Desktop visually sound
- [ ] Tests pass
- [ ] Build succeeds

## Known Limitations
- Real payments are disabled; using mock cards.
- AI is rule-based simulated.
