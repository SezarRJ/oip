# OPPORTUNITY INTELLIGENCE PLATFORM (OIP)
## Complete Application Workflow — 14-Stage Architecture

**Version:** 2.0.0
**Classification:** Personal AI Opportunity Radar — Not SaaS — Single Operator
**Core Question:** *"If I had \$X available today, where should I deploy it for highest probability-adjusted profit?"*

---

## ARCHITECTURE OVERVIEW

```
                        ┌───────────────────────────────────────┐
                        │         THE OIP DATA RIVER            │
                        │                                       │
  RAW WORLD ────────────┤  1.COLLECT → 2.CLEAN → 3.RESOLVE     │
  (web, news,           │       ↓           ↓         ↓         │
   tenders, trade       │  4.GRAPH → 5.SIGNALS → 6.DETECT      │
   data, social)        │       ↓           ↓         ↓         │
                        │  7.VALIDATE → 8.PROFIT → 9.RISK       │
                        │       ↓           ↓         ↓         │
                        │  10.SCORE → 11.DEBATE → 12.DECIDE     │
                        │       ↓           ↓         ↓         │
  OPERATOR ←────────────┤  13.ACT → 14.LEARN (feedback loop)   │
  (daily action plan    │                                       │
   + capital report)    └───────────────────────────────────────┘
```

### Data Flow Principle

Every stage feeds the next. No stage calls backwards. The feedback loop (Stage 14) feeds Stage 10 (scoring weights) and Stage 11 (debate priors) asynchronously — it never blocks the forward pipeline.

---

## STAGE 1 — CONTINUOUS DATA COLLECTION

### Purpose
Transform the chaotic open web and structured data sources into a raw intelligence stream. This is the platform's sensory nervous system.

### Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    COLLECTION ORCHESTRATOR                        │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ MARKETPLACE│ │ TRADE DB │ │ TENDER   │ │ NEWS     │  ...      │
│  │ COLLECTORS│ │COLLECTORS│ │COLLECTORS│ │COLLECTORS│           │
│  └─────┬─────┘ └─────┬────┘ └─────┬────┘ └─────┬────┘           │
│        │             │            │            │                 │
│  ┌─────┴─────────────┴────────────┴────────────┴─────┐          │
│  │              CONCURRENT ASYNC EXECUTOR              │          │
│  │         (rate-limited, proxy-rotated, retried)      │          │
│  └───────────────────────┬────────────────────────────┘          │
│                          ↓                                       │
│                  RAW INTELLIGENCE STREAM                          │
│               (append-only, timestamped, hashed)                  │
└──────────────────────────────────────────────────────────────────┘
```

### Inputs
20+ data source categories: B2B marketplaces (Alibaba, Made-in-China, TradeKey), trade databases (UN Comtrade, ITC TradeMap), tender platforms (DGMarket, Etimad, EKAP), news sources (Reuters, Bloomberg, Trade Arabia), government portals, logistics providers, search engines, business directories, industry forums, social media, economic reports.

### Processing Logic

Each collector is an isolated async agent with:
1. **Authentication/session management** — API keys, cookie jars, login flows
2. **Rate limiting with jitter** — prevents IP bans, respects robots.txt
3. **Proxy rotation** — residential/mobile proxies for geo-blocked sources
4. **Incremental collection** — If-Modified-Since, ETags, cursor-based pagination
5. **Content fingerprinting** — SHA-256 of normalized content to skip duplicates at ingest
6. **Error classification** — transient (retry with backoff) vs permanent (quarantine source)
7. **Collection health metrics** — items/sec, error rate, freshness age

### AI Agents Involved
- **Collection Scheduler Agent** — adjusts frequency based on source velocity (high-churn sources get higher frequency)
- **Source Health Monitor Agent** — detects silent failures (source still responding but returning stale/empty data)
- **Adaptive Scraper Agent** — when a site changes its DOM structure, detects the break and suggests new selectors

### Output: RawItem
```
RawItem {
    item_id: UUID, source_name: str, source_type: enum
    collection_timestamp: datetime, source_timestamp: datetime
    content_type: enum, raw_content: bytes, url: str
    content_hash: str, parse_attempts: int, parse_status: enum
    collector_version: str
}
```

### Storage
- PostgreSQL raw_items table (append-only, partitioned by week)
- S3/MinIO for PDFs and large HTML
- collection_runs table — one row per collector per run with stats

### Decision Criteria
- **Frequency adjustment:** >80% new items per run → increase frequency. <20% new → decrease.
- **Source quarantine:** Error rate >30% over 6 consecutive runs → flag for manual review.
- **Duplicate suppression:** Identical content hashes within 24h → dropped at ingest.

---

## STAGE 2 — DATA CLEANING & NORMALIZATION

### Purpose
Convert the raw, multilingual, inconsistent data stream into structured, normalized, trusted records.

### Processing Pipeline

```
RawItem → LANGUAGE DETECT → DECODE & EXTRACT → SPAM FILTER → FRAUD DETECTOR
       → CURRENCY NORM (→ USD) → UNIT NORM (→ SI) → NAME NORM
       → ADDRESS NORM → COUNTRY NORM (→ ISO 3166-1 alpha-2)
       → DATE NORM (→ UTC ISO 8601) → PHONE NORM (→ E.164)
       → QUALITY SCORE (0-10) → CleanedItem
```

### AI Agents Involved
- **Spam Detection Agent** — embedding-based classifier using multilingual sentence embeddings (LaBSE) for Arabic, Chinese, Turkish, Farsi
- **Fraud Pattern Agent** — rule-engine + anomaly detection. Flags: newly registered domains, email-only contact, prices >3σ below category mean, mismatched country/phone
- **Deduplication Agent** — fuzzy matching: same if company name similarity >0.85 AND city matches AND product similarity >0.80

### Output: CleanedItem
```
CleanedItem {
    item_id: UUID, raw_item_id: UUID, entity_type: enum
    language: str, company_name: str, country_code: str, city: str
    address_structured: {street, district, city, region, postal_code, country}
    contact: {email, phone, whatsapp, website}
    products: [NormalizedProduct], demand: NormalizedDemand, intel: NormalizedIntel
    completeness_score: float, spam_probability: float, fraud_probability: float
    is_duplicate: bool, duplicate_of: UUID
}
```

### Decision Criteria
- **Discard:** Spam probability >0.90 OR fraud probability >0.80 → quarantine
- **Review:** Completeness <3.0/10 AND entity_type=COMPANY → human review queue
- **Merge:** Duplicate confidence >0.85 → merge, update freshness timestamp

---

## STAGE 3 — ENTITY RESOLUTION

### Purpose
The same company exists on Alibaba as "Ankara Çelik Sanayi A.Ş.", on TradeKey as "Ankara Steel Industries", and in UN Comtrade as reporter code 792. Create unified master entities — one golden record per real-world entity.

### Processing Logic

```
CleanedItems → CANDIDATE GENERATION (name n-gram blocking, phone/email exact match,
               domain match, geo-hash proximity)
            → PAIRWISE SCORING (name similarity 0.30 + location match 0.20
               + contact match 0.25 + product overlap 0.15 + certifications 0.10)
            → GRAPH CLUSTERING (connected components >0.75, Louvain community detection)
            → GOLDEN RECORD GENERATION (best field per source reliability)
            → MasterEntity
```

### AI Agents Involved
- **Entity Resolution Agent** — runs pairwise scoring and clustering. Retrained on operator feedback.
- **Ambiguity Resolution Agent** — handles gray zone (0.65-0.85 similarity). Presents cases with recommendations.
- **Golden Record Agent** — selects best field values preferring: verified sources > government data > direct manufacturer claims > marketplace listings.

### Output — Master Entity Types

```
MasterCompany {
    master_id: UUID, canonical_name: str, aliases: [str]
    names_localized: {lang: str}, country_code: str, city: str
    geolocation: (lat, lon), contact: {email, phone, whatsapp, website}
    company_type: enum, employees_estimate: int, years_in_business: int
    certifications: [str], reliability_score: float, source_records: [UUID]
    confidence: float, first_seen: datetime, last_updated: datetime
}

MasterProduct {
    master_id: UUID, canonical_name: str, category: str, hs_code: str
    specifications_normalized: JSON, manufacturer_master_id: UUID
    source_records: [UUID], confidence: float
}

MasterDemand {
    master_id: UUID, signal_type: enum, title: str, description: str
    buyer_master_id: UUID, buyer_country: str, products_needed: [str]
    estimated_budget_usd: float, deadline: datetime, tender_ref: str
    tender_status: enum, source_records: [UUID], confidence: float
}
```

### Storage
- master_companies table with PostGIS geography, GIN trigram indexes
- master_products table with HS code index
- master_demands table with deadline index
- entity_resolution_edges table (source_A, source_B, similarity_score, resolved_status)

---

## STAGE 4 — KNOWLEDGE GRAPH CREATION

### Purpose
Connect every entity into a traversable market graph revealing hidden relationships.

### Graph Schema

**Node Types:** COMPANY, PRODUCT, DEMAND, COUNTRY, PORT, HS_CODE, PROJECT, TENDER

**Edge Types (weighted, directed where meaningful):**
- COMPANY → MANUFACTURES → PRODUCT (capacity, leadtime)
- COMPANY → DISTRIBUTES → PRODUCT (region, markup)
- COMPANY → EXPORTS_TO → COUNTRY (volume_usd, hs)
- PRODUCT → HAS_HS_CODE → HS_CODE (confidence)
- PRODUCT → SHIPS_VIA → ROUTE (cost, days)
- DEMAND → NEEDS → PRODUCT (qty, deadline)
- DEMAND → ISSUED_BY → COMPANY (role: buyer)
- DEMAND → LOCATED_IN → COUNTRY (city)
- PROJECT → REQUIRES → PRODUCT (budget_line)
- PROJECT → LOCATED_IN → COUNTRY (city, gps)
- TENDER → SEEKS → PRODUCT (lot_no, qty)
- COUNTRY → HAS_PORT → PORT (type)
- COUNTRY → HAS_TARIFF → HS_CODE (rate, effective)
- COUNTRY → TRADES_WITH → COUNTRY (volume, balance)
- ROUTE → CONNECTS → PORT → PORT (mode, cost, freq)

**Derived Edges (computed, not stored):**
- COMPANY → CAN_FULFILL → DEMAND (match score)
- PRODUCT → ARBITRAGE → COUNTRY (price_gap)
- COMPANY → COMPETES_WITH → COMPANY (product overlap)

### Technology
- **Storage:** Neo4j or PostgreSQL with Apache AGE for production. NetworkX + in-memory dicts for lightweight operation.
- **Query language:** Cypher (Neo4j/AGE)
- **Indexes:** Node property indexes on country_code, hs_code, product_category

### Key Queries

```cypher
// Products needed by active tenders where supply exists
MATCH (d:DEMAND {status:'active'})-[:NEEDS]->(p:PRODUCT)<-[:MANUFACTURES]-(c:COMPANY)
WHERE d.deadline > date() AND c.country <> d.country
RETURN c, p, d

// Arbitrage: products with >30% price gap between countries
MATCH (p1:PRODUCT)-[:HAS_HS_CODE]->(hs:HS_CODE)<-[:HAS_HS_CODE]-(p2:PRODUCT)
WHERE p1.country <> p2.country AND p2.unit_price > p1.unit_price * 1.3
RETURN p1, p2, (p2.unit_price - p1.unit_price) / p1.unit_price as margin

// Companies positioned for reconstruction project
MATCH (proj:PROJECT {type:'reconstruction'})-[:REQUIRES]->(p:PRODUCT)
MATCH (c:COMPANY)-[:MANUFACTURES]->(p)-[:EXPORTS_TO]->(proj.country)
RETURN c, count(p) as products_matched ORDER BY products_matched DESC
```

---

## STAGE 5 — SIGNAL DETECTION

### Purpose
The continuous radar. Scan the unified entity stream + knowledge graph for statistically significant changes that may indicate opportunity.

### Signal Types and Detection Methods

| Signal | Detection Method | Sensitivity |
|--------|-----------------|-------------|
| Demand Spike | Product mentions >2σ above 30-day rolling mean | High |
| Demand Collapse | Product mentions drop >50% vs 90-day baseline | Medium |
| Supply Shortage | Active suppliers drop below threshold OR "shortage" in news sentiment | Critical |
| Supply Surplus | Price drops >2σ below category mean | Medium |
| Price Increase | Unit price up >15% in 30 days | Medium |
| Price Decrease | Unit price down >15% in 30 days | High |
| New Supplier | MasterCompany created, not seen before | Medium |
| New Buyer | MasterDemand from a buyer not in graph | Medium |
| New Project | Project-type demand with budget >$1M | High |
| New Tender | Tender open with deadline within 30 days | Critical |
| Regulation Change | MarketIntel with regulation_change + opportunity sentiment | Critical |
| Tariff Change | Duty rate changed >2% | High |
| Shipping Cost Change | Container cost changed >20% | Medium |
| Currency Event | Exchange rate moved >5% in 7 days | High |
| Market Anomaly | Multiple signals for same product/country simultaneously | High |

### AI Agents Involved
- **Statistical Signal Agent** — rolling z-score detection on all time-series metrics
- **NLP Signal Agent** — scans MarketIntel for signal keywords, classifies sentiment, extracts affected entities
- **Cross-Signal Correlation Agent** — multiple weak signals → strong composite signal
- **Anomaly Detection Agent** — Isolation Forest on (product, country, price, volume, count, sentiment)

### Output: MarketSignal
```
MarketSignal {
    signal_id: UUID, signal_type: enum, detection_method: str
    entities_involved: {products: [UUID], countries: [str], companies: [UUID]}
    metrics: {current_value: float, baseline_value: float, z_score: float, confidence: float}
    source_items: [UUID], detected_at: datetime, severity: enum
    expires_at: datetime, related_signals: [UUID]
}
```

### Storage
- market_signals table with time-series partition
- Signal decay: LOW expires 7 days, MEDIUM 30 days, HIGH 90 days, CRITICAL never

---

## STAGE 6 — OPPORTUNITY DETECTION

### Purpose
Convert signals into concrete, named opportunities. A signal says "steel prices are up in Iraq." An opportunity says "Buy Turkish rebar at $580/ton, ship to Basra at $55/ton, clear customs at 5% duty, sell at $780/ton — 22% net margin, repeatable monthly."

### 14 Detector Agents

| # | Detector | Pattern | Key Trigger |
|---|----------|---------|-------------|
| D1 | Trade Arbitrage | Price_A + shipping + duties + risk < Price_B | Price divergence for same HS code |
| D2 | Information Arbitrage | Knowledge of demand before market | MarketIntel ahead of public posting |
| D3 | Supply Gap | Demand exists, zero local supply | Demand spike + no local suppliers |
| D4 | Demand Gap | Supply exists, no visible demand (create market) | Supply surplus + zero demand signals |
| D5 | Inventory Liquidation | Price >2σ below mean, large MOQ | Price decrease + high MOQ + urgency |
| D6 | Project Procurement | Large project with specific needs | New project signal + budget >$100K |
| D7 | Tender Opportunity | Open tender + matching supply | New tender + supplier match in graph |
| D8 | Reconstruction | Post-conflict + construction materials | Reconstruction keywords + SY/IQ/LY |
| D9 | Regional Shortage | Supply disruption across >=2 countries | Multiple shortage signals |
| D10 | Emerging Demand | Same product requested >=3x in 60 days | Demand spikes for quiet product |
| D11 | Regulatory Change | Regulation creates inefficiency window | Regulation/tariff/sanctions change |
| D12 | Shipping Route Advantage | Proximity or new route gives edge | Shipping cost change + proximity check |
| D13 | Supplier-Buyer Match | Supplier has what buyer explicitly needs | New supplier + new demand in graph |
| D14 | Brokerage | High-value demand + matching supply, $0 capital | Demand budget >$50K + supplier match |

### For Every Detected Opportunity, Answer:
- **Why does this exist?** — Signal evidence + graph analysis
- **Why would competitors miss it?** — How many other suppliers are connected to this demand in the graph?
- **What capital is required?** — Estimated from purchase + shipping + duties
- **What is the timeline?** — Cash conversion cycle estimate
- **Is it repeatable?** — Recurring demand check
- **What is the window?** — Deadline-driven or market-efficiency-driven

### Output: DetectedOpportunity
```
DetectedOpportunity {
    opportunity_id: UUID, opportunity_type: enum, title: str, description: str
    source_country: str, target_country: str
    source_companies: [UUID], target_buyers: [UUID]
    products: [{master_product_id: UUID, hs_code: str, quantity_estimate: float}]
    triggering_signals: [UUID], evidence_strength: float
    capital_required_estimate: float, profit_estimate: float
    timeline_estimate_days: int, window_estimate: str
    is_repeatable: bool, competitor_count: int
    why_exists: str, competitor_analysis: str
    detected_at: datetime, confidence: float, urgency: enum
}
```

---

## STAGE 7 — VALIDATION ENGINE

### Purpose
Before committing capital, every opportunity must survive verification. The internet contains lies, scams, outdated listings, and phantom companies.

### Validation Pipeline

```
DetectedOpportunity → 1. SUPPLIER VERIFICATION (WHOIS, SSL, business registry,
                         certifications check, email age, social presence, Street View)
                    → 2. BUYER VERIFICATION (government gazette, commercial registry,
                         credit check, tender reference cross-check)
                    → 3. DEMAND VERIFICATION (cross-reference tender on multiple
                         sources, verify tender ref, check procuring entity)
                    → 4. PRICE VERIFICATION (check against other suppliers,
                         UN Comtrade unit values, historical records; flag if >30% off median)
                    → 5. FEASIBILITY CHECK (export legality, import legality,
                         sanctions OFAC/EU/UN, dual-use goods, required licenses)
                    → ValidatedOpportunity
```

### AI Agents Involved
- **Supplier Verification Agent** — 0-10 trust score from verification signals
- **Buyer Due Diligence Agent** — government procurement portals, registries, sanctions lists
- **Price Sanity Agent** — DBSCAN outlier detection on comparable prices
- **Feasibility Agent** — export/import regulations, sanctions, licensing

### Output: ValidatedOpportunity
```
ValidatedOpportunity {
    opportunity_id: UUID, detected_opportunity_id: UUID
    supplier_validation_score: float, buyer_validation_score: float
    demand_validation_score: float, price_accuracy_score: float
    feasibility_score: float, composite_validation_score: float
    validation_class: enum  # VERIFIED, PARTIALLY_VERIFIED, SPECULATIVE
    confidence: float, source_reliability_score: float
    red_flags: [{flag_type: str, severity: enum, description: str}]
    verification_evidence: [{check_type: str, result: str, source: str, timestamp: datetime}]
    requires_human_review: bool
}
```

### Decision Criteria
- **VERIFIED:** Composite >= 7.0 AND zero high-severity red flags → proceed
- **PARTIALLY VERIFIED:** Composite 4.0-6.9 OR 1-2 medium red flags → caution
- **SPECULATIVE:** Composite < 4.0 OR any high-severity red flag → archive
- **Human review trigger:** Confidence < 0.60 AND value > $50K

---

## STAGE 8 — PROFITABILITY ENGINE

### Purpose
Transform "this looks interesting" into "$X net profit at Y% ROI in Z days." All-in cost modeling — no hidden costs, no optimistic assumptions.

### Full Cost Model

```
EXPECTED REVENUE = Selling Price x Quantity

COST STACK:
  - PURCHASE COST      = Unit Price x Quantity x (1 + buffer%)
  - SHIPPING COST      = Container/per-kg rate x quantity x mode multiplier
                          (sea=1.0, land=0.7, air=3.5)
  - INSURANCE          = Cargo Value x 1% (adjustable by route)
  - CUSTOMS DUTIES     = CIF Value x Duty Rate (HS-code + country-pair specific)
  - VAT / SALES TAX    = (CIF + Duty) x VAT Rate (country-specific)
  - HANDLING           = Purchase Cost x 2%
  - WAREHOUSING        = Purchase Cost x 1% x months_stored
  - FINANCING          = Purchase Cost x Annual Rate x (cash_cycle_days / 365)
  - BROKERAGE FEE      = Deal Size x Rate% (if applicable)
  - MISCELLANEOUS      = Purchase Cost x 2% (contingency)

TOTAL COST = sum of all above

GROSS PROFIT = Revenue - Purchase Cost
NET PROFIT   = Revenue - Total Cost
ROI          = Net Profit / Total Cost x 100
CASH CYCLE   = days from payment to collection
ANNUALIZED ROI = ROI x (365 / cash_cycle_days)
BREAK-EVEN   = Total Cost / Unit Margin
```

### Market-Driven Pricing (not flat 25%)

| Corridor | Base Margin | Rationale |
|----------|------------|-----------|
| TR->IQ (land) | 15-23% | Competitive, fast, established |
| TR->SY (land) | 20-28% | Higher risk, less competition |
| TR->SA (sea) | 12-18% | Competitive GCC market |
| CN->IQ (sea) | 22-30% | Long chain, financing cost |
| CN->SA (sea) | 15-22% | Competitive, established |
| CN->IR (sea) | 22-30% | Sanctions premium |

Small deals (<$10K): +8-12% margin bonus. Large deals (>$500K): -3-5%.

### Sensitivity Analysis
- **Optimistic:** Revenue +20%, Costs -10%
- **Pessimistic:** Revenue -20%, Costs +10%
- **Monte Carlo:** 1000 iterations with +/-20% variance per component

### AI Agents Involved
- **Pricing Agent** — market-clearing price from graph comparables + UN Comtrade unit values + demand budget indicators
- **Cost Estimation Agent** — fills missing costs from shipping routes, customs rates, insurance tables
- **Sensitivity Agent** — Monte Carlo simulation for profit distribution

### Output: FinancialProfile
```
FinancialProfile {
    opportunity_id: UUID
    costs: {purchase, shipping, insurance, customs_duty, vat_tax, other_taxes,
            handling, warehousing, financing, brokerage_fee, miscellaneous, total}
    expected_selling_price: float, expected_commission: float
    gross_profit: float, net_profit: float, roi_pct: float
    annualized_roi_pct: float, cash_conversion_days: int
    break_even_units: int, profit_per_dollar_invested: float
    optimistic_net_profit: float, pessimistic_net_profit: float
    profit_volatility: float, probability_of_profit: float
    comparable_prices: [{source, price, date}]
}
```

---

## STAGE 9 — RISK ENGINE

### Purpose
Profit without risk assessment is gambling. 11-dimensional risk profile → unified risk score.

### 11 Risk Dimensions

| # | Dimension | Weight | Key Inputs |
|---|-----------|--------|-----------|
| R1 | Supplier Risk | 20% | Verification score, years in business, certifications, contact completeness |
| R2 | Buyer Risk | 15% | Government/corporate/unknown, verifiable track record |
| R3 | Country Risk | 15% | Baselined: AE=15, SA=20, IQ=50, SY=70, IR=60. World Bank governance indicators |
| R4 | Political Risk | 8% | Sanctions exposure, conflict zones, political instability |
| R5 | Currency Risk | 10% | TRY=25% vol, IRR=35% (+convertibility), SAR=1% (pegged) |
| R6 | Logistics Risk | 10% | Distance, border crossings, port efficiency, route reliability |
| R7 | Customs Risk | 10% | Country clearance complexity, HS-code restrictions, documentation |
| R8 | Payment Risk | 10% | LC=20, Advance=10, TT=35, Open Account=60. Country banking restrictions |
| R9 | Fraud Risk | 5% | Spam probability, fraud patterns, verification gaps, too-good-to-be-true |
| R10 | Market Risk | 5% | Opportunity-type volatility: tenders=35, arbitrage=30, reconstruction=45 |
| R11 | Execution Risk | 7% | Complexity: distance + language + parties + documentation |

```
UNIFIED RISK SCORE = sum(weight_i x risk_component_i)

Risk Levels:
  0-25  = LOW      (proceed with standard precautions)
  25-50 = MEDIUM   (proceed with mitigations)
  50-75 = HIGH     (requires significant risk management)
  75-100 = EXTREME (avoid unless extraordinary strategic value)
```

### Risk Mitigation Generator

| Risk >60 | Mitigation |
|----------|-----------|
| Supplier | Third-party inspection, samples, references, escrow |
| Buyer | Letter of credit, advance payment, credit insurance |
| Country | Political risk insurance, local partner |
| Currency | USD/EUR denomination, forward contracts |
| Payment | Confirmed irrevocable LC only |

### AI Agents Involved
- **Risk Scoring Agent** — computes all 11 dimensions, normalizes, applies weights
- **Mitigation Agent** — tailored mitigations per elevated dimension
- **Red Flag Agent** — show-stoppers: sanctions, >75 composite, known fraud

### Output: RiskProfile
```
RiskProfile {
    opportunity_id: UUID
    components: {supplier_risk, buyer_risk, country_risk, political_risk,
                 currency_risk, logistics_risk, customs_risk, payment_risk,
                 fraud_risk, market_risk, execution_risk}  # all 0-100
    composite_risk_score: float, risk_level: enum
    risk_adjusted_return: float  # Expected Profit x (1 - Risk/100)
    key_risks: [str], mitigations: [str], red_flags: [str]
    is_investable: bool
}
```

---

## STAGE 10 — OPPORTUNITY SCORING

### Purpose
Reduce every opportunity to a single 0-100 score. This is the ranking engine.

### Scoring Formula

```
OPPORTUNITY SCORE = sum(weight_i x component_score_i)

Weights (learned over time from Stage 14):

| Component              | Weight | Calculation |
|------------------------|--------|-------------|
| Expected Profit        | 25%    | Nonlinear: min(100, (profit/1000)^0.6 x 8) |
| Probability of Success | 20%    | Validation confidence x detector confidence x 100 |
| Capital Efficiency     | 15%    | ROI %. Brokerage (inf ROI) = 100. Zero-capital bonus: +20 |
| Execution Ease         | 10%    | (10 - complexity) / 10 x 100 |
| Speed to Revenue       | 10%    | <=7d=100, <=30d=85, <=60d=65, <=120d=40, >120d=15 |
| Repeatability          | 8%     | Recurring=90, One-shot=20 |
| Risk Inverse           | 7%     | 100 - composite_risk_score |
| Scalability            | 5%     | Commodity=high, bespoke=low |
```

### Score Tiers

| Tier | Score | Action |
|------|-------|--------|
| **S** | 85-100 | **EXECUTE** — allocate capital, contact today |
| **A** | 70-84 | **INVESTIGATE** — verify details, prepare negotiation |
| **B** | 50-69 | **PURSUE** — standard diligence, portfolio consideration |
| **C** | 30-49 | **MONITOR** — set alerts, revisit if conditions improve |
| **D** | 0-29 | **ARCHIVE** — do not pursue unless fundamental change |

### Rankings
1. **Global rank:** by score descending
2. **Tier rank:** within capital tier ($0, <$10K, <$50K, <$100K, <$500K, <$1M)
3. **Type rank:** within opportunity type (best brokerage, best arbitrage, etc.)

### Output: ScoredOpportunity
```
ScoredOpportunity {
    opportunity_id: UUID
    component_scores: {profit_score, probability_score, capital_efficiency_score,
                       execution_ease_score, speed_score, repeatability_score,
                       scalability_score, risk_inverse_score}
    final_score: float, tier: enum  # S, A, B, C, D
    global_rank: int, capital_tier: str, tier_rank: int, type_rank: int
    summary: str
}
```

---

## STAGE 11 — AI INVESTMENT COMMITTEE

### Purpose
A single score can be gamed. The AI Investment Committee simulates a panel of 7 specialized experts who debate every top-tier opportunity. Adversarial collaboration > any single model.

### The 7 Committee Members

```
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ TRADER   │ │ BROKER   │ │ RISK     │ │ LOGISTICS│ │ MARKET   │ │ FINANCIAL│ │CONTRARIAN│
│ AGENT    │ │ AGENT    │ │ AGENT    │ │ AGENT    │ │ ANALYST  │ │ ANALYST  │ │ AGENT    │
│ Focus:   │ │ Focus:   │ │ Focus:   │ │ Focus:   │ │ Focus:   │ │ Focus:   │ │ Focus:   │
│ Price    │ │ Conn-    │ │ Downside │ │ Feas-    │ │ Demand   │ │ Numbers  │ │ "What if │
│ timing   │ │ ection   │ │ protect- │ │ ibility  │ │ strength │ │ cashflow │ │  wrong?" │
│ margin   │ │ value    │ │ ion      │ │ timeline │ │ timing   │ │ returns  │ │          │
└────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
     └─────────────┴────────────┴────────────┴────────────┴────────────┴────────────┘
                                         ↓
                               CONSENSUS / DISSENT
                                         ↓
                              DEBATE MINUTES & VOTE
```

### Each Agent Must Answer
1. **Why pursue?** — Top 3 reasons with specific evidence
2. **Why reject?** — Top 3 concerns with specific evidence
3. **What assumptions might be wrong?** — Fragility assessment
4. **What evidence is missing?** — Data gaps that would change the decision
5. **Vote:** PURSUE / HOLD / REJECT with confidence (0-1)

### The Contrarian Agent (most important)
- "What if the buyer doesn't actually have budget?"
- "What if the supplier's claimed capacity is inflated 10x?"
- "What if customs clearance takes 3x longer?"
- "What if the currency devalues 15% between contract and payment?"
- "Has anyone actually called this phone number?"

### Consensus Mechanism
```
Weights: Trader 20%, Broker 15%, Risk 20%, Logistics 10%, Market Analyst 15%, Financial Analyst 10%, Contrarian 10%

CONSENSUS: >=5 PURSUE, no REJECT votes
SPLIT:     3-4 PURSUE, remainder HOLD
DEADLOCK:  >=2 REJECT -> flagged
```

### AI Implementation
Each agent is an LLM instance (Claude, GPT-4) with a specialized system prompt. They receive the full ScoredOpportunity + knowledge graph access + signal evidence. Structured JSON output.

### Output: CommitteeDecision
```
CommitteeDecision {
    opportunity_id: UUID
    votes: {trader, broker, risk, logistics, market_analyst, financial_analyst, contrarian}
           each: {vote: enum, confidence: float, rationale: str}
    consensus: enum  # CONSENSUS, SPLIT, DEADLOCK
    final_vote: enum  # PURSUE, HOLD, REJECT
    key_agreements: [str], key_disagreements: [str]
    missing_evidence: [str], fragile_assumptions: [str]
    debate_minutes: str
}
```

---

## STAGE 12 — DECISION ENGINE

### Purpose
Answer the core question with absolute clarity: "Here is exactly where to deploy your capital today, ranked by expected outcome."

### Daily Briefing (07:00 Baghdad time)

```
┌─────────────────────────────────────────────────────────────┐
│           OIP DAILY CAPITAL ALLOCATION REPORT                │
│           Date: 2026-06-16  |  07:00 Asia/Baghdad            │
├─────────────────────────────────────────────────────────────┤
│ EXECUTIVE SUMMARY                                           │
│ 247 opportunities monitored. 12 new in 24h. 3 Tier S/A.    │
│ Total addressable profit: $4.2M. Top corridor: TR->IQ.     │
├─────────────────────────────────────────────────────────────┤
│ IF YOU HAVE $0:  (Brokerage / Commission Only)              │
│ #1 NEOM Brokerage - $15M deal x 3% = $450K. Score: 82/A    │
│ #2 Iraq Hospital Tender - $2.5M x 3% = $75K. Score: 79/A   │
│                                                             │
│ IF YOU HAVE $10,000:                                        │
│ #1 Medical Scrubs TR->IQ - Capital $2.1K, Profit $840,      │
│     ROI 40%, Risk 42, Score 76/A, Repeatable monthly        │
│ #2 LED Fixtures CN->SA - Capital $5.2K, Profit $1.8K,       │
│     ROI 35%, Risk 38, Score 71/A                            │
│                                                             │
│ IF YOU HAVE $50,000: ... (same structure)                   │
│ IF YOU HAVE $100,000: ...                                   │
│ IF YOU HAVE $500,000: ...                                   │
│ IF YOU HAVE $1,000,000: ...                                 │
├─────────────────────────────────────────────────────────────┤
│ BEST BY CATEGORY                                            │
│ Low-Risk: Electronics CN->AE (Risk 22, ROI 18%)              │
│ High-Margin: Steel TR->IQ (ROI 62%)                          │
│ Repeatable: Medical Monthly Contract (12-month recurring)   │
│ Long-Term: Syria Reconstruction (2-5 year horizon)          │
├─────────────────────────────────────────────────────────────┤
│ FORWARD LOOKING                                             │
│ 3mo: Qatar Healthcare Procurement                           │
│ 6mo: Iraq Railway Materials                                 │
│ 12mo: Saudi Vision 2030 Industrial Supplies                 │
├─────────────────────────────────────────────────────────────┤
│ PORTFOLIO ($100K deployment):                               │
│ $35K -> Steel TR->IQ (74/A, 62% ROI)                        │
│ $25K -> Medical Scrubs (76/A, 40% ROI)                      │
│ $20K -> LED Lights CN->SA (71/A, 35% ROI)                   │
│ $12K -> PVC Pipes TR->SY (65/B, 27% ROI)                    │
│ $8K  -> Reserve for emergencies                             │
│ Total: $92K deployed | Profit: $42.8K | Blended ROI: 46.5% │
└─────────────────────────────────────────────────────────────┘
```

### Capital Allocation Algorithm
```
function allocate(available, opportunities):
    sort by score descending
    for each opp in opportunities:
        if opp.capital <= remaining x 1.10:
            add to portfolio, subtract from remaining
    check diversification (corridor, type concentration)
    rebalance if over-concentrated
    return {portfolio, total_deployed, remaining, blended_roi, expected_profit}
```

---

## STAGE 13 — ACTION ENGINE

### Purpose
Convert decisions into executable tasks with specific contacts, questions, documents, and deadlines.

### Action Plan Structure (per opportunity)

```
OPPORTUNITY: Turkish Steel Rebar -> Iraq ($8,500 capital)

WEEK 1 - VERIFICATION
[] Call Ankara Steel: +90 312 555 0190
  Ask: "Can you supply 200 tons/month to Iraq? Certifications? Payment terms?"
[] Email for 3 photos of current inventory/production
[] Request proforma invoice for 50-ton trial order
[] Verify ISO 9001 certificate with issuing body
[] Contact Iraq buyer: Al-Rafidain Development Co
  Ask: "Exact specs? Delivery timeline? Payment method preference?"

WEEK 2 - LOGISTICS
[] Get shipping quotes from 3 freight forwarders (Ankara->Ibrahim Khalil->Baghdad)
[] Confirm Iraq customs clearance for HS 7214
[] Calculate all-in landed cost with exact duties

WEEK 3 - NEGOTIATION
[] Negotiate supplier: target $560/ton (from $580)
[] Negotiate buyer: $780/ton delivered Baghdad
[] Agree payment: LC from buyer, 30% advance to supplier
[] Draft contract with force majeure and arbitration clause

WEEK 4 - EXECUTION
[] Receive LC from buyer's bank
[] Issue purchase order to supplier
[] Arrange transport and insurance
[] Track shipment (GPS tracker recommended for Iraq)
[] Prepare customs documentation

DATA GAPS: buyer payment history, sanctions check, competitor pricing
DOCUMENTS: Commercial Invoice, Packing List, Certificate of Origin, B/L, Insurance, Mill Test Cert
DEADLINES: Supplier call Jun 17 | Shipping quotes Jun 19 | Proforma Jun 20 | LC Jun 25 | Ship Jul 10
PRIORITY: HIGH | CONFIDENCE: 75% | SCORE: 74/A
```

### Output: ActionPlan
```
ActionPlan {
    opportunity_id: UUID, title: str
    phases: [{phase: str, week: int, tasks: [{
        task_id: UUID, description: str
        contact: {name, phone, email, role}
        questions_to_ask: [str]
        deadline: datetime, priority: enum
        depends_on: [UUID], status: enum  # PENDING, IN_PROGRESS, COMPLETED, BLOCKED
    }]}]
    data_gaps: [{gap: str, importance: enum, how_to_fill: str}]
    documents_needed: [{document: str, template_available: bool, issuing_party: str}]
    key_contacts: [{name, company, role, phone, email, whatsapp, best_time_to_contact, notes}]
    timeline: {start_date, target_completion, critical_path_tasks: [UUID]}
    priority: enum
}
```

---

## STAGE 14 — FEEDBACK & LEARNING

### Purpose
The platform's intelligence compounds. Every executed opportunity — success, failure, or missed — becomes training data.

### Five Learning Loops

**Loop 1: Scoring Weight Optimization**
- Input: Executed opportunities with actual outcomes
- Method: Gradient descent on scoring weights to maximize score-outcome correlation
- Frequency: Monthly, after >=10 executed opportunities

**Loop 2: Risk Model Calibration**
- Input: Predicted risk_score vs actual issues encountered
- Method: Compare each risk component with reality. Adjust baselines per country/corridor
- Output: Updated country risk baselines, shipping reliability scores

**Loop 3: Detector Tuning**
- Input: Opportunities detected vs opportunities missed
- Method: Analyze missed opportunities — what signals were present? What threshold was too high?
- Output: Adjusted detection thresholds, new signal patterns

**Loop 4: Validation Accuracy**
- Input: Validation scores vs actual legitimacy
- Method: Track false negatives (fraud that passed) and false positives (legit entities flagged)
- Output: Updated spam/fraud classifier thresholds

**Loop 5: Committee Performance**
- Input: Committee votes vs actual outcomes
- Method: Track which agent was most predictive. Increase their weight. Decrease consistently wrong agents.
- Output: Adjusted committee voting weights

### Outcome Tracking Table
```sql
CREATE TABLE opportunity_outcomes (
    id UUID PRIMARY KEY,
    opportunity_id UUID REFERENCES opportunities(id),
    status ENUM('executed','abandoned','expired','missed'),
    actual_purchase_cost_usd NUMERIC, actual_shipping_cost_usd NUMERIC,
    actual_customs_duty_usd NUMERIC, actual_revenue_usd NUMERIC,
    actual_net_profit_usd NUMERIC, actual_roi_pct NUMERIC,
    actual_cash_cycle_days INT,
    actual_supplier_issues TEXT[], actual_buyer_issues TEXT[],
    actual_logistics_issues TEXT[], actual_customs_issues TEXT[],
    actual_payment_issues TEXT[],
    prediction_accuracy_score FLOAT,
    lessons_learned TEXT, would_repeat BOOLEAN,
    completed_at TIMESTAMPTZ, outcome_recorded_at TIMESTAMPTZ DEFAULT now()
);
```

### Continuous Improvement Metrics

| Metric | Target |
|--------|--------|
| Score-outcome correlation | >0.70 |
| Risk prediction accuracy | +/-15% of actual issues |
| Detection recall (found/actual) | >80% |
| Validation precision (real/flagged) | >90% |
| Committee consensus accuracy | >75% correct |

---

## END-TO-END DATA FLOW

```
RAW WORLD
    |
    v
STAGE 1:  COLLECTION     RawItem stream (~10K-100K items/day)
    |
    v
STAGE 2:  CLEANING       CleanedItem (~30-50% of raw - deduped, filtered)
    |
    v
STAGE 3:  RESOLUTION     MasterEntity (golden records, ~500-5K entities)
    |
    v
STAGE 4:  KNOWLEDGE GRAPH Connected nodes + edges in graph DB
    |
    v
STAGE 5:  SIGNAL DETECTION MarketSignal (~50-500 signals/day)
    |
    v
STAGE 6:  OPPORTUNITY DETECTION DetectedOpportunity (~20-200/day)
    |
    v
STAGE 7:  VALIDATION     ValidatedOpportunity (~50-80% pass)
    |
    v
STAGE 8:  PROFITABILITY  FinancialProfile
    |
    v
STAGE 9:  RISK           RiskProfile
    |
    v
STAGE 10: SCORING        ScoredOpportunity (ranked 0-100, S/A/B/C/D)
    |
    v
STAGE 11: COMMITTEE      CommitteeDecision (top ~20 debated)
    |
    v
STAGE 12: DECISION       Daily Capital Allocation Report
    |
    v
STAGE 13: ACTION         Daily Action Plan (contacts, tasks, deadlines)
    |
    v
OPERATOR EXECUTES --> OUTCOME DATA --> STAGE 14: LEARNING --> (back to Stage 10)
```

---

## OPERATIONAL CADENCE

| Frequency | Activity | Stage |
|-----------|----------|-------|
| **Continuous** | Data collection (all sources) | 1 |
| **Every 15 min** | High-frequency source refresh (news, tenders) | 1 |
| **Every 1 hour** | Signal detection scan | 5 |
| **Every 6 hours** | Opportunity detection + validation | 6-7 |
| **Every 12 hours** | Full pipeline (profitability, risk, scoring) | 8-10 |
| **Daily 07:00** | Committee convenes, Decision Engine, Briefing + Action Plan | 11-13 |
| **Weekly** | Learning loop analysis, weight adjustments | 14 |
| **Monthly** | Scoring weight optimization, risk model recalibration | 14 |

---

## SYSTEM PROPERTIES

| Property | Implementation |
|----------|---------------|
| **Idempotent** | Content hashing prevents double-processing at every stage |
| **Incremental** | Only new/changed data flows. Unchanged entities untouched |
| **Observable** | Every stage emits metrics: items processed, errors, latency |
| **Degradable** | Source failures don't stop pipeline. No single point of failure |
| **Auditable** | Every transformation logged. Output traceable to raw inputs |
| **Personal** | No users. No SaaS. No multi-tenant. Single operator, single truth |

---

*OIP Workflow Architecture v2.0.0 — Complete 14-Stage Design — June 2026*
