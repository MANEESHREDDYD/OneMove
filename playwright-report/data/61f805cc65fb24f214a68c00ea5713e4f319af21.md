# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: onemove-intelligence-platform-phase4.spec.ts >> Intelligence Platform Phase 4: AI Assistants and MLOps >> Admin Experiments page loads and simulates data
- Location: tests\e2e\onemove-intelligence-platform-phase4.spec.ts:24:7

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
        - generic [ref=e6]:
          - generic [ref=e7]:
            - img [ref=e8]
            - generic [ref=e10]:
              - heading "A/B Experiments Platform" [level=1] [ref=e11]
              - paragraph [ref=e12]: MVP directional experiment readout; not a production statistical inference engine.
          - button "Simulate Traffic" [ref=e14]:
            - img [ref=e15]
            - text: Simulate Traffic
        - generic [ref=e21]:
          - generic [ref=e22]:
            - generic [ref=e23]:
              - heading "Dynamic Delivery Fee Test" [level=2] [ref=e24]
              - paragraph [ref=e25]: Testing if dynamic delivery fees based on demand increases overall conversion vs flat fees.
            - generic [ref=e26]: ACTIVE
          - generic [ref=e28]:
            - generic [ref=e29]:
              - generic [ref=e30]:
                - heading "Treatment (Dynamic)" [level=3] [ref=e31]
                - generic [ref=e32]: 50% Alloc
              - generic [ref=e33]:
                - generic [ref=e34]:
                  - generic [ref=e35]: Impressions
                  - generic [ref=e36]: "42"
                - generic [ref=e37]:
                  - generic [ref=e38]: Conversions
                  - generic [ref=e39]: "13"
                - generic [ref=e40]:
                  - generic [ref=e41]: Conv. Rate
                  - generic [ref=e42]: 31.0%
                - generic [ref=e43]:
                  - generic [ref=e44]: Revenue
                  - generic [ref=e45]: $536.00
              - generic [ref=e47]: continue (winning)
            - generic [ref=e48]:
              - generic [ref=e49]:
                - heading "Control (Flat Fee)" [level=3] [ref=e50]
                - generic [ref=e51]: 50% Alloc
              - generic [ref=e52]:
                - generic [ref=e53]:
                  - generic [ref=e54]: Impressions
                  - generic [ref=e55]: "58"
                - generic [ref=e56]:
                  - generic [ref=e57]: Conversions
                  - generic [ref=e58]: "13"
                - generic [ref=e59]:
                  - generic [ref=e60]: Conv. Rate
                  - generic [ref=e61]: 22.4%
                - generic [ref=e62]:
                  - generic [ref=e63]: Revenue
                  - generic [ref=e64]: $479.00
              - generic [ref=e66]: needs more data
    - navigation [ref=e67]:
      - generic [ref=e68]:
        - link "Command Center" [ref=e69] [cursor=pointer]:
          - /url: /admin/command-center
          - img [ref=e70]
          - generic [ref=e75]: Command Center
        - link "Analytics" [ref=e76] [cursor=pointer]:
          - /url: /admin/analytics
          - img [ref=e77]
          - generic [ref=e80]: Analytics
        - link "ML Lab" [ref=e81] [cursor=pointer]:
          - /url: /admin/ml-lab
          - img [ref=e82]
          - generic [ref=e84]: ML Lab
        - link "Compliance" [ref=e85] [cursor=pointer]:
          - /url: /admin/compliance
          - img [ref=e86]
          - generic [ref=e88]: Compliance
        - link "Ops Assistant" [ref=e89] [cursor=pointer]:
          - /url: /admin/ops-assistant
          - img [ref=e90]
          - generic [ref=e98]: Ops Assistant
  - region "Notifications alt+T"
  - button "Open Next.js Dev Tools" [ref=e104] [cursor=pointer]:
    - img [ref=e105]
  - alert [ref=e108]
```