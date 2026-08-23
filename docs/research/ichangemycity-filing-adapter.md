# I Change My City (ICMC) as a TrashTag Filing Adapter — Research & Recommendation

**Research Date:** August 23, 2026  
**Status:** Viable as Tier 2 (form-based) adapter; API access unconfirmed

---

## Executive Summary

I Change My City is a viable but **Tier 2** filing adapter candidate for TrashTag. It covers both TrashTag issue classes (potholes, garbage) across three cities (Bengaluru, Mumbai, Panaji), with a claimed 93.5% resolution rate and demonstrable municipal integration. However, **no public API exists** — submission is web-form-only for non-partners. ICMC would work best as a city-specific adapter for Bengaluru (where BBMP integration is strongest) rather than a national default, complementing CPGRAMS for locations where city-level engagement is preferred.

**Required spike:** Contact Janaagraha to confirm whether partner/NGO API access exists for bulk complaint filing, and whether TrashTag would qualify as a civic-tech partner.

---

## 1. What It Is

**I Change My City (ICMC)** is a civic engagement platform operated by the **Janaagraha Centre for Citizenship and Democracy**, a Bengaluru-based nonprofit founded in 2001. ICMC launched in Bengaluru in 2012 and has since expanded to Mumbai and Panaji. The platform describes itself as a "seamless bridge between government and citizens" for reporting and tracking civic issues.

**Relationship to municipal bodies:**  
- ICMC is **not a government portal** — it's an NGO-run platform that *integrates with* municipal systems.
- In Bengaluru, ICMC powers **SAHAAYA** (branded as "SAHAAYA Powered by I Change My City"), which is the semi-official citizen complaint system used by BBMP (Bruhat Bengaluru Mahanagara Palike).
- The platform has a formal partnership with DXC Technology for technical infrastructure.
- Complaints are routed to the relevant civic agency/ward engineer based on location mapping; ward boundaries and agency jurisdictions are pre-loaded into the system.
- **Constituency Connect** feature allows elected representatives (corporators, MLAs) to view and forward complaints to agencies, making it a genuine accountability/resolution tool rather than pure advocacy.

**Source:** [ichangemycity.com](https://www.ichangemycity.com), [janaagraha.org/projects/i-change-my-city](https://www.janaagraha.org/projects/i-change-my-city)

---

## 2. Geographic Coverage

**Three cities as of 2026:**  
- **Bengaluru** (Karnataka) — flagship city, strongest municipal integration (BBMP)
- **Mumbai** (Maharashtra)
- **Panaji** (Goa)

Additionally, Janaagraha developed the **Swachhata** platform (for the national Swachh Bharat Mission) targeting "all 4041 towns and cities of India," which was actively used by 1,000+ cities/towns as of 2017. However, ICMC itself remains limited to the three cities listed above for general civic complaints.

**Routing:** Complaints are mapped to **ward boundaries** and routed to the appropriate civic agency (e.g., BBMP for roads/garbage in Bengaluru, BWSSB for water/sewage, BESCOM for power). Location input is address/landmark-based rather than pure GPS, though the platform supports geo-mapping ("MAPS" feature for visualizing complaints).

**Source:** [ichangemycity.com](https://www.ichangemycity.com), [janaagraha.org](https://www.janaagraha.org)

---

## 3. Complaint Categories

ICMC supports **both of TrashTag's core issue classes:**

### Potholes
- "Fixing/Repairing Potholes"
- "Repair of Potholes on Roads"
- "Potholes"
- "1D - Repair existing roads (fill potholes)"

### Garbage/Solid Waste
- "Clearance Of Garbage Dump Or Black Spot"
- "Collection Of Door-to-door Garbage"
- "Implementation Of Waste Segregation/Garbage"
- "Garbage Dumping In Vacant Lot/Land"
- "Stop/Prevent Burning Of Garbage"
- "Build Garbage/Waste Composting Units"
- "Build Dry Waste Collection Centre"
- "Collection And Removal Of Garbage"
- "Burning of waste"
- Multiple specialized subcategories (healthcare waste, market waste, residential waste)

The platform also covers street lights, drainage/sewage, water supply, traffic, and other civic issues — making it a broader civic-engagement portal than a single-purpose pothole/garbage reporter.

**Source:** [ichangemycity.com/complaints](https://www.ichangemycity.com/complaints)

---

## 4. Submission Mechanism (API?)

**Key finding: No public API documented or discovered.**

### What exists:
- **Web form** at [ichangemycity.com/complaints/post-complaint](https://www.ichangemycity.com/complaints/post-complaint) — four-step process:
  1. Select complaint category (dropdown)
  2. Enter location (address + landmark, ward-mapped)
  3. Add description + photo (**photo required**)
  4. Create/login to user account
- **Mobile apps** (Android, iOS, Windows) — submit complaints in real-time with photos
- **Backend API endpoint** at `https://api.ichangemycity.com/api/` exists (referenced in page source), but returns 404 on direct access and has no public documentation

### What does NOT exist (publicly):
- No developer documentation at `/api`, `/developers`, or `/docs`
- No mention of API keys, OAuth, or programmatic access on the public site
- No GitHub repos, SDKs, or integration guides found in search
- Google Scholar, data.gov.in, and civic tech sources yielded no technical integration details

### Complaint tracking:
- Complaints receive a **tracking ID** (called "generic ID" in templates)
- Status states: `Open → On The Job → Resolved → Closed` (with option to re-open)
- Citizens can vote-up complaints and leave comments
- Status updates visible on the platform; unclear if email/SMS notifications are sent

### Assessment:
ICMC is **form-only for non-partners**. The existence of a backend API suggests partner/internal access may exist (e.g., for BBMP's SAHAAYA integration), but this would require a formal partnership negotiation with Janaagraha. TrashTag cannot programmatically file complaints without such a partnership.

**Source:** Site inspection of [ichangemycity.com](https://www.ichangemycity.com), page source analysis

---

## 5. Reliability & Track Record

### Impact data (as of June 2017):
- **244,928 total complaints filed**
- **174,057 resolved** (71% resolution rate)
- **607,931 registered users**
- Platform claims **93.5% resolution rate** on current site (date unstated; likely updated figure)

### Recognition:
- **Google Global Impact Award — India 2013**
- Partnership with **Swachh Bharat Mission** (Ministry of Urban Development)
- Collaboration with **Bengaluru Traffic Police** (Public Eye app for traffic violations)

### Active maintenance:
- Site is operational as of August 2026
- Recent complaints visible (date-stamped)
- Mobile apps available on App Store and Google Play (though specific app pages were inaccessible during research)

### Known issues/limitations:
- **Wikipedia article** on Janaagraha carries maintenance flags for "promotional content" and needing "more citations" — suggests ICMC's claimed impact may lack independent verification
- Data is dated (2017 figures are 9 years old; current volume/resolution stats not publicly available)
- City-specific fragility example from TrashTag's architecture doc: PMC's Road Mitra (a competing Pune city app) went dark for months in 2026 over an unpaid SMS gateway — ICMC's NGO funding model may carry similar operational risk, though its DXC Technology partnership and longevity (14 years) suggest greater stability

**Source:** [janaagraha.org](https://www.janaagraha.org), [Wikipedia: Janaagraha](https://en.wikipedia.org/wiki/Janaagraha)

---

## 6. Comparison vs. CPGRAMS

| Criterion | I Change My City | CPGRAMS | Winner |
|-----------|------------------|---------|--------|
| **Geographic coverage** | 3 cities (Bengaluru, Mumbai, Panaji) | National (all states/ministries that subscribe) | **CPGRAMS** — broader reach |
| **Issue categories** | Strong fit — explicit pothole/garbage categories, plus broader civic issues | General grievances; less granular issue taxonomy | **ICMC** — better category match |
| **API access** | None public; partner-only (unconfirmed) | Varies by state; some have API, many don't (per architecture doc) | **Tie** — both require spike to confirm |
| **Municipal integration** | Direct BBMP integration (Bengaluru), ward-level routing | Auto-routes to Grievance Redressal Officer, but varies by state | **ICMC** — tighter city-level integration where it exists |
| **Tracking/accountability** | Complaint ID, status updates, vote-ups, corporator visibility | Registration ID, SLA (30-day), 5-level appeal path | **CPGRAMS** — stronger legal/SLA backing |
| **Resolution rate** | 93.5% claimed (date unknown) | Varies by state/ministry; SLA-enforced but not publicly reported as aggregate | **ICMC** — higher claimed rate, but less verifiable |
| **Citizen engagement** | High — voting, comments, community features | Low — form submission, status polling only | **ICMC** — advocacy/transparency layer |
| **Operational risk** | NGO-run; funding-dependent | Government-run; more stable but fragile at state level (PMC Road Mitra example) | **Tie** — different risk profiles |
| **TrashTag role** | Best as **city-specific adapter** for Bengaluru (maybe Mumbai/Panaji) | Best as **national default/fallback** | **Complementary, not competitive** |

---

## 7. Recommendation: Tier 2 Adapter, Bengaluru-Specific

### Is it worth building an `ICMCAdapter`?
**Yes, as a Tier 2 (manual/export) adapter for Bengaluru** — but not as TrashTag's default/national filing target.

### Rationale:
1. **Strong city-level fit for Bengaluru:** ICMC's BBMP integration, ward-level routing, and 14-year track record make it the *best* complaint channel for Bengaluru-detected issues — better than CPGRAMS for city-specific civic problems.
2. **Coverage gap:** Only 3 cities means ICMC cannot replace CPGRAMS as TrashTag's default. It's a city-specific upgrade, not a national adapter.
3. **Form-only submission:** Without API access, `ICMCAdapter` would be a **complaint packet generator + guided form-fill** tool (similar to CPGRAMS's Tier 1 design if CPGRAMS API access isn't confirmed). TrashTag drafts the complaint (photo, GPS, description, category-matched to ICMC's taxonomy), and a human reviewer submits via ICMC's web form.
4. **Citizen engagement advantage:** ICMC's vote-up/comment/transparency features give TrashTag-filed issues a public accountability layer that CPGRAMS lacks — useful for building trust in the platform.

### Tier classification:
- **Tier 2** — manual/form-based submission until/unless a partnership with Janaagraha is negotiated for API access.
- If API access is secured, upgrade to **Tier 1**.

### Adapter scope:
- **Primary:** Bengaluru (BBMP jurisdiction)
- **Secondary:** Mumbai, Panaji (lower confidence in municipal integration strength; would need validation)
- **Not applicable:** All other locations — fall back to `CPGRAMSAdapter`

---

## 8. Required Spike Before Building

**Single confirmation needed:** Does Janaagraha offer partner/NGO API access for bulk complaint filing?

### Steps:
1. Contact Janaagraha's civic-tech team via their website ([janaagraha.org](https://www.janaagraha.org)) or ICMC's partnership inquiry channel (if one exists).
2. Present TrashTag as a civic-tech platform that would generate high-quality, geo-verified, photo-documented complaints for BBMP and other municipalities.
3. Ask:
   - Is there a partner API for programmatic complaint submission?
   - What is the authentication/authorization model (API keys, OAuth, IP whitelist)?
   - Are there rate limits or bulk-upload constraints?
   - Can TrashTag poll complaint status programmatically, or is status-tracking manual-only?
   - Does partnership require formal MOU, data-sharing agreement, or fee?

### If no API:
- Build `ICMCAdapter` as a **form-fill assistant** (draft complaint → pre-fill web form fields → human submits).
- Store the ICMC complaint URL/ID manually after submission for status tracking.

### If API exists:
- Build as **Tier 1 adapter** with full programmatic submission and status polling.

---

## 9. Adapter Design Notes (If Proceeding)

Assuming Tier 2 (form-based):

### Complaint generation logic:
```python
class ICMCAdapter(FilingAdapter):
    """Bengaluru-specific adapter for I Change My City (BBMP SAHAAYA integration)."""

    COVERAGE = [
        "Bengaluru",
        "Mumbai",
        "Panaji",
    ]  # ponytail: hardcoded city list, expand via jurisdiction DB later

    CATEGORY_MAP = {
        "pothole": "Fixing/Repairing Potholes",
        "garbage": "Clearance Of Garbage Dump Or Black Spot",
    }

    def generate_complaint(self, issue: Issue) -> ComplaintPacket:
        return ComplaintPacket(
            category=self.CATEGORY_MAP[issue.class_type],
            location_address=issue.reverse_geocoded_address,  # address + landmark
            location_ward=issue.ward_number,  # if available from jurisdiction DB
            description=self._format_description(
                issue
            ),  # <1000 chars, ICMC has no stated limit but keep brief
            photo=issue.primary_evidence_photo,  # ICMC requires 1 photo minimum
            tracking_note="Complaint drafted for I Change My City. Submit at: https://www.ichangemycity.com/complaints/post-complaint",
        )
```

### Human-in-the-loop:
- TrashTag ops dashboard shows the drafted complaint packet.
- Reviewer clicks "File via ICMC" → opens pre-filled form (via URL params if ICMC supports them, or manual copy-paste).
- Reviewer submits, copies the ICMC complaint ID back into TrashTag.
- TrashTag stores `icmc_complaint_url` and `status="filed_icmc"`.

### Status polling:
- Manual for Tier 2 — reviewer checks ICMC periodically and updates TrashTag issue status.
- If API access is later secured, add automated polling.

---

## 10. Sources & Verification

All claims sourced from:
- [ichangemycity.com](https://www.ichangemycity.com) (main site, complaint pages)
- [janaagraha.org](https://www.janaagraha.org) (organizational background, ICMC impact data)
- [Wikipedia: Janaagraha](https://en.wikipedia.org/wiki/Janaagraha)
- Site source inspection (`https://api.ichangemycity.com/api/` endpoint discovery)

**Limitations:**
- Many secondary sources (news articles, app store pages) were inaccessible during research due to fetch/redirect failures.
- Impact data is dated (2017); current complaint volume and resolution rates not independently verified.
- No direct confirmation of BBMP's operational use of SAHAAYA beyond branding mentions on ICMC site.

**Recommended validation before production:**
- Contact Janaagraha to confirm API access and partnership model.
- Test ICMC submission flow end-to-end (create test account, file sample pothole/garbage complaint, track to resolution).
- Validate that BBMP engineers actually receive and act on ICMC complaints (interview ward engineer or check BBMP's official complaint portal for cross-listing).

---

## Conclusion

I Change My City is a **strong city-specific adapter for Bengaluru**, with good category fit, municipal integration, and a 14-year track record. However, its 3-city coverage and lack of public API make it a **complement to CPGRAMS**, not a replacement. TrashTag should:
1. Keep **CPGRAMS as the default national adapter** (per architecture doc §2.4).
2. Build **`ICMCAdapter` as a Bengaluru-specific override** for TrashTag issues detected in BBMP jurisdiction.
3. Spike on Janaagraha partnership for API access — if secured, upgrade to Tier 1; if not, implement as Tier 2 form-fill assistant.

This gives TrashTag the best of both worlds: national reach via CPGRAMS, and city-level accountability/engagement via ICMC where it's strongest.
