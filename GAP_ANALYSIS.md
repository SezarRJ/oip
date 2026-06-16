# OIP — Deep Dive Gap Analysis
## June 16, 2026

## EXECUTIVE SUMMARY

**Current state:** v1.0.0 is a functional proof-of-concept. All core engines run, demo pipeline works, 51 opportunities detected across 13 detectors.  
**Total source:** 2,211 Python + 347 SQL + 452 doc + 129 YAML = working code.  
**The gap:** The system is a skeleton. It has the right architecture but nearly every component is a stub or uses synthetic/hardcoded data.

---

## TIER 1: CRITICAL (System non-functional without these)

### CRIT-1: Zero Live Data Collectors
- **Spec:** 20+ sources: Alibaba, Made-in-China, TradeKey, TurkExim, UN Comtrade, ITC Trade Map, DG Market, Etimad, EKAP, Reuters, Bloomberg, Trade Arabia, Iraq Business News, plus search engines, social, forums
- **Current:** Only `base.py` with abstract classes. No collectors exist. Pipeline uses `_generate_demo_data()` hardcoded in orchestrator
- **Impact:** Cannot discover real opportunities. Entire radar is blind.

### CRIT-2: No Data Extraction Layer
- **Spec:** Extract company (name, address, GPS, email, phone, WhatsApp, decision makers, size, certifications), product (specs, HS code, MOQ, pricing, lead time, weight, packaging), demand signal (buyer, RFQ, volume, timeline, budget)
- **Current:** `data_extraction/` directory is empty. All demo data is manually structured
- **Impact:** Raw HTML/API responses cannot become structured records

### CRIT-3: No Database Connection
- **Spec:** PostgreSQL 15+ with PostGIS, 10 tables, 2 materialized views, triggers
- **Current:** `schema.sql` exists (347 lines) but no Python connects to any database. No SQLAlchemy models. No ORM. Pipeline runs entirely in-memory
- **Impact:** Nothing persists. No history. No trends. No deduplication across runs.

### CRIT-4: Missing Information Arbitrage Detector
- **Spec:** 14 detector types include Information Arbitrage
- **Current:** `OpportunityType` enum has it. `self.detectors` dict has 13 entries — INFORMATION_ARBITRAGE is never registered. Method deleted during refactoring
- **Impact:** One of 14 core opportunity types is completely missing

---

## TIER 2: HIGH (Core functionality broken or misleading)

### HIGH-1: Detection Analysis is Template Text, Not Real Analysis
- Every detector outputs fixed strings: `"3-6 months"`, `"Information asymmetry"`, `"No domestic production"`
- `competitor_analysis` field is **always empty string** — never populated by any detector
- `window_estimate` is hardcoded per detector, not calculated from data
- **Impact:** The "intelligence" in "Opportunity Intelligence" is templated filler text

### HIGH-2: Every Opportunity Gets 25% Target Margin — Fantasy Pricing
- `ProfitabilityEngine.calculate()` applies `total_cost * 1.25` for **every single opportunity** regardless of product, corridor, or market conditions
- No market-driven pricing. No demand-side price discovery. No competitive margin analysis
- **Impact:** All ROI estimates are fictional. Some products can't command 25% margin; others can command 80%

### HIGH-3: Risk Scores Are Static Country Baselines, Not Data-Driven
- Supplier risk defaults to 60.0 when no data is passed (most cases)
- Country risk is a hardcoded lookup table (`IQ: 0.50`, `SY: 0.70`)
- No real currency volatility data, no real political risk feeds, no counterparty history
- **Impact:** Risk scores don't reflect actual current conditions

### HIGH-4: Briefing Score Map is Broken — Everything Shows Score: 0
- `run_briefing_phase()` builds score map with key = `opp.title`
- `generate_briefing()` → `_top_by_capital()` → `_format_opp_entry()` tries to read score from a different implied key
- **Impact:** The daily briefing — the single most important output — shows Score: 0 for every entry. The core deliverable is broken.

### HIGH-5: Brokerage Profit Math is Wrong
- Brokerage opportunities have `commission_based=True` which gives them 3% of deal size as commission
- BUT the purchase cost from `opp.capital_required_estimate * 0.7` is also calculated, so the "capital required" shows non-zero for a zero-capital opportunity
- The profit shows `commission - total_cost + expected_selling_price` which creates inflated numbers
- **Impact:** Brokerages (the best opportunities) have misleading financials

### HIGH-6: No Persistence — Every Run is a Clean Slate
- `previous_opportunity_ids` is an in-memory `set()` lost on restart
- No way to compare today vs yesterday vs last week
- **Impact:** Cannot answer "what's new?", "what changed?", "what's trending?"

---

## TIER 3: MEDIUM (Reduced capability)

### MED-1: No Currency Conversion
- Schema has `currency_rates` table. Config lists 14 currencies. All calculations are USD-only
- No exchange rate API integration. No conversion logic anywhere
- Products priced in TRY, IRR, IQD would break the system

### MED-2: HS Codes Are Strings, Not Intelligence
- Products carry HS code strings but no HS code validation, lookup, or intelligence
- Customs rates are fixed per country-pair, ignoring HS code entirely (schema has HS-code-specific customs rates but code doesn't use them)
- No HS code → trade flow analysis (what's actually moving per UN Comtrade?)

### MED-3: No Alerts or Notifications
- Briefing is printed to stdout only. No email. No SMS. No push
- Critical opportunities (urgency=critical) don't trigger any alert
- Operator must manually run CLI to see anything

### MED-4: No Geospatial Analysis
- Schema has PostGIS geography columns and spatial indexes
- No Python code uses geospatial queries
- Cannot answer "closest cement supplier to Baghdad" or "all suppliers within 200km of port"

### MED-5: Source/Demand Markets Hardcoded in Detector Code
- `srcs = {"TR","CN","IR","IQ","SY"}` — hardcoded in `_detect_trade_arbitrage()`
- Same pattern in `_detect_demand_gap()` and `_detect_supply_gap()`
- Spec says "new countries can be added easily" — they cannot; requires code changes

### MED-6: No Product Name Fuzzy Matching
- Matching uses `pr.get("name","").lower() in [n.lower() for n in needed]` — naive substring
- "LED lights" won't match "led lighting"; "cement" won't match "Portland cement"
- No TF-IDF, no embeddings, no synonym handling, no multilingual matching

### MED-7: Demo Data Embedded in Pipeline Orchestrator (350+ lines)
- `_generate_demo_data()` is inside `pipeline/orchestrator.py` making it 733 lines
- Violates separation of concerns. Can't be reused by tests independently

### MED-8: No Opportunity Expiry Tracking
- `expires_at` field exists on `DetectedOpportunity` but is **never set** by any detector
- Tenders with deadlines won't auto-expire. Expired opportunities keep appearing forever

### MED-9: No Error Recovery / Retry / Dead-Letter Queue
- Failed collector → silent skip with log. Failed analysis → silent skip. Failed scoring → silent skip
- No retry with backoff. No dead-letter queue. No alert when detection rate drops

### MED-10: Shipping Costs Are Static Hardcoded Lookup Tables
- `self.shipping_estimates` dict in profitability engine never updates
- Real shipping rates fluctuate weekly. System is blind to rate changes

---

## TIER 4: LOW (Polish and completeness)

### LOW-1: Zero Tests — No Test Files Anywhere
- No `tests/` directory. No pytest. No coverage. 2,211 lines of Python with zero assertions

### LOW-2: Config File is Never Loaded or Validated
- `config/settings.yaml` (129 lines) exists but no Python code reads it
- The `config` parameter passes through all constructors but is never used
- Changing YAML has zero effect on runtime

### LOW-3: Logging is a Quick-Fix Hack
- Replaced `loguru` with `import logging; logger = logging.getLogger("OIP")` inline, 5 separate times
- No logging config, no levels, no handlers, no rotation, no structured format

### LOW-4: No Containerization
- No Dockerfile, no docker-compose, no deployment instructions beyond `pip install`
- PostgreSQL dependency is undocumented in deployment steps

### LOW-5: No Opportunity Execution Tracking
- `executed_at` field exists in schema but nothing writes to it
- No "accepted/rejected/executed/outcome" workflow
- Learning loop is broken — can't track which opportunities actually worked

### LOW-6: Empty `__init__.py` Files — Module Structure is Skeletal
- 17 `__init__.py` files, many zero bytes, serving only to make directories importable
- No meaningful package-level exports or documentation

### LOW-7: No Historical Price Tracking in Code
- `product_price_history` table exists in schema. No code reads or writes to it
- Cannot detect price drops, inflation, seasonal patterns

### LOW-8: `detected_at` Never Used for Trend Analysis
- Every `DetectedOpportunity` has `detected_at = datetime.utcnow()`
- But without persistence, this is meaningless — every run is "now"

---

## GAP COUNT BY TIER

| Tier | Count | Items |
|------|-------|-------|
| CRITICAL | 4 | CRIT-1 through CRIT-4 |
| HIGH | 6 | HIGH-1 through HIGH-6 |
| MEDIUM | 10 | MED-1 through MED-10 |
| LOW | 8 | LOW-1 through LOW-8 |
| **TOTAL** | **28** | |

---

## FIX PRIORITY ROADMAP

### Phase 1 — Make It Real (CRIT-1, CRIT-2, CRIT-3)
- Build 3-5 live collectors (Alibaba, UN Comtrade, DG Market, Reuters, Trade Arabia)
- Build extraction layer (CompanyExtractor, ProductExtractor, DemandSignalExtractor)
- Wire PostgreSQL with SQLAlchemy, write-through pipeline, persistence
- Add information arbitrage detector (CRIT-4)
- **Outcome:** System ingests real data and persists it

### Phase 2 — Make It Smart (HIGH-1 through HIGH-6)
- LLM-powered competitive analysis per opportunity
- Market-driven pricing instead of fixed 25%
- Real-time currency and political risk data
- Fix briefing score keying (broken Score: 0)
- Fix brokerage profit calculation
- Database-backed trend detection across runs
- **Outcome:** Opportunities genuinely scored against real data

### Phase 3 — Make It Reliable (MED-1 through MED-10)
- Live exchange rate integration
- HS code intelligence
- Email/SMS alerts for critical opportunities
- Geospatial proximity queries
- Configuration-driven country management
- Product name fuzzy matching (embeddings)
- Shipping rate refresh
- **Outcome:** Production-grade capability

### Phase 4 — Make It Polished (LOW-1 through LOW-8)
- Full test suite
- Configuration loading and validation
- Structured logging
- Docker Compose (app + PostgreSQL)
- Execution tracking and learning loop
- Web dashboard
- **Outcome:** Complete platform matching full specification
