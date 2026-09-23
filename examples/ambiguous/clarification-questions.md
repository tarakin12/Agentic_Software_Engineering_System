# Clarification Questions — "Build a better URL platform."

**Produced by:** Requirement Analyst
**Reason:** The requirement lacks enough information to design or
implement anything specific. Unlike the URL shortener requirement (where
ambiguity existed but was judged non-material — see
`examples/greenfield/url-shortener.md`), here the ambiguity is **material**:
almost every dimension needed to even choose an architecture is undefined.

## Why This Blocks Proceeding

"Better" relative to what baseline? "Platform" implies something broader
than a single service, but how much broader is unspecified. Proceeding to
architecture here would require inventing the actual business requirements
— which is explicitly disallowed ("never silently convert assumptions
into requirements").

## Questions Requiring Human Answers

1. **Business objective:** What does "better" mean — faster redirects,
   more features (custom domains, QR codes, link-in-bio pages), monetization,
   analytics depth, or something else entirely?
2. **Users:** Who uses this — internal teams, the general public, paying
   business customers? Single-tenant or multi-tenant?
3. **Expected scale:** Approximate requests/day and total stored URLs —
   thousands, millions, billions?
4. **Availability:** Is downtime tolerable (best-effort) or does this need
   defined uptime guarantees (e.g., 99.9%)?
5. **Authentication:** Should URL creation be open, API-key gated, or full
   user-account based? Should analytics be private per-account?
6. **Analytics:** Aggregate counts only, or detailed (referrer, device,
   geography, time-series dashboards)?
7. **Retention:** How long should URLs and analytics data be kept? Is
   there a compliance requirement (e.g., GDPR deletion requests)?
8. **Performance:** Any specific latency target for redirects (e.g., p99
   under 50ms)?
9. **Security/compliance:** Any regulatory constraints (GDPR, CCPA,
   industry-specific)? Any abuse-prevention requirement (malware/phishing
   URL blocking)?
10. **"Platform" scope:** Is this one service, or does it imply a broader
    product (dashboard UI, billing, multi-team support, public API for
    third parties)?

## Impact of Proceeding Without Clarification

If the workflow proceeded now, the Architecture Designer would have to
silently invent answers to all 10 questions above — effectively deciding
the actual product on the requester's behalf without their knowledge. Per
the global rule ("material ambiguity requires human clarification or
approval"), that is not acceptable here, unlike the URL shortener case
where the ambiguities were narrow implementation details with low-risk,
clearly-labeled defaults.

