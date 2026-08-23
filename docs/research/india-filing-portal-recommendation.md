# India Filing Portal Recommendation for TrashTag

**Research Date:** August 23, 2026  
**Status:** In Progress

---

## TL;DR Recommendation

**Split by issue type, both form-only:**

1. **Garbage/waste dumps → Swachhata App** (MoHUA/Swachh Bharat Mission Urban)
   - National coverage (4000+ ULBs), purpose-built for cleanliness/waste issues
   - **No public API** - initial adapter is Tier 2 (complaint packet generator + guided form-fill)
   - Spike: Contact MoHUA/SBM for partner API access

2. **Potholes/roads → CPGRAMS** (DARPG grievance portal)
   - National coverage (all ministries/states), auto-routing, tracking ID
   - **No public API** - Tier 2 adapter (form-fill)
   - Does not explicitly list "potholes" as a category, but broad "service delivery grievance" scope suggests it can route municipal issues
   - Spike: Confirm CPGRAMS accepts municipal road complaints and routes them correctly (test with sample filing)

3. **City overrides:** Where city apps show strong integration (ICMC for Bengaluru, tested-and-working municipal portals), use as location-specific adapters; fall back to Swachhata/CPGRAMS outside those zones.

**Why split?** Swachhata is garbage-specialized with explicit national ULB reach; CPGRAMS is general-purpose with broader coverage but less clarity on municipal road issues. Splitting gives TrashTag the best national coverage for each issue class, vs forcing both through one suboptimal portal.

**Fallback chain:** Swachhata/CPGRAMS (issue-specific) → city app (if location matches) → "Outside coverage" (if no confident routing).

---

## Decisions (post-research)

These refine the research recommendation based on product direction:

1. **CPGRAMS as the single default adapter for BOTH classes** (potholes *and* garbage), for simplicity — one adapter, one integration, one tracking/SLA/appeal system (matches the original architecture §2.4 plan). CPGRAMS is a general-purpose national grievance portal covering all municipal service delivery, so both roads and sanitation fall under it via auto-routing.
   - **Swachhata (garbage)** and **city apps (ICMC, etc.)** are retained as **fallbacks/overrides**, added *only where the routing spike shows CPGRAMS handles that class poorly*. Still pluggable per `FilingAdapter`.
   - **Decisive spike (unchanged, now for both classes):** file a test pothole *and* a test garbage complaint via CPGRAMS and confirm each routes to the correct municipal body (PWD / sanitation), not stuck at ministry level.

2. **Complainant identity is protected — file via an umbrella identity (default), or anonymously where supported.**
   - **Umbrella account:** TrashTag registers ONE organizational account and files all complaints under it; the authority sees "TrashTag" as the complainant, never the individual citizen. This also consolidates status-tracking under one account.
   - **Citizen PII never leaves TrashTag:** report `user_id` is optional and internal-only (anti-abuse), and is *never* included in a filed complaint. Fully anonymous reports (no `user_id`) are supported end to end.
   - **Anonymous filing** only where a portal supports it without losing tracking — a per-portal spike.
   - **Accountability note:** filing under an umbrella identity makes TrashTag the named complainant (a legal/representational responsibility for the org).
   - **Spike:** confirm CPGRAMS/Swachhata terms permit an organization filing on behalf of citizens under one account, and whether anonymous filing is offered.

3. **Filing automation — status tracking, OTP, and the CAPTCHA ceiling.**
   - **Programmatic status tracking (umbrella benefit):** with one org account, poll all filed complaints + their status transitions under a single login and feed them back into the issue lifecycle (§2.3 `filed → in_progress → resolved`). No per-citizen accounts to reconcile.
   - **OTP broker:** the umbrella account's registered email/mobile receives OTPs at login/submission; automated/assisted filing needs a way to obtain them:
     - **Email OTP (preferred):** a controlled inbox polled over IMAP/provider API; parse the code and hand it to the filing session. Simplest and reliable.
     - **SMS OTP:** a controlled number via an SMS gateway / phone SMS-forwarder / receive-SMS API — heavier, and subject to India's DLT/telecom rules.
     - Prefer **session-level OTP** (authenticate once, file many in that session) to minimize OTP events.
   - **CAPTCHA ceiling (honest constraint):** portals typically pair OTP with CAPTCHA. `OTP + CAPTCHA + no API` ⇒ *fully* automated filing is fragile and likely against ToS. The OTP broker helps but is not sufficient alone.
   - **Durable unlock = API/partnership:** a negotiated CPGRAMS/Swachhata integration replaces OTP+CAPTCHA with API-key auth — this is what the "confirm API access" spike is really pursuing.
   - **Interim = assisted filing (keeps human-presses-send):** TrashTag drafts + prefills the complaint under the umbrella account, the OTP broker supplies the code, and a human approves the batch and clears any CAPTCHA / final submit.
   - **Security:** the OTP inbox/number is a sensitive credential surface — isolate it, restrict access, never log OTP codes. (Add to SECURITY.md when the filing layer is built.)
   - **Spike:** determine, per portal, whether OTP is per-login (session) or per-submission, and whether CAPTCHA is present — this decides how far filing can be automated before a partnership/API.

---

## Candidate Comparison

| Portal | Operator | Potholes | Garbage | Coverage | API? | Tracking+SLA | Routing | Fit for TrashTag |
|--------|----------|----------|---------|----------|------|--------------|---------|------------------|
| **Swachhata App** | MoHUA (SBM) | **No** | **Yes** | **4000+ ULBs (national)** | **No (form-only)** | Dashboard, unclear | ULB-level | **Best for garbage** |
| **CPGRAMS** | DARPG/NIC | Unclear | Unclear | National (all ministries/states) | **No (form-only)** | Reg ID, "reasonable time" | Auto-routes GRO | **Fallback for potholes** |
| NHAI portals | NHAI/MoRTH | Highways only | No | National highways only | Unknown | Unknown | Unknown | Too narrow |
| ICMC (Bengaluru) | Janaagraha NGO | Yes | Yes | Bengaluru + 2 cities | No (form-only) | Yes, 93.5% claim | Ward-based | City override |
| City apps (MCD 311, MCGM, etc.) | Municipal | Varies | Varies | Single city each | Mostly no | Varies | Ward/zone | Fragmented, fragile |

---

## Deep Notes

### 1. CPGRAMS (Centralised Public Grievance Redress and Monitoring System)

**Operator:** Department of Administrative Reforms & Public Grievances (DARPG), hosted by National Informatics Centre (NIC) under MeitY  
**URL:** https://pgportal.gov.in

**Coverage:** National - all Central Ministries/Departments and State governments across India. Single portal connected to all government entities.

**Issue categories:** Broadly covers "any subject related to service delivery" to public authorities. **Does not explicitly list potholes, roads, or garbage** in public documentation, but routing mechanism suggests it can handle municipal issues if routed to appropriate Ministry/Department.

**Tracking:** Yes - unique registration ID provided at submission, used for status tracking and appeals.

**SLA:** No specific timeline stated on main portal. Mentions "reasonable period" and appeal mechanism if resolution is rated "Poor". (Architecture doc §2.4 mentions 30-day resolution target and 5-level appeal path - needs verification.)

**Routing:** Auto-routes to relevant Ministry/Department/State based on grievance subject and location. Role-based access for Grievance Redressal Officers.

**API:** **No public API documented.** Access via web portal, standalone mobile apps (Google Play/Apple App Store), and UMANG integration only. No developer documentation found.

**Assessment:** Broad national reach, established routing/tracking, but **unclear if it's the right channel for municipal road/garbage issues** (may route poorly vs specialized municipal apps). No API = form-only submission for MVP.

**Sources:** https://pgportal.gov.in (main page)

---

### 2. Swachhata App / Swachhata-MoUD (Swachh Bharat Mission)

**Operator:** Ministry of Housing and Urban Affairs (MoHUA) under Swachh Bharat Mission Urban  
**URL:** https://sbmurban.org (main site), swachhata.gov.in (app portal - not resolving as of Aug 2026)

**Coverage:** National - launched August 2016, spans "all Indian states and union territories" with multi-city/ULB framework. Architecture doc mentions "4000+ ULBs" served.

**Issue categories:** **Strong garbage/cleanliness focus** - garbage dumps, waste collection, sanitation, public toilets. **No mention of potholes or road maintenance** - this is a Swachh Bharat (cleanliness) tool, not a roads tool.

**Tracking:** Citizen Feedback Dashboard mentioned (cf.sbmurban.org), but no detail on individual complaint tracking IDs or states.

**SLA:** Not documented in public-facing content.

**Routing:** Not detailed, but national multi-city structure suggests ULB-level routing.

**API:** **No API documentation found.** Portal describes Swachhata App and dashboards but no technical integration, endpoints, or developer access mentioned.

**Assessment:** **Strongest national option for garbage/waste issues specifically**, but does not cover potholes. Would need to be paired with a road-focused channel (CPGRAMS, NHAI, or city PWD apps) for full TrashTag coverage. Form-only submission without API partnership.

**Sources:** https://sbmurban.org

---

### 3. NHAI Road Portals (Rajmarg Yatra / Sukhad Yatra)

**Operator:** National Highways Authority of India (NHAI), Ministry of Road Transport & Highways  
**URL:** https://nhai.gov.in, http://morth.gov.in

**Coverage:** National highways only (not city roads, state highways, or municipal roads).

**Issue categories:** Potholes, road maintenance, highway issues - but **limited to NHAI-managed national highways**, which is a tiny fraction of India's road network and won't cover urban potholes reported by TrashTag.

**API / Tracking / Routing:** Could not extract details - government portal pages returned minimal content (likely JavaScript-heavy SPAs). Complaint portals like "Rajmarg Yatra" or "Sukhad Yatra" mentioned in architecture doc but not documented on public-facing pages accessed.

**Assessment:** **Too narrow in scope** - national highways are not where TrashTag's urban pothole/garbage detection will occur. Not a viable default. Could be a specialized fallback for highway-adjacent reports, but requires deeper investigation.

**Sources:** https://nhai.gov.in, http://morth.gov.in (pages returned minimal content)

---

### 4. City-Specific Apps

**BBMP Sahaaya / I Change My City (Bengaluru):** Already researched in `docs/research/ichangemycity-filing-adapter.md`. Strong fit for Bengaluru (potholes + garbage), form-only (no public API), Tier 2 adapter candidate as city-specific override.

**Other cities (Delhi MCD 311, Mumbai MCGM, Chennai, Hyderabad, Pune):** Not yet investigated in this research pass. Known to exist but highly fragmented, often form-only, and subject to operational fragility (example: Pune's PMC Road Mitra went dark for months in 2026 per architecture doc).

---

## Recommended Default + Fallback Strategy

### Default Pairing (Issue-Type Split)

**Garbage/waste dumps:**
- **Primary:** `SwachhataAdapter` (Swachhata App via sbmurban.org portal)
- **Rationale:** Swachh Bharat Mission Urban is *the* national cleanliness program, explicitly covering garbage/waste across 4000+ ULBs. Purpose-built for this issue class.
- **Implementation:** Form-based complaint packet generator until API partnership secured with MoHUA.

**Potholes/roads:**
- **Primary:** `CPGRAMSAdapter` (pgportal.gov.in)
- **Rationale:** Broader national grievance system covering all ministries/states. While it doesn't explicitly list "potholes" as a category, its auto-routing to appropriate government departments and universal coverage make it the default for issues Swachhata doesn't handle.
- **Caveat:** Needs validation that CPGRAMS accepts and routes municipal road complaints correctly (see Spikes below).
- **Implementation:** Form-based until API confirmed (architecture doc mentions "some states have API integration" - spike required).

### Fallback / Override Strategy

**Tier 1: Issue-type routing**
```
if issue.class_type == "garbage":
    primary = SwachhataAdapter
    fallback = CPGRAMSAdapter  # if Swachhata coverage doesn't include detected location
elif issue.class_type == "pothole":
    primary = CPGRAMSAdapter
    fallback = CityRoadAdapter(location)  # city PWD/municipal road apps
```

**Tier 2: Geographic overrides**
Where city-specific apps demonstrate strong municipal integration, route there INSTEAD of the national default:
- **Bengaluru** → `ICMCAdapter` (I Change My City / BBMP Sahaaya) — covers both potholes and garbage
- **[Other cities]** → add as tested; only override national defaults where city app is proven reliable

**Tier 3: "Outside coverage"**
If reverse-geocoded location cannot be confidently matched to an adapter's coverage area, mark issue as "Outside coverage" rather than guessing a recipient. This gate remains even with national portals, since Swachhata's 4000+ ULB list and CPGRAMS's ministry routing may not cover every rural/tier-3 location.

### Why Not CPGRAMS-Only (Original Architecture Plan)?

The architecture doc (§2.4) proposed CPGRAMS as the single default adapter. This research suggests **splitting by issue type** is better:

1. **Swachhata is garbage-specialized** - it's the official national cleanliness program with 4000+ ULB reach, whereas CPGRAMS is a general grievance portal that doesn't explicitly mention waste/garbage handling.
2. **Better routing confidence** - Swachhata's ULB framework routes waste complaints to the right municipal body; CPGRAMS's ministry-level routing may misroute municipal issues or route them slowly.
3. **Both lack APIs initially** - so implementation cost is the same (both are Tier 2 form-fill adapters); might as well use the more specialized tool for garbage.
4. **CPGRAMS still covers potholes as fallback** - it remains valuable as the broadest-reach grievance system, just not the sole default.

This split follows the architecture's own principle: *"Filing logic is pluggable (`FilingAdapter` interface)"* (§2.4). Use the best tool per issue class.

---

## Decisive Spikes per Adapter

### 1. SwachhataAdapter (Garbage → Swachhata App)

**Single spike needed:** Does MoHUA/Swachh Bharat Mission Urban provide partner API access for programmatic complaint filing, or is submission web-form-only?

**Steps:**
1. Contact MoHUA (via sbmurban.org) or the Swachh Bharat Mission Urban directorate to present TrashTag as a civic-tech partner generating high-quality, geo-verified, photo-documented garbage-dump reports.
2. Ask:
   - Is there a partner/NGO API for bulk complaint submission?
   - What is the auth model (API keys, OAuth, IP whitelist)?
   - Can complaint status be polled programmatically?
   - Are there rate limits or approval processes?
3. **If no API:** Build as Tier 2 adapter (form-fill assistant) - TrashTag drafts complaint packet (photo, GPS, reverse-geocoded address, description), human reviewer submits via web form at sbmurban.org or the Swachhata App, manually stores tracking ID.
4. **If API exists:** Build as Tier 1 adapter with full programmatic submission and status polling.

**Form constraints (if Tier 2):**
- Reverse-geocode GPS to address + ULB/city for location field
- Photo upload (1 required minimum, check size limits)
- Description (keep brief, <500 chars unless otherwise documented)
- Category selection (map TrashTag's "garbage" class to Swachhata's complaint type taxonomy - likely "Garbage Dump" or "Solid Waste Management")

---

### 2. CPGRAMSAdapter (Potholes → CPGRAMS)

**Two spikes needed:**

**Spike A:** Does CPGRAMS accept municipal road/pothole complaints, and do they route correctly?

**Steps:**
1. File a **test pothole complaint** via pgportal.gov.in:
   - Select a real GPS location in a known municipality (e.g., Bengaluru, Delhi)
   - Reverse-geocode to address
   - Choose grievance category (likely "Public Works" or "Ministry of Housing and Urban Affairs" → state/municipal PWD)
   - Submit with photo and description: "Pothole at [address], [GPS], causing traffic hazard. Request road repair."
2. Track using the registration ID returned.
3. Observe:
   - Does CPGRAMS route it to the correct municipal PWD/road authority, or does it get stuck at ministry level?
   - What is the actual resolution timeline (architecture doc claims 30-day SLA, but main portal says "reasonable time" - which is true)?
   - Does the complaint get a meaningful response, or generic closure?
4. **If routing works well:** CPGRAMS is a viable pothole adapter.
5. **If routing fails or routes poorly:** fall back to city-specific road apps (ICMC for Bengaluru, MCD 311 for Delhi, etc.) and mark CPGRAMS as "general grievance fallback only" rather than primary pothole channel.

**Spike B:** Does CPGRAMS (or any state's integrated portal) expose an API for partner/bulk submission?

**Steps:**
1. Check architecture doc claim: "some states/ministries already have API-based integration" (§2.4) - identify which states.
2. Contact DARPG or NIC (CPGRAMS operators) to ask:
   - Is there a partner API for civic-tech organizations to submit complaints programmatically?
   - Are any state portals integrated with CPGRAMS via API that TrashTag could leverage?
3. Search API Setu, data.gov.in, or NIC developer portals for "CPGRAMS API" or "grievance API" (note: this research pass found no public API docs, but partner-only access may exist).
4. **If API exists:** Build as Tier 1 adapter.
5. **If no API:** Build as Tier 2 (form-fill) - draft complaint packet respecting CPGRAMS format constraints from architecture doc §2.4:
   - Subject line: <100 chars
   - Description: <1000 chars initially (can extend via PDF attachment)
   - Attachments: PDF, max 4MB each, up to 5 files
   - Photo → convert to PDF for attachment
   - Store registration ID for status tracking

---

### 3. ICMCAdapter (Bengaluru City Override)

**Already researched** in `docs/research/ichangemycity-filing-adapter.md`. Single spike: Contact Janaagraha to confirm partner API access. If none, implement as Tier 2 form-fill assistant.

---

### 4. City-Specific Adapters (Delhi MCD 311, Mumbai MCGM, etc.)

**Spike per city:** Only build if:
1. City app is known to be operational and reliable (not subject to the "PMC Road Mitra went dark for months" fragility).
2. Coverage area is high-priority for TrashTag (Bengaluru, Delhi, Mumbai, Pune, Hyderabad, Chennai).
3. Spike confirms:
   - App/portal accepts both potholes and garbage complaints (or at least one of TrashTag's issue classes)
   - Form submission is stable (or API exists - rare)
   - Tracking ID and status updates are available
   - Municipal authority actually responds to complaints filed through the app

**Tier:** Most city apps will be Tier 2 (form-only). Only build as location overrides where they demonstrably outperform the national defaults (Swachhata, CPGRAMS).

---

### Summary: What to Spike First

**Immediate priority (before building any adapter):**
1. **Spike CPGRAMSAdapter (Spike A):** File test pothole complaint to validate routing and resolution. This is the **decisive technical question** for potholes. If it works, CPGRAMS is the default; if not, fall back to city apps.
2. **Contact MoHUA for SwachhataAdapter API:** Determines Tier 1 vs Tier 2 implementation. Parallel to CPGRAMS spike.

**Secondary priority (after MVP):**
3. **CPGRAMS API access (Spike B):** Upgrade from Tier 2 to Tier 1 if API exists.
4. **ICMC partnership for Bengaluru:** Upgrade ICMCAdapter from Tier 2 to Tier 1 if Janaagraha provides API.

**Lower priority (expand coverage):**
5. **City app spikes:** Only for high-priority cities where national defaults prove inadequate.

---

## Key Findings Summary

### What This Research Establishes

1. **No national portal covers both potholes AND garbage with equal strength** - necessitates issue-type split.
2. **No public APIs found** for any national grievance portal (CPGRAMS, Swachhata) - all initial adapters will be Tier 2 (form-based) until partnerships secured.
3. **Swachhata App is the strongest national garbage channel** - 4000+ ULB coverage, purpose-built for waste/cleanliness issues under Swachh Bharat Mission.
4. **CPGRAMS is the broadest-reach general grievance system** - but needs validation that it handles municipal potholes correctly (routing may be too high-level).
5. **City apps are fragmented and fragile** - use as location-specific overrides only where proven reliable (ICMC for Bengaluru is the only validated example from prior research).
6. **NHAI portals are too narrow** - national highways only, not relevant for urban pothole detection.

### What Remains Uncertain (Requires Spikes)

- Does CPGRAMS route municipal pothole complaints correctly, or do they get stuck at ministry level?
- Do MoHUA (Swachhata) or DARPG (CPGRAMS) provide partner API access for civic-tech organizations?
- What is the real CPGRAMS resolution SLA (architecture doc says 30 days, portal says "reasonable time")?
- Which cities have reliable, operational municipal complaint apps worth building adapters for?

---

## Sources

- Prior research: `docs/civic-vision-architecture-plan.md`, `docs/research/ichangemycity-filing-adapter.md`
- CPGRAMS portal: https://pgportal.gov.in (main page, about section)
- Swachh Bharat Mission Urban: https://sbmurban.org (main site, citizen interface)
- Ministry of Road Transport & Highways: http://morth.gov.in (limited content retrieved)
- NHAI: https://nhai.gov.in (limited content retrieved)
- API Setu: https://apisetu.gov.in, https://directory.apisetu.gov.in (no grievance APIs found in catalog)
- UMANG: https://web.umang.gov.in (limited content retrieved)

**Research limitations:**
- Many government portals returned minimal content (likely JavaScript-heavy SPAs that WebFetch cannot fully render) or blocked access (403 Forbidden).
- App store links (Google Play) for CPGRAMS and Swachhata apps returned 404 errors.
- No independent verification of CPGRAMS's 30-day SLA claim or Swachhata's ULB count (4000+) - these come from architecture doc and portal marketing copy, not audited data.
- API Setu directory search found no grievance/complaint APIs - but partner-only APIs may exist outside public catalog.

**Recommended validation before production:**
- Test-file complaints through CPGRAMS (pothole) and Swachhata (garbage) to observe actual routing, tracking, and resolution.
- Contact MoHUA and DARPG directly to confirm API access policies.
- Interview municipal officials or ward engineers to validate which complaint channels they actually monitor and respond to.
