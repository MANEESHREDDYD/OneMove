# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-ride-flow.spec.ts >> OneMove Ride Flow >> E2E Ride Booking across roles
- Location: tests\e2e\onemove-ride-flow.spec.ts:21:7

# Error details

```
Error: Expected 0 console/network errors, but got 41:
Request failed: http://localhost:3000/auth/register?_rsc=n5hqsW7r31npIJSZ - net::ERR_ABORTED
Request failed: http://localhost:3000/auth/register?_rsc=zq8L_ECosMvEVZUv - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/eats?_rsc=l3fTzP44Ysfd4SEU - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/orders?_rsc=l3fTzP44Ysfd4SEU - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides?_rsc=l3fTzP44Ysfd4SEU - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/grocery?_rsc=l3fTzP44Ysfd4SEU - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/orders/2c2a8968-d342-4c18-ae00-7ba91e3b94a5?_rsc=l3fTzP44Ysfd4SEU - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/courier?_rsc=l3fTzP44Ysfd4SEU - net::ERR_ABORTED
Request failed: http://localhost:3000/?_rsc=l3fTzP44Ysfd4SEU - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/profile?_rsc=l3fTzP44Ysfd4SEU - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/orders?_rsc=Iq2_1BRHCAOQpI60 - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/grocery?_rsc=Iq2_1BRHCAOQpI60 - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/eats?_rsc=Iq2_1BRHCAOQpI60 - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides?_rsc=4K3RPiGcJUcpE3Fm - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides?_rsc=9kT79piB27zheD4h - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides?_rsc=6W-awLhu6xeD--nd - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/orders/2c2a8968-d342-4c18-ae00-7ba91e3b94a5?_rsc=Iq2_1BRHCAOQpI60 - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/profile?_rsc=pD8v03SfZ8VSeAi9 - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/profile?_rsc=Gb_0x4cjDoJAP8nu - net::ERR_ABORTED
Request failed: http://localhost:3000/?_rsc=gb9AOIIhGorIsmcG - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/courier?_rsc=Iq2_1BRHCAOQpI60 - net::ERR_ABORTED
Request failed: http://localhost:3000/?_rsc=9kT79piB27zheD4h - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/profile?_rsc=9LaSdG7cUq_T84rj - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/courier?_rsc=9LaSdG7cUq_T84rj - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/eats?_rsc=9LaSdG7cUq_T84rj - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/grocery?_rsc=9LaSdG7cUq_T84rj - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/profile?_rsc=cwbgjA8WNQFY0jtU - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/eats?_rsc=bx8BTqFmd9r5qApR - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides?_rsc=F5TG00HeqPh_LC1w - net::ERR_ABORTED
Request failed: http://localhost:3000/customer?_rsc=bx8BTqFmd9r5qApR - net::ERR_ABORTED
Error: NEXT_REDIRECT
    at a (http://localhost:3000/_next/static/chunks/067stm0dkt722.js:1:22524)
    at F (http://localhost:3000/_next/static/chunks/0o~p~nz63sut..js:2:3129)
    at http://localhost:3000/_next/static/chunks/0o~p~nz63sut..js:2:2212
Request failed: http://localhost:3000/customer/profile?_rsc=SuC5v0JKS5BJy-Ju - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/profile?_rsc=yeLqVR9kY9XV1-_K - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/eats?_rsc=LGNmddOT4z6DN0I- - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/grocery?_rsc=LGNmddOT4z6DN0I- - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/courier?_rsc=LGNmddOT4z6DN0I- - net::ERR_ABORTED
Request failed: http://localhost:3000/customer?_rsc=LGNmddOT4z6DN0I- - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides/e421b3ce-24b4-499d-a2a8-49315a8cae03?_rsc=ByuFlPelwaI9WJx7 - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides?_rsc=TeQ9I9k9jdj4jH25 - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides?_rsc=xbCI-MEAHTWZJbqf - net::ERR_ABORTED
Request failed: http://localhost:3000/customer/rides?_rsc=HrvKn5Mvgpx90m2L - net::ERR_ABORTED

expect(received).toBe(expected) // Object.is equality

Expected: 0
Received: 41
```