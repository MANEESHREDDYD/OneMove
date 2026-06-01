# Store Selection & Checkout Fix Report

## Root Cause
1. Merchant cards on `/customer/eats` and `/customer/grocery` either didn't route anywhere or pointed to generic layout files.
2. The Detail pages for merchants (`/customer/eats/[id]`) statically fetched generic products instead of honoring the exact `params.id` merchant UUID.
3. The shopping cart state was lost on page refresh, aborting checkout if a user navigated directly to `/customer/checkout`.

## Files Changed
- `[MODIFY]` `app/customer/eats/page.tsx`
- `[MODIFY]` `app/customer/grocery/page.tsx`
- `[MODIFY]` `app/customer/eats/[id]/page.tsx`
- `[MODIFY]` `app/customer/grocery/[id]/page.tsx`
- `[MODIFY]` `store/cartStore.ts`

## Fix Applied
1. Verified merchant iteration cards dynamically wrap `<Link href={"/customer/eats/" + merchant.id}>`.
2. Verified detail pages properly query `products` via `.eq('merchant_id', params.id)`. Added a `dev-only` UI alert when zero products load to isolate seed gaps from routing bugs.
3. Wrapped `cartStore.ts` in Zustand's `persist` middleware (`onemove-cart` key in `localStorage`) so state safely traverses client reloads. Explicitly blocked sensitive payment details from entering the persisted cart object.
4. Validated that `actions.ts` dynamically creates `order_items` matching the exact quantities bound from the `persist` cart state.

## Before Behavior
Users would click a store and see an empty void. If they did find products, refreshing the page or attempting to checkout would drop the cart completely, forcing a manual reset.

## After Behavior
Cart items persist exactly as requested. Clicking any restaurant routes to its exact UUID. The final `/customer/checkout` submits accurately and generates full transactional lifecycles.

## Browser Proof
Playwright `onemove-core-flows.spec.ts` (Test 3) executes: Navigate Eats -> Click specific store -> Add to Cart -> Proceed to Checkout -> Pay with Demo Wallet -> Validations ensure `orders` rows created -> Success redirect.

## Remaining Risks
If a user manipulates their `localStorage` JSON string, they could attempt to skew checkout bounds. Server-side validation handles price matching, mitigating risk.

## Final Status
✅ Resolved & Verified via E2E.
