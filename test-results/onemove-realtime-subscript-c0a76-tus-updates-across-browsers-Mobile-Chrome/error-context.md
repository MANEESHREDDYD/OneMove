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
    - main [ref=e3]:
      - generic [ref=e5]:
        - generic [ref=e7]:
          - heading "Pizza Napoli" [level=1] [ref=e8]
          - paragraph [ref=e9]: Select items to add to your order
        - generic [ref=e10]:
          - generic [ref=e11]:
            - generic [ref=e12]:
              - heading "Spicy Tuna Roll" [level=3] [ref=e13]
              - paragraph [ref=e14]: Japanese specialty
              - paragraph [ref=e15]: $6.89
            - button [ref=e17]:
              - img [ref=e18]
          - generic [ref=e19]:
            - generic [ref=e20]:
              - heading "Dragon Roll" [level=3] [ref=e21]
              - paragraph [ref=e22]: Japanese specialty
              - paragraph [ref=e23]: $24.48
            - button [ref=e25]:
              - img [ref=e26]
          - generic [ref=e27]:
            - generic [ref=e28]:
              - heading "Miso Soup" [level=3] [ref=e29]
              - paragraph [ref=e30]: Japanese specialty
              - paragraph [ref=e31]: $12.02
            - button [ref=e33]:
              - img [ref=e34]
          - generic [ref=e35]:
            - generic [ref=e36]:
              - heading "Edamame" [level=3] [ref=e37]
              - paragraph [ref=e38]: Japanese specialty
              - paragraph [ref=e39]: $18.64
            - button [ref=e41]:
              - img [ref=e42]
          - generic [ref=e43]:
            - generic [ref=e44]:
              - heading "Teriyaki Chicken" [level=3] [ref=e45]
              - paragraph [ref=e46]: Japanese specialty
              - paragraph [ref=e47]: $26.52
            - button [ref=e49]:
              - img [ref=e50]
          - generic [ref=e51]:
            - generic [ref=e52]:
              - heading "Ramen Tonkotsu" [level=3] [ref=e53]
              - paragraph [ref=e54]: Japanese specialty
              - paragraph [ref=e55]: $24.42
            - button [ref=e57]:
              - img [ref=e58]
          - generic [ref=e59]:
            - generic [ref=e60]:
              - heading "Tempura Shrimp" [level=3] [ref=e61]
              - paragraph [ref=e62]: Japanese specialty
              - paragraph [ref=e63]: $13.79
            - button [ref=e65]:
              - img [ref=e66]
          - generic [ref=e67]:
            - generic [ref=e68]:
              - heading "Salmon Sashimi" [level=3] [ref=e69]
              - paragraph [ref=e70]: Japanese specialty
              - paragraph [ref=e71]: $16.89
            - button [ref=e73]:
              - img [ref=e74]
          - generic [ref=e75]:
            - generic [ref=e76]:
              - heading "Gyoza (6pc)" [level=3] [ref=e77]
              - paragraph [ref=e78]: Japanese specialty
              - paragraph [ref=e79]: $7.46
            - button [ref=e81]:
              - img [ref=e82]
          - generic [ref=e83]:
            - generic [ref=e84]:
              - heading "Matcha Ice Cream" [level=3] [ref=e85]
              - paragraph [ref=e86]: Japanese specialty
              - paragraph [ref=e87]: $23.45
            - button [ref=e89]:
              - img [ref=e90]
    - navigation [ref=e91]:
      - generic [ref=e92]:
        - link "Dashboard" [ref=e93] [cursor=pointer]:
          - /url: /customer
          - img [ref=e94]
          - generic [ref=e99]: Dashboard
        - link "Rides" [ref=e100] [cursor=pointer]:
          - /url: /customer/rides
          - img [ref=e101]
          - generic [ref=e105]: Rides
        - link "Eats" [ref=e106] [cursor=pointer]:
          - /url: /customer/eats
          - img [ref=e107]
          - generic [ref=e110]: Eats
        - link "Grocery" [ref=e111] [cursor=pointer]:
          - /url: /customer/grocery
          - img [ref=e112]
          - generic [ref=e115]: Grocery
        - link "Courier" [ref=e116] [cursor=pointer]:
          - /url: /customer/courier
          - img [ref=e117]
          - generic [ref=e121]: Courier
  - region "Notifications alt+T"
  - button "Open Next.js Dev Tools" [ref=e127] [cursor=pointer]:
    - img [ref=e128]
  - alert [ref=e131]
```