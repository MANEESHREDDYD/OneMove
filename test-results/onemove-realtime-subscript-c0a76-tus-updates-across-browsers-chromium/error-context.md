# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-realtime-subscriptions.spec.ts >> OneMove Realtime Subscriptions >> Order status updates across browsers
- Location: tests\e2e\onemove-realtime-subscriptions.spec.ts:7:7

# Error details

```
Test timeout of 30000ms exceeded.
```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e2]:
    - complementary [ref=e3]:
      - link "OneMove" [ref=e5] [cursor=pointer]:
        - /url: /
      - navigation [ref=e6]:
        - link "Dashboard" [ref=e7] [cursor=pointer]:
          - /url: /customer
          - img [ref=e8]
          - generic [ref=e13]: Dashboard
        - link "Rides" [ref=e14] [cursor=pointer]:
          - /url: /customer/rides
          - img [ref=e15]
          - generic [ref=e19]: Rides
        - link "Eats" [ref=e20] [cursor=pointer]:
          - /url: /customer/eats
          - img [ref=e21]
          - generic [ref=e24]: Eats
        - link "Grocery" [ref=e25] [cursor=pointer]:
          - /url: /customer/grocery
          - img [ref=e26]
          - generic [ref=e29]: Grocery
        - link "Courier" [ref=e30] [cursor=pointer]:
          - /url: /customer/courier
          - img [ref=e31]
          - generic [ref=e35]: Courier
        - link "Profile" [ref=e36] [cursor=pointer]:
          - /url: /customer/profile
          - img [ref=e37]
          - generic [ref=e40]: Profile
    - main [ref=e41]:
      - generic [ref=e43]:
        - generic [ref=e44]:
          - generic [ref=e46]:
            - heading "Good Morning" [level=1] [ref=e47]
            - paragraph [ref=e48]: Where to next?
          - button "Sign Out" [ref=e49]:
            - img
            - text: Sign Out
        - generic [ref=e50]:
          - generic [ref=e51]:
            - heading "Active Orders" [level=2] [ref=e52]
            - link "View all" [ref=e53] [cursor=pointer]:
              - /url: /customer/orders
          - generic [ref=e54]:
            - link "ride • accepted Times Square" [ref=e55] [cursor=pointer]:
              - /url: /customer/orders/b0a41999-cfd7-4d06-a4e2-e0ba87982265
              - generic [ref=e56]:
                - img [ref=e58]
                - generic [ref=e62]:
                  - heading "ride • accepted" [level=3] [ref=e63]
                  - generic [ref=e64]:
                    - img [ref=e65]
                    - generic [ref=e68]: Times Square
            - link "ride • pending 8812 Maymie Lodge, New York, NY" [ref=e69] [cursor=pointer]:
              - /url: /customer/orders/2c2a8968-d342-4c18-ae00-7ba91e3b94a5
              - generic [ref=e70]:
                - img [ref=e72]
                - generic [ref=e76]:
                  - heading "ride • pending" [level=3] [ref=e77]
                  - generic [ref=e78]:
                    - img [ref=e79]
                    - generic [ref=e82]: 8812 Maymie Lodge, New York, NY
        - generic [ref=e83]:
          - heading "Services" [level=2] [ref=e84]
          - generic [ref=e85]:
            - link "Rides Get there fast" [ref=e86] [cursor=pointer]:
              - /url: /customer/rides
              - generic [ref=e87]:
                - img [ref=e90]
                - generic [ref=e94]:
                  - heading "Rides" [level=3] [ref=e95]
                  - paragraph [ref=e96]: Get there fast
            - link "Food Cravings delivered" [ref=e97] [cursor=pointer]:
              - /url: /customer/eats
              - generic [ref=e98]:
                - img [ref=e101]
                - generic [ref=e104]:
                  - heading "Food" [level=3] [ref=e105]
                  - paragraph [ref=e106]: Cravings delivered
            - link "Grocery Fresh & fast" [ref=e107] [cursor=pointer]:
              - /url: /customer/grocery
              - generic [ref=e108]:
                - img [ref=e111]
                - generic [ref=e117]:
                  - heading "Grocery" [level=3] [ref=e118]
                  - paragraph [ref=e119]: Fresh & fast
            - link "Courier Send packages" [ref=e120] [cursor=pointer]:
              - /url: /customer/orders
              - generic [ref=e121]:
                - img [ref=e124]
                - generic [ref=e128]:
                  - heading "Courier" [level=3] [ref=e129]
                  - paragraph [ref=e130]: Send packages
        - generic [ref=e133]:
          - heading "Try OneMove Prime" [level=3] [ref=e134]
          - paragraph [ref=e135]: Get $0 delivery fees on eligible food and grocery orders, plus 5% off rides.
          - button "Start Free Trial" [ref=e136]
        - button [ref=e138]:
          - img [ref=e139]
  - region "Notifications alt+T"
  - button "Open Next.js Dev Tools" [ref=e146] [cursor=pointer]:
    - generic [ref=e149]:
      - text: Compiling
      - generic [ref=e150]:
        - generic [ref=e151]: .
        - generic [ref=e152]: .
        - generic [ref=e153]: .
  - alert [ref=e154]
```