# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-ride-flow.spec.ts >> OneMove Ride Flow >> E2E Ride Booking across roles
- Location: tests\e2e\onemove-ride-flow.spec.ts:21:7

# Error details

```
Error: Expected 0 console/network errors, but got 28:
Request failed: http://localhost:3000/auth/register?_rsc=zq8L_ECosMvEVZUv - net::ERR_ABORTED
Request failed: http://localhost:3000/auth/login - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/courier?_rsc=l3fTzP44Ysfd4SEU - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/eats?_rsc=l3fTzP44Ysfd4SEU - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/orders?_rsc=l3fTzP44Ysfd4SEU - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/orders/2c2a8968-d342-4c18-ae00-7ba91e3b94a5?_rsc=l3fTzP44Ysfd4SEU - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/courier?_rsc=Iq2_1BRHCAOQpI60 - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/grocery?_rsc=Iq2_1BRHCAOQpI60 - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/eats?_rsc=Iq2_1BRHCAOQpI60 - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides?_rsc=9kT79piB27zheD4h - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides?_rsc=4K3RPiGcJUcpE3Fm - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides?_rsc=LHi-B_LRJWO7NYaO - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/orders?_rsc=Iq2_1BRHCAOQpI60 - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/orders/2c2a8968-d342-4c18-ae00-7ba91e3b94a5?_rsc=Iq2_1BRHCAOQpI60 - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/grocery?_rsc=9LaSdG7cUq_T84rj - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/grocery?_rsc=bx8BTqFmd9r5qApR - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides?_rsc=cwbgjA8WNQFY0jtU - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/eats?_rsc=bx8BTqFmd9r5qApR - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides?_rsc=Tr6a2FfptmmbpnPa - net::ERR_ABORTED
Request failed: http://localhost:3000/customer?_rsc=bx8BTqFmd9r5qApR - net::ERR_ABORTED
Error: NEXT_REDIRECT
    at a (http://localhost:3000/_next/static/chunks/067stm0dkt722.js:1:22524)
    at F (http://localhost:3000/_next/static/chunks/0o~p~nz63sut..js:2:3129)
    at http://localhost:3000/_next/static/chunks/0o~p~nz63sut..js:2:2212
Request failed: http://localhost:3000/customer/rides - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/grocery?_rsc=l52b1t7woI2TK1vR - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/eats?_rsc=l52b1t7woI2TK1vR - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides?_rsc=ORKQNr0i9CVxNrT- - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides?_rsc=6PRwrNgxbdr1Ya6u - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides?_rsc=olsGt3M11toFcvqj - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides/f1701f88-565b-436a-b77c-5f9fc53f4ac8?_rsc=t0m67Qkk_-lfP9js - net::ERR_ABORTED

expect(received).toBe(expected) // Object.is equality

Expected: 0
Received: 28
```