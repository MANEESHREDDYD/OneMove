# Demo Auth Users Report

**Run Date:** 2026-06-01
**Status:** ✅ VERIFIED

## Summary
To ensure valid login capabilities for every simulated user, we have created deterministic matching Supabase Auth users for all demo profiles across the platform.

## Generation Stats
* **Total Customer Auth Users:** 50
* **Total Partner Auth Users:** 50
* **Total Merchant Auth Users:** 50
* **Total Admin Auth Users:** 2
* **Total Primary Accounts:** 4
* **Total Users Generated:** 156

## Verification Status
* **Profiles Verified:** 156 (1-to-1 match with auth.users)
* **Partner Profiles Verified:** 50 (All partners mapped to driver role with vehicle rows)
* **Merchant Profiles Verified:** 50 (All merchants mapped to merchant role with merchant rows)

## Credential Storage
* **CSV Export Path:** `private/demo-login-credentials.csv` (gitignored)
* **Markdown Export Path:** `private/DEMO_LOGIN_CREDENTIALS.local.md` (gitignored)

## Primary Demo Accounts
| Role | Email | Password | Route |
|------|-------|----------|-------|
| Customer | customer@onemove.demo | Demo@12345 | /customer |
| Partner | partner@onemove.demo | Demo@12345 | /partner |
| Merchant | merchant@onemove.demo | Demo@12345 | /merchant |
| Admin | admin@onemove.demo | Demo@12345 | /admin/command-center |

## Sample Generated Accounts
| Role | Email | Password | Route |
|------|-------|----------|-------|
| Customer | customer001@onemove.demo | Customer@001Move | /customer |
| Partner | partner001@onemove.demo | Partner@001Move | /partner |
| Merchant | merchant001@onemove.demo | Merchant@001Move | /merchant |
| Admin | admin001@onemove.demo | Admin@001Move | /admin/command-center |

## Verification Command
`npm run verify:auth`

## Final Status
✅ All demo users have valid passwords, matching profiles, appropriate role relationships, and correct routing.
